from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from pdf2video.compositor import compose_video
from pdf2video.extractor import extract_text
from pdf2video.script_generator import generate_script, generate_script_from_txt
from pdf2video.sticker_overlay import parse_sticker_config
from pdf2video.subtitle_generator import (
    apply_emphasis_to_segments,
    detect_keywords_for_emphasis,
    export_to_ass,
    generate_subtitles,
)
from pdf2video.tts_engine import text_to_speech
from pdf2video.types import FinalVideo, StickerConfig, SubtitleConfig, VideoClip
from pdf2video.video_downloader import download_video
from pdf2video.video_searcher import search_videos

logger = logging.getLogger(__name__)

# Default video resolution (width, height)
DEFAULT_RESOLUTION = (1920, 1080)

class PipelineError(Exception):
    pass


def _build_search_query(script: str) -> str:
    # Check if script contains Chinese characters
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in script)
    if has_chinese:
        return "business technology manufacturing"
    
    # Existing logic for English
    first_sentence = script.split(".", maxsplit=1)[0].strip()
    if not first_sentence:
        return "research presentation"

    words = [word.strip(" ,:;!?()[]{}\"'").lower() for word in first_sentence.split()]
    filtered_words = [word for word in words if len(word) > 3]
    if not filtered_words:
        return "research presentation"
    return " ".join(filtered_words[:6])


def _cleanup_intermediate_files(audio_path: Path, downloaded_clips: list[VideoClip], temp_dir: Path) -> None:
    if audio_path.exists():
        audio_path.unlink()

    for clip in downloaded_clips:
        if clip.file_path.exists():
            clip.file_path.unlink()

    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def _raise_stage_error(stage_name: str, exc: Exception) -> None:
    raise PipelineError(f"Failed at step {stage_name}: {exc}") from exc


def _default_subtitle_config() -> SubtitleConfig:
    return SubtitleConfig(
        font_path="Arial",
        font_size=48,
        color=(255, 255, 255),
        outline_color=(0, 0, 0),
        position="bottom",
    )


def _generate_subtitles_with_constraints(
    script: str,
    audio_duration: float,
    config: SubtitleConfig,
) -> list:
    try:
        return generate_subtitles(script, audio_duration, config)
    except TypeError as exc:
        logger.debug(
            "generate_subtitles signature fallback triggered (continuing with legacy call): %s",
            exc,
        )
        return generate_subtitles(script, audio_duration)


def _export_subtitles_ass(
    segments: list,
    output_path: Path,
    config: SubtitleConfig,
) -> None:
    try:
        export_to_ass(segments, output_path, config, DEFAULT_RESOLUTION)
    except TypeError as exc:
        logger.debug(
            "export_to_ass signature fallback triggered (continuing with legacy call): %s",
            exc,
        )
        export_to_ass(segments, output_path, config)


def _check_video_apis_available() -> bool:
    """Check if video APIs (Pexels) are configured."""
    return bool(os.getenv("PEXELS_API_KEY"))


def run_pipeline(
    input_path: str,
    output_path: str,
    cleanup: bool = True,
    enable_subtitles: bool = False,
    enable_emphasis: bool = False,
    sticker_config: Optional[Path] = None,
    subtitle_config: Optional[SubtitleConfig] = None,
    skip_tts: bool = False,
    target_duration: Optional[float] = None,
) -> FinalVideo:
    """Run the full pipeline or audio-only pipeline based on API availability.
    
    Args:
        input_path: Path to input PDF or TXT file
        output_path: Path for output video/audio file
        cleanup: Whether to remove intermediate files (default True)
        enable_subtitles: Generate and burn subtitles into video (default False)
        enable_emphasis: Use AI to detect keywords for subtitle emphasis (default False)
        sticker_config: Optional path to JSON sticker configuration file
        subtitle_config: Optional SubtitleConfig for customizing subtitle appearance
        skip_tts: Skip TTS generation and use estimated/target duration (default False)
        target_duration: Optional target video duration in seconds (used when skip_tts=True)
    
    Returns:
        FinalVideo with path, duration, and resolution
    """
    
    # Check if video APIs are available
    video_enabled = _check_video_apis_available()
    
    if video_enabled:
        return _run_full_pipeline(
            input_path,
            output_path,
            cleanup,
            enable_subtitles=enable_subtitles,
            enable_emphasis=enable_emphasis,
            sticker_config=sticker_config,
            subtitle_config=subtitle_config,
            skip_tts=skip_tts,
            target_duration=target_duration,
        )
    else:
        return _run_audio_only_pipeline(
            input_path,
            output_path,
            cleanup,
            enable_subtitles=enable_subtitles,
            enable_emphasis=enable_emphasis,
            sticker_config=sticker_config,
            subtitle_config=subtitle_config,
            skip_tts=skip_tts,
            target_duration=target_duration,
        )
