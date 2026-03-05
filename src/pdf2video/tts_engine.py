from __future__ import annotations

import importlib
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, List, Optional

from pdf2video.types import TTSAudio
logger = logging.getLogger(__name__)


DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MAX_CHARS_PER_REQUEST = 4000
WORDS_PER_SECOND = 2.5


class TTSError(Exception):
    pass


def _create_client() -> Any:
    dotenv = importlib.import_module("dotenv")
    elevenlabs = importlib.import_module("elevenlabs")

    dotenv.load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise TTSError("ELEVENLABS_API_KEY environment variable is not set")

    return elevenlabs.ElevenLabs(api_key=api_key)


def _chunk_text_for_tts(text: str, max_chars: int = MAX_CHARS_PER_REQUEST) -> List[str]:
    normalized = text.strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in normalized.split("\n\n") if part.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        for sentence in _split_paragraph(paragraph, max_chars=max_chars):
            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def _split_paragraph(paragraph: str, max_chars: int) -> List[str]:
    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", paragraph) if segment.strip()]
    if not sentences:
        sentences = [paragraph]

    output: List[str] = []
    for sentence in sentences:
        if len(sentence) <= max_chars:
            output.append(sentence)
            continue

        words = sentence.split()
        if not words:
            continue

        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                output.append(current)

            if len(word) <= max_chars:
                current = word
                continue

            start = 0
            while start < len(word):
                end = start + max_chars
                output.append(word[start:end])
                start = end
            current = ""

        if current:
            output.append(current)

    return output


def _audio_bytes_from_response(response: Any) -> bytes:
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)

    audio_parts: List[bytes] = []

    if hasattr(response, "read"):
        data = response.read()
        if isinstance(data, (bytes, bytearray)):
            audio_parts.append(bytes(data))

    if hasattr(response, "__iter__"):
        for part in response:
            if isinstance(part, (bytes, bytearray)):
                audio_parts.append(bytes(part))

    if not audio_parts:
        raise TTSError("ElevenLabs returned empty audio data")

    return b"".join(audio_parts)


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _combine_audio_chunks(chunk_paths: List[Path], output_path: Path) -> None:
    if not chunk_paths:
        raise TTSError("No audio chunks available for combination")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as merged_audio:
        for chunk_path in chunk_paths:
            merged_audio.write(chunk_path.read_bytes())


def _estimate_duration_seconds(text: str) -> float:
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    return round(word_count / WORDS_PER_SECOND, 2)


def text_to_speech(text: str, output_path: str, voice_id: Optional[str] = None) -> TTSAudio:
    logger.info("Starting text-to-speech synthesis (output: %s)", output_path)
    if not text or not text.strip():
        logger.error("Cannot synthesize empty text")
        raise TTSError("Cannot synthesize empty text")

    chunks = _chunk_text_for_tts(text)
    if not chunks:
        logger.error("No text chunks available for synthesis")
        raise TTSError("No text chunks available for synthesis")
    
    logger.info("Split text into %d chunks for TTS processing", len(chunks))

    output_file = Path(output_path)
    selected_voice_id = voice_id or DEFAULT_VOICE_ID
    logger.debug("Using voice ID: %s", selected_voice_id)
    client = _create_client()
    max_retries = 3
    try:
        if len(chunks) == 1:
            logger.debug("Processing single-chunk audio")
            # Retry logic for single chunk
            for attempt in range(max_retries):
                try:
                    response = client.text_to_speech.convert(
                        voice_id=selected_voice_id,
                        text=chunks[0],
                        model_id=DEFAULT_MODEL_ID,
                        output_format=DEFAULT_OUTPUT_FORMAT,
                    )
                    _write_bytes(output_file, _audio_bytes_from_response(response))
                    logger.info("Single-chunk audio generated successfully")
                    break
                except Exception as exc:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            "ElevenLabs API call failed (attempt %d/%d): %s. Retrying in %ds...",
                            attempt + 1, max_retries, exc, wait_time
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error("ElevenLabs API call failed after %d attempts", max_retries)
                        raise TTSError(f"Failed to generate speech audio: {exc}") from exc
        else:
            logger.debug("Processing multi-chunk audio (%d chunks)", len(chunks))
            with tempfile.TemporaryDirectory() as temp_dir:
                chunk_paths: List[Path] = []
                for index, chunk in enumerate(chunks, start=1):
                    logger.debug("Processing audio chunk %d/%d", index, len(chunks))
                    
                    # Retry logic for each chunk
                    for attempt in range(max_retries):
                        try:
                            response = client.text_to_speech.convert(
                                voice_id=selected_voice_id,
                                text=chunk,
                                model_id=DEFAULT_MODEL_ID,
                                output_format=DEFAULT_OUTPUT_FORMAT,
                            )
                            chunk_path = Path(temp_dir) / f"chunk_{index:04d}.mp3"
                            _write_bytes(chunk_path, _audio_bytes_from_response(response))
                            chunk_paths.append(chunk_path)
                            logger.info("Generated audio chunk %d/%d", index, len(chunks))
                            break
                        except Exception as exc:
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt
                                logger.warning(
                                    "ElevenLabs API call failed for chunk %d (attempt %d/%d): %s. Retrying in %ds...",
                                    index, attempt + 1, max_retries, exc, wait_time
                                )
                                time.sleep(wait_time)
                            else:
                                logger.error("ElevenLabs API call failed for chunk %d after %d attempts", index, max_retries)
                                raise TTSError(f"Failed to generate audio chunk {index}/{len(chunks)}: {exc}") from exc

                logger.info("Combining %d audio chunks", len(chunk_paths))
                _combine_audio_chunks(chunk_paths, output_file)

        duration = _estimate_duration_seconds(text)
        logger.info("TTS synthesis complete: duration=%.2fs, file=%s", duration, output_file)
        return TTSAudio(
            file_path=output_file,
            duration=duration,
            voice_id=selected_voice_id,
        )
    except TTSError:
        raise
    except Exception as exc:
        logger.error("Unexpected error during TTS synthesis: %s", exc)
        raise TTSError(f"Failed to generate speech audio: {exc}") from exc
