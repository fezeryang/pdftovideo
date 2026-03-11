from __future__ import annotations

import importlib
import logging
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any, List, Optional

from pdf2video.subtitle_utils import burn_subtitles_ffmpeg, check_ffmpeg_available
from pdf2video.types import FinalVideo, VideoClip, StickerConfig
from pdf2video.types import SubtitleError
from pdf2video.sticker_overlay import load_sticker
logger = logging.getLogger(__name__)


class CompositionError(Exception):
    pass


def _load_moviepy_editor() -> Any:
    return importlib.import_module("moviepy")


def _load_pysubs2() -> Any:
    return importlib.import_module("pysubs2")


def _ensure_file_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise CompositionError(f"Missing {label} file: {path}")


def _resize_clip(clip: Any, resolution: tuple[int, int]) -> Any:
    if hasattr(clip, "resize"):
        return clip.resize(newsize=resolution)
    if hasattr(clip, "resized"):
        return clip.resized(resolution)
    raise CompositionError("MoviePy clip does not support resize operations")


def _set_audio(clip: Any, audio_clip: Any) -> Any:
    if hasattr(clip, "set_audio"):
        return clip.set_audio(audio_clip)
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio_clip)
    raise CompositionError("MoviePy clip does not support audio assignment")


def _trim_clip(clip: Any, duration: float) -> Any:
    if hasattr(clip, "subclip"):
        return clip.subclip(0, duration)
    if hasattr(clip, "subclipped"):
        return clip.subclipped(0, duration)
    raise CompositionError("MoviePy clip does not support trimming")


def _loop_clip(moviepy_editor: Any, clip: Any, duration: float) -> Any:
    """Loop a clip to match the desired duration (MoviePy 2.x compatible)."""
    clip_duration = float(getattr(clip, "duration", 0) or 0)
    if clip_duration <= 0:
        raise CompositionError("Cannot loop clip with invalid duration")
    
    # Calculate how many times we need to repeat the clip
    num_loops = int(duration / clip_duration) + 1
    clips_to_concat = [clip] * num_loops
    
    # Use concatenate to create a looped clip
    looped = moviepy_editor.concatenate_videoclips(clips_to_concat, method="compose")
    
    # Trim to exact duration if needed
    if hasattr(looped, "subclip"):
        return looped.subclip(0, duration)
    elif hasattr(looped, "subclipped"):
        return looped.subclipped(0, duration)
    return looped
    vfx = getattr(moviepy_editor, "vfx", None)
    if vfx is None or not hasattr(vfx, "loop"):
        raise CompositionError("MoviePy vfx.loop is unavailable for extending short video")
    return clip.fx(vfx.loop, duration=duration)


def _build_subtitle_clips_moviepy(moviepy_editor: Any, subtitle_path: Path) -> List[Any]:
    pysubs2 = _load_pysubs2()
    subtitles = pysubs2.load(str(subtitle_path))

    subtitle_clips: List[Any] = []
    for event in getattr(subtitles, "events", []):
        raw_text = str(getattr(event, "text", "") or "").strip()
        if not raw_text:
            continue

        start_ms = float(getattr(event, "start", 0) or 0)
        end_ms = float(getattr(event, "end", start_ms) or start_ms)
        duration = max(0.0, (end_ms - start_ms) / 1000.0)
        if duration <= 0:
            continue

        text = raw_text.replace("\\N", "\n")
        text_clip = moviepy_editor.TextClip(text)
        text_clip = text_clip.with_start(start_ms / 1000.0)
        text_clip = text_clip.with_duration(duration)
        text_clip = text_clip.with_position(("center", "bottom"))
        subtitle_clips.append(text_clip)

    return subtitle_clips