def _run_audio_only_pipeline(
    input_path: str,
    output_path: str,
    cleanup: bool = True,
    enable_subtitles: bool = False,
    enable_emphasis: bool = False,
    sticker_config: Optional[Path] = None,
    subtitle_config: Optional[SubtitleConfig] = None,
    skip_tts: bool = False,
    target_duration: Optional[float] = None,
) -> FinalVideo:
    """Run pipeline that outputs only audio (when PEXELS_API_KEY is not set).
    
    Note: Subtitles and stickers are ignored in audio-only mode since there is no video.
    """
    if enable_subtitles:
        logger.warning("Subtitles ignored in audio-only mode (no video)")
    if sticker_config is not None:
        logger.warning("Stickers ignored in audio-only mode (no video)")
    
    total_steps = 3
    text = ""
    script = ""
    temp_dir = Path(tempfile.mkdtemp(prefix="pdf2video_"))
    audio_path = temp_dir / "narration.mp3"
    input_file = Path(input_path)

    try:
        # Detect file type and extract/read text
        if input_file.suffix.lower() == '.txt':
            logger.info("[1/%s] Reading TXT file...", total_steps)
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                if not text or not text.strip():
                    raise PipelineError("TXT file is empty")
            except PipelineError:
                raise
            except Exception as exc:
                _raise_stage_error("TXT reading", exc)
        else:
            logger.info("[1/%s] Extracting PDF text...", total_steps)
            try:
                text = extract_text(input_path)
            except Exception as exc:
                _raise_stage_error("PDF extraction", exc)

        logger.info("[2/%s] Generating narration script...", total_steps)
        try:
            script = generate_script(text)
        except Exception as exc:
            _raise_stage_error("script generation", exc)

        if skip_tts:
            logger.info("[3/%s] Skipping TTS (--no-tts flag)...", total_steps)
            # Create a placeholder audio path and estimate duration
            from pdf2video.tts_engine import _estimate_duration_seconds
            duration = _estimate_duration_seconds(script)
            # Create an empty audio file as placeholder
            audio_path.touch()
        else:
            logger.info("[3/%s] Converting script to audio...", total_steps)
            try:
                text_to_speech(script, str(audio_path))
            except Exception as exc:
                _raise_stage_error("text-to-speech", exc)

        # Copy audio to output path
        # Ensure output has .mp3 extension if it's audio-only
        output_file = Path(output_path)
        if output_file.suffix.lower() not in ['.mp3', '.wav', '.m4a']:
            output_file = output_file.with_suffix('.mp3')
        
        # Copy the audio file to output (only if not skip_tts)
        if not skip_tts:
            shutil.copy2(audio_path, output_file)
        
        # Get audio duration
        from pdf2video.tts_engine import _estimate_duration_seconds
        duration = _estimate_duration_seconds(script)
        
        final_video = FinalVideo(
            file_path=output_file,
            duration=duration,
            resolution="0x0"  # No video, just audio
        )
        
        logger.info("Audio-only pipeline completed successfully: %s (duration: %.1fs)", final_video.file_path, duration)
        logger.info("💡 Tip: Set PEXELS_API_KEY to enable video generation")
        
        return final_video
        
    finally:
        if cleanup:
            try:
                if audio_path.exists():
                    audio_path.unlink()
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as exc:
                logger.warning("Failed to clean intermediate files: %s", exc)

