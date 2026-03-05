from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from pdf2video.compositor import compose_video
from pdf2video.extractor import extract_text
from pdf2video.script_generator import generate_script, generate_script_from_txt
from pdf2video.tts_engine import text_to_speech
from pdf2video.types import FinalVideo, VideoClip
from pdf2video.video_downloader import download_video
from pdf2video.video_searcher import search_videos


logger = logging.getLogger(__name__)


class PipelineError(Exception):
    pass


def _build_search_query(script: str) -> str:
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


def _check_video_apis_available() -> bool:
    """Check if video APIs (Pexels) are configured."""
    return bool(os.getenv("PEXELS_API_KEY"))


def run_pipeline(input_path: str, output_path: str, cleanup: bool = True) -> FinalVideo:
    """Run the full pipeline or audio-only pipeline based on API availability."""
    
    # Check if video APIs are available
    video_enabled = _check_video_apis_available()
    
    if video_enabled:
        return _run_full_pipeline(input_path, output_path, cleanup)
    else:
        return _run_audio_only_pipeline(input_path, output_path, cleanup)


def _run_audio_only_pipeline(input_path: str, output_path: str, cleanup: bool = True) -> FinalVideo:
    """Run pipeline that outputs only audio (when PEXELS_API_KEY is not set)."""
    
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
        
        # Copy the audio file to output
        shutil.copy2(audio_path, output_file)
        
        # Get audio duration
        from pdf2video.tts_engine import _estimate_duration_seconds
        duration = _estimate_duration_seconds(script)
        
        final_video = FinalVideo(
            file_path=output_file,
            duration=duration,
            resolution=(0, 0)  # No video, just audio
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


def _run_full_pipeline(input_path: str, output_path: str, cleanup: bool = True) -> FinalVideo:
    """Run the full pipeline with video generation."""
    
    total_steps = 6
    text = ""
    script = ""
    clips: list[VideoClip] = []
    final_video: FinalVideo | None = None
    downloaded_clips: list[VideoClip] = []
    temp_dir = Path(tempfile.mkdtemp(prefix="pdf2video_"))
    audio_path = temp_dir / "narration.mp3"
    video_cache_dir = temp_dir / "videos"
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

        logger.info("[3/%s] Converting script to audio...", total_steps)
        try:
            text_to_speech(script, str(audio_path))
        except Exception as exc:
            _raise_stage_error("text-to-speech", exc)

        logger.info("[4/%s] Searching for video clips...", total_steps)
        query = _build_search_query(script)
        try:
            clips = search_videos(query)
            if not clips:
                raise PipelineError(f"Failed at step video search: no clips found for query '{query}'")
        except PipelineError:
            raise
        except Exception as exc:
            _raise_stage_error("video search", exc)

        logger.info("[5/%s] Downloading video clips...", total_steps)
        try:
            for clip in clips:
                downloaded_clips.append(download_video(clip, cache_dir=str(video_cache_dir)))
        except Exception as exc:
            _raise_stage_error("video download", exc)

        logger.info("[6/%s] Composing final video...", total_steps)
        try:
            final_video = compose_video(str(audio_path), downloaded_clips, output_path)
        except Exception as exc:
            _raise_stage_error("video composition", exc)

        if final_video is None:
            raise PipelineError("Failed at step video composition: empty composition result")

        logger.info("Pipeline completed successfully: %s", final_video.file_path)
        return final_video
    finally:
        if cleanup:
            try:
                _cleanup_intermediate_files(audio_path, downloaded_clips, temp_dir)
            except Exception as exc:
                logger.warning("Failed to clean intermediate files: %s", exc)