def compose_video(
    audio_path: Optional[str],
    video_clips: List[VideoClip],
    output_path: str,
    resolution: tuple[int, int] = (1920, 1080),
    subtitle_path: Optional[Path] = None,
    stickers: Optional[List[StickerConfig]] = None,
    target_duration: Optional[float] = None,
) -> FinalVideo:
    """Compose a video from clips, optional audio, subtitles, and stickers.
    
    Args:
        audio_path: Path to audio file, or None for no audio
        video_clips: List of VideoClip objects to compose
        output_path: Path for output video file
        resolution: Output resolution (width, height), defaults to (1920, 1080)
        subtitle_path: Optional path to ASS subtitle file
        stickers: Optional list of StickerConfig for overlays
        target_duration: Optional target duration in seconds (used when no audio)
    
    Returns:
        FinalVideo with path, duration, and resolution
    """
    logger.info("Starting video composition (output: %s)", output_path)
    logger.debug("Composition parameters: resolution=%s, video_clips=%d", resolution, len(video_clips))
    if not video_clips:
        logger.error("No video clips provided for composition")
        raise CompositionError("At least one video clip is required for composition")

    if len(resolution) != 2 or resolution[0] <= 0 or resolution[1] <= 0:
        logger.error("Invalid resolution: %s", resolution)
        raise CompositionError("resolution must be a tuple of positive integers")

    audio_file: Optional[Path] = None
    if audio_path is not None:
        audio_file = Path(audio_path)
        logger.debug("Checking audio file: %s", audio_file)
        _ensure_file_exists(audio_file, "audio")

    subtitle_file: Optional[Path] = None
    if subtitle_path is not None:
        subtitle_file = Path(subtitle_path)
        if not subtitle_file.exists():
            raise SubtitleError(f"Missing subtitle file: {subtitle_file}")

    # Validate stickers limit (max 5)
    if stickers is not None and len(stickers) > 5:
        logger.error("Too many stickers: %d (max 5)", len(stickers))
        raise CompositionError("Maximum 5 stickers allowed per video")
    for idx, clip in enumerate(video_clips, 1):
        logger.debug("Checking video clip %d/%d: %s", idx, len(video_clips), clip.file_path)
        _ensure_file_exists(clip.file_path, "video")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory created: %s", output_file.parent)

    moviepy_editor = _load_moviepy_editor()
    logger.debug("MoviePy editor loaded successfully")

    audio_clip: Any = None
    loaded_video_clips: List[Any] = []
    loaded_sticker_clips: List[Any] = []
    composed_video_clip: Any = None
    final_video_clip: Any = None
    ffmpeg_subtitle_burn = bool(subtitle_file) and check_ffmpeg_available()
    temporary_output_path: Optional[Path] = None
    audio_duration = 0.0

    try:
        if audio_file is not None:
            logger.debug("Loading audio file: %s", audio_file)
            audio_clip = moviepy_editor.AudioFileClip(str(audio_file))
        else:
            logger.info("No audio file provided (skip_tts mode)")

        logger.debug("Loading %d video clips", len(video_clips))
        for idx, clip in enumerate(video_clips, 1):
            logger.debug("Loading video clip %d/%d: %s", idx, len(video_clips), clip.file_path)
            loaded_video_clips.append(moviepy_editor.VideoFileClip(str(clip.file_path)))

        if len(loaded_video_clips) == 1:
            logger.debug("Using single video clip (no concatenation needed)")
            composed_video_clip = loaded_video_clips[0]
        else:
            logger.info("Concatenating %d video clips", len(loaded_video_clips))
            composed_video_clip = moviepy_editor.concatenate_videoclips(
                loaded_video_clips,
                method="compose",
            )

        if audio_clip is not None:
            audio_duration = float(getattr(audio_clip, "duration", 0.0) or 0.0)
            video_duration = float(getattr(composed_video_clip, "duration", 0.0) or 0.0)
            logger.debug("Durations: audio=%.2fs, video=%.2fs", audio_duration, video_duration)

            if audio_duration > 0 and video_duration > 0:
                if video_duration < audio_duration:
                    logger.info("Looping video to match audio duration (%.2fs -> %.2fs)", video_duration, audio_duration)
                    composed_video_clip = _loop_clip(moviepy_editor, composed_video_clip, audio_duration)
                elif video_duration > audio_duration:
                    logger.info("Trimming video to match audio duration (%.2fs -> %.2fs)", video_duration, audio_duration)
                    composed_video_clip = _trim_clip(composed_video_clip, audio_duration)
        elif target_duration is not None and target_duration > 0:
            # No audio but target duration specified - enforce target length
            video_duration = float(getattr(composed_video_clip, "duration", 0.0) or 0.0)
            logger.debug("No audio - using target duration: %.2fs (video=%.2fs)", target_duration, video_duration)
            if video_duration > 0:
                if video_duration < target_duration:
                    logger.info("Looping video to match target duration (%.2fs -> %.2fs)", video_duration, target_duration)
                    composed_video_clip = _loop_clip(moviepy_editor, composed_video_clip, target_duration)
                elif video_duration > target_duration:
                    logger.info("Trimming video to match target duration (%.2fs -> %.2fs)", video_duration, target_duration)
                    composed_video_clip = _trim_clip(composed_video_clip, target_duration)
        logger.debug("Resizing video to %s", resolution)
        composed_video_clip = _resize_clip(composed_video_clip, resolution)

        overlay_layers: List[Any] = [composed_video_clip]

        # Load and apply stickers if provided
        if stickers:
            logger.info("Loading %d stickers", len(stickers))
            for idx, sticker_config in enumerate(stickers, 1):
                logger.debug("Loading sticker %d/%d: %s", idx, len(stickers), sticker_config.path)
                sticker_clip = load_sticker(sticker_config)
                # Apply timing: start time and duration
                sticker_duration = sticker_config.end_time - sticker_config.start_time
                sticker_clip = sticker_clip.with_start(sticker_config.start_time)
                sticker_clip = sticker_clip.with_duration(sticker_duration)
                loaded_sticker_clips.append(sticker_clip)

            overlay_layers.extend(loaded_sticker_clips)

        if subtitle_file is not None and not ffmpeg_subtitle_burn:
            logger.warning("FFmpeg unavailable, using MoviePy subtitle fallback")
            overlay_layers.extend(_build_subtitle_clips_moviepy(moviepy_editor, subtitle_file))

        if len(overlay_layers) > 1:
            logger.debug("Compositing video with %d overlay layers", len(overlay_layers) - 1)
            composed_video_clip = moviepy_editor.CompositeVideoClip(overlay_layers)

        if audio_clip is not None:
            logger.debug("Setting audio track")
            final_video_clip = _set_audio(composed_video_clip, audio_clip)
        else:
            logger.debug("No audio track (skip_tts mode)")
            final_video_clip = composed_video_clip

        fps = getattr(final_video_clip, "fps", None) or 30
        logger.info("Exporting final video: %s (fps=%d)", output_file, fps)

        video_export_path = output_file
        if subtitle_file is not None and ffmpeg_subtitle_burn:
            logger.info("FFmpeg available, rendering intermediate video for subtitle burn")
            with tempfile.NamedTemporaryFile(
                suffix=output_file.suffix,
                prefix=f"{output_file.stem}_base_",
                dir=output_file.parent,
                delete=False,
            ) as temp_file:
                temporary_output_path = Path(temp_file.name)
            video_export_path = temporary_output_path

        final_video_clip.write_videofile(
            str(video_export_path),
            codec="libx264",
            audio_codec="aac",
            fps=fps,
        )

        if subtitle_file is not None and ffmpeg_subtitle_burn and temporary_output_path is not None:
            burn_subtitles_ffmpeg(temporary_output_path, subtitle_file, output_file)

        final_duration = float(getattr(final_video_clip, "duration", audio_duration) or 0.0)
        logger.info("Video composition complete: %s (duration=%.2fs, resolution=%s)", output_file, final_duration, f"{resolution[0]}x{resolution[1]}")
        return FinalVideo(
            file_path=output_file,
            duration=final_duration,
            resolution=f"{resolution[0]}x{resolution[1]}",
        )
    except CompositionError:
        raise
    except SubtitleError:
        raise
    except FileNotFoundError as exc:
        logger.error("Asset file not found during composition: %s", exc)
        raise CompositionError(f"Asset file not found during composition: {exc}") from exc
    except PermissionError as exc:
        logger.error("Permission denied writing output video '%s': %s", output_file, exc)
        raise CompositionError(f"Permission denied writing output video '{output_file}': {exc}") from exc
    except OSError as exc:
        logger.error("Disk or filesystem error during video export: %s", exc)
        raise CompositionError(f"Disk or filesystem error during video export: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error during video composition: %s", exc)
        raise CompositionError(f"Failed to compose video: {exc}") from exc
    finally:
        for clip in (final_video_clip, composed_video_clip):
            if clip is not None:
                with suppress(Exception):
                    clip.close()

        for clip in loaded_video_clips:
            with suppress(Exception):
                clip.close()

        for clip in loaded_sticker_clips:
            with suppress(Exception):
                clip.close()

        if audio_clip is not None:
            with suppress(Exception):
                audio_clip.close()

        if temporary_output_path is not None and temporary_output_path.exists():
            with suppress(Exception):
                temporary_output_path.unlink()