def _run_full_pipeline(
    input_path: str,
    output_path: str,
    cleanup: bool = True,
    enable_subtitles: bool = False,
    enable_emphasis: bool = False,
    sticker_config: Optional[Path] = None,
    subtitle_config: Optional[SubtitleConfig] = None,
    skip_tts: bool = False,
    target_duration: Optional[float] = None,
) -> FinalVideo:
    """Run the full pipeline with video generation."""
    
    total_steps = 6
    if enable_subtitles:
        total_steps += 1
    if sticker_config is not None:
        total_steps += 1
    
    text = ""
    script = ""
    clips: list[VideoClip] = []
    final_video: FinalVideo | None = None
    downloaded_clips: list[VideoClip] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="pdf2video_"))
    audio_path = temp_dir / "narration.mp3"
    video_cache_dir = temp_dir / "videos"
    input_file = Path(input_path)
    subtitle_ass_path: Optional[Path] = None
    effective_subtitle_config: Optional[SubtitleConfig] = None
    stickers: Optional[list[StickerConfig]] = None
    current_step = 0

    try:
        # Detect file type and extract/read text
        if input_file.suffix.lower() == '.txt':
            current_step += 1
            logger.info("[%d/%s] Reading TXT file...", current_step, total_steps)
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                if not text or not text.strip():
                    raise PipelineError("TXT file is empty")
            except PipelineError:
                raise
            except Exception as exc:
                _raise_stage_error("TXT reading", exc)
        else:
            current_step += 1
            logger.info("[%d/%s] Extracting PDF text...", current_step, total_steps)
            try:
                text = extract_text(input_path)
            except Exception as exc:
                _raise_stage_error("PDF extraction", exc)

        current_step += 1
        logger.info("[%d/%s] Generating narration script...", current_step, total_steps)
        try:
            script = generate_script(text)
        except Exception as exc:
            _raise_stage_error("script generation", exc)

        current_step += 1
        if skip_tts:
            logger.info("[%d/%s] Skipping TTS (--no-tts flag)...", current_step, total_steps)
        else:
            logger.info("[%d/%s] Converting script to audio...", current_step, total_steps)
            try:
                text_to_speech(script, str(audio_path))
            except Exception as exc:
                _raise_stage_error("text-to-speech", exc)

        # Get audio duration for subtitle timing
        # If skip_tts and target_duration provided, use target_duration
        audio_duration: float = 0.0
        if skip_tts and target_duration is not None and target_duration > 0:
            audio_duration = target_duration
            logger.debug("Using target duration for timing: %.2fs", target_duration)
        elif enable_subtitles or sticker_config is not None:
            from pdf2video.tts_engine import _estimate_duration_seconds
            audio_duration = _estimate_duration_seconds(script)
        # Generate subtitles if enabled
        if enable_subtitles:
            current_step += 1
            logger.info("[%d/%s] Generating subtitles...", current_step, total_steps)
            try:
                effective_subtitle_config = subtitle_config or _default_subtitle_config()
                segments = _generate_subtitles_with_constraints(
                    script,
                    audio_duration,
                    effective_subtitle_config,
                )
                
                # Apply emphasis if enabled (non-blocking on failure)
                if enable_emphasis:
                    try:
                        keywords = detect_keywords_for_emphasis(script)
                        if keywords:
                            logger.debug("Applying emphasis for %d keywords", len(keywords))
                            segments = apply_emphasis_to_segments(segments, keywords)
                    except Exception as keyword_exc:
                        logger.warning("Keyword detection failed (continuing without emphasis): %s", keyword_exc)
                
                # Export ASS file to temp directory
                subtitle_ass_path = temp_dir / "subtitles.ass"
                _export_subtitles_ass(segments, subtitle_ass_path, effective_subtitle_config)
                logger.debug("Subtitles exported to %s", subtitle_ass_path)
            except Exception as exc:
                _raise_stage_error("subtitle generation", exc)

        # Load sticker config if provided
        if sticker_config is not None:
            current_step += 1
            logger.info("[%d/%s] Loading sticker configuration...", current_step, total_steps)
            try:
                stickers = parse_sticker_config(sticker_config)
                logger.debug("Loaded %d stickers from config", len(stickers))
            except Exception as exc:
                logger.warning("Sticker config parsing failed (continuing without stickers): %s", exc)
                stickers = None

        current_step += 1
        logger.info("[%d/%s] Searching for video clips...", current_step, total_steps)
        query = _build_search_query(script)
        try:
            clips = search_videos(query)
            if not clips:
                raise PipelineError(f"Failed at step video search: no clips found for query '{query}'")
        except PipelineError:
            raise
        except Exception as exc:
            _raise_stage_error("video search", exc)

        current_step += 1
        logger.info("[%d/%s] Downloading video clips...", current_step, total_steps)
        download_errors: list[str] = []
        for clip in clips:
            try:
                downloaded_clips.append(download_video(clip, cache_dir=str(video_cache_dir)))
            except Exception as exc:
                clip_name = clip.file_path.name
                logger.warning("Video clip download failed for %s: %s", clip_name, exc)
                download_errors.append(f"{clip_name}: {exc}")

        if not downloaded_clips:
            if download_errors:
                raise PipelineError(
                    "Failed at step video download: no clips downloaded; "
                    f"{len(download_errors)} failures. First failure: {download_errors[0]}"
                )
            raise PipelineError("Failed at step video download: no clips downloaded")

        current_step += 1
        logger.info("[%d/%s] Composing final video...", current_step, total_steps)
        try:
            # Use placeholder audio path if skip_tts is True
            audio_file = str(audio_path) if not skip_tts else None
            # Pass target_duration for no-audio path (skip_tts mode)
            effective_target = target_duration if (skip_tts and target_duration is not None and target_duration > 0) else None
            final_video = compose_video(
                audio_file,
                downloaded_clips,
                output_path,
                subtitle_path=subtitle_ass_path,
                stickers=stickers,
                target_duration=effective_target,
            )
        except Exception as exc:
            _raise_stage_error("video composition", exc)

        if final_video is None:
            raise PipelineError("Failed at step video composition: empty composition result")

        logger.info("Pipeline completed successfully: %s", final_video.file_path)
        return final_video
    finally:
        if cleanup:
            try:
                # Clean up subtitle file
                if subtitle_ass_path is not None and subtitle_ass_path.exists():
                    subtitle_ass_path.unlink()
                _cleanup_intermediate_files(audio_path, downloaded_clips, temp_dir)
            except Exception as exc:
                logger.warning("Failed to clean intermediate files: %s", exc)
