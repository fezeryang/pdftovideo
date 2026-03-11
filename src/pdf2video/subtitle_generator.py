from __future__ import annotations

import importlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from pdf2video.subtitle_utils import estimate_segment_timing, rgb_to_ass_color
from pdf2video.types import SubtitleConfig, SubtitleSegment

pysubs2 = importlib.import_module("pysubs2")

_PUNCTUATION_BOUNDARIES = frozenset("。！？；：，.!?;:,")
_DEFAULT_MIN_DURATION_SECONDS = float(SubtitleConfig.__dataclass_fields__["min_duration"].default)
_DEFAULT_MAX_DURATION_SECONDS = float(SubtitleConfig.__dataclass_fields__["max_duration"].default)
_DEFAULT_MAX_LINES = int(SubtitleConfig.__dataclass_fields__["max_lines"].default)
_DEFAULT_MAX_CHARS_PER_LINE = int(SubtitleConfig.__dataclass_fields__["max_chars_per_line"].default)
_FALLBACK_SPLIT_TRIGGER_CHARS = 48
_FALLBACK_TARGET_CHARS = 24

logger = logging.getLogger(__name__)

#KK|# Read from environment variables with fallbacks
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
KEYWORD_PROMPT = (
    "You are an expert at extracting key terms from video scripts. Extract 3-10 important keywords (names, "
    "technical terms, numbers, key concepts) that should be visually emphasized in subtitles. Return ONLY a "
    "JSON array of strings."
)


def _create_client() -> Any:
    dotenv = importlib.import_module("dotenv")
    openai = importlib.import_module("openai")
    dotenv.load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable is not set")

    return openai.OpenAI(api_key=api_key, base_url=DEEPSEEK_API_BASE)


def detect_keywords_for_emphasis(script: str) -> list[str]:
    if not script.strip():
        return []

    try:
        client = _create_client()
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": KEYWORD_PROMPT},
                {"role": "user", "content": f"Script:\n{script}"},
            ],
            temperature=0.2,
            timeout=30,
        )
        content = response.choices[0].message.content
    except Exception as exc:
        logger.warning("Keyword detection failed: %s", exc)
        return []

    try:
        parsed = json.loads(content or "[]")
    except Exception as exc:
        logger.warning("Keyword detection failed: invalid response format: %s", exc)
        return []

    if not isinstance(parsed, list):
        logger.warning("Keyword detection failed: invalid response type")
        return []

    keywords = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
    if len(keywords) < 3:
        return []
    return keywords[:10]


def apply_emphasis_to_segments(
    segments: list[SubtitleSegment], keywords: list[str]
) -> list[SubtitleSegment]:
    normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword and keyword.strip()]
    emphasized: list[SubtitleSegment] = []

    for segment in segments:
        text_lower = segment.text.lower()
        has_keyword = any(keyword in text_lower for keyword in normalized_keywords)
        emphasized.append(
            SubtitleSegment(
                text=segment.text,
                start_time=segment.start_time,
                end_time=segment.end_time,
                style="emphasis" if has_keyword else segment.style,
            )
        )

    return emphasized


def _split_script_into_segments(script: str) -> list[str]:
    raw = script.strip()
    if not raw:
        return []

    punctuation_segments: list[str] = []
    buffer: list[str] = []
    for char in raw:
        if char == "\n":
            if buffer and buffer[-1] != " ":
                buffer.append(" ")
            continue

        if char.isspace():
            if buffer and buffer[-1] != " ":
                buffer.append(" ")
            continue

        buffer.append(char)
        should_split = char in _PUNCTUATION_BOUNDARIES
        if char == "," and (not buffer or not re.search(r"[\u4e00-\u9fff]", "".join(buffer))):
            should_split = False

        if should_split:
            segment = "".join(buffer).strip()
            if segment:
                punctuation_segments.append(segment)
            buffer = []

    if buffer:
        trailing = "".join(buffer).strip()
        if trailing:
            punctuation_segments.append(trailing)

    if len(punctuation_segments) > 1:
        return punctuation_segments

    if punctuation_segments and any(char in _PUNCTUATION_BOUNDARIES for char in raw):
        return punctuation_segments

    line_segments = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines() if line.strip()]
    if len(line_segments) > 1:
        return line_segments

    normalized = re.sub(r"\s+", " ", raw)
    if len(normalized) <= _FALLBACK_SPLIT_TRIGGER_CHARS:
        return [normalized]

    fallback_segments: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        remaining = len(normalized) - cursor
        if remaining <= _FALLBACK_TARGET_CHARS:
            chunk = normalized[cursor:].strip()
            if chunk:
                fallback_segments.append(chunk)
            break

        end = min(len(normalized), cursor + _FALLBACK_TARGET_CHARS)
        split_at = normalized.rfind(" ", cursor + (_FALLBACK_TARGET_CHARS // 2), end)
        if split_at <= cursor:
            split_at = end

        chunk = normalized[cursor:split_at].strip()
        if chunk:
            fallback_segments.append(chunk)
        cursor = split_at
        while cursor < len(normalized) and normalized[cursor] == " ":
            cursor += 1

    return fallback_segments or [normalized]


def _segment_style(text: str) -> str:
    return "emphasis" if "!" in text else "default"


def _line_with_ellipsis(line: str, max_chars_per_line: int) -> str:
    if max_chars_per_line <= 0:
        return ""
    if max_chars_per_line <= 3:
        return "." * max_chars_per_line
    stripped = line.strip()
    if len(stripped) > max_chars_per_line - 3:
        stripped = stripped[: max_chars_per_line - 3].rstrip()
    return f"{stripped}..."


def wrap_text_to_lines(text: str, max_lines: int, max_chars_per_line: int) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized or max_lines <= 0 or max_chars_per_line <= 0:
        return ""

    words = normalized.split(" ")
    lines: list[str] = []
    current = ""
    overflowed = False

    def append_line(value: str) -> bool:
        nonlocal overflowed
        if len(lines) >= max_lines:
            overflowed = True
            return False
        lines.append(value)
        return True

    for word in words:
        if not word:
            continue

        if len(word) > max_chars_per_line:
            if current:
                if not append_line(current):
                    break
                current = ""

            start = 0
            while start < len(word):
                chunk = word[start : start + max_chars_per_line]
                start += max_chars_per_line
                if start < len(word):
                    if not append_line(chunk):
                        break
                else:
                    current = chunk

            if overflowed:
                break
            continue

        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars_per_line:
            current = candidate
            continue

        punctuation_index = max(current.rfind(mark) for mark in ",;:，；：") if current else -1
        if punctuation_index > 0:
            preferred = current[: punctuation_index + 1].strip()
            remainder = current[punctuation_index + 1 :].strip()
            if preferred and len(preferred) <= max_chars_per_line:
                if not append_line(preferred):
                    break
                current = f"{remainder} {word}".strip() if remainder else word
                continue

        if not append_line(current):
            break
        current = word

    if not overflowed and current:
        append_line(current)

    if not lines:
        return ""

    if overflowed:
        lines[-1] = _line_with_ellipsis(lines[-1], max_chars_per_line)

    return "\\N".join(lines)


def _ass_hex_to_color(ass_color: str) -> Any:
    hex_value = ass_color[2:-1]
    b = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    r = int(hex_value[4:6], 16)
    return pysubs2.Color(r=r, g=g, b=b)


def _emphasis_rgb(base_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = base_rgb
    emphasized = (
        min(255, int(r * 1.12 + 24)),
        min(255, int(g * 1.03 + 8)),
        max(0, int(b * 0.82)),
    )
    if emphasized == base_rgb:
        return (min(255, r + 40), max(0, g - 20), max(0, b - 20))
    return emphasized


def _map_alignment(position: str) -> Any:
    normalized = position.strip().lower()
    mapping = {
        "bottom": pysubs2.Alignment.BOTTOM_CENTER,
        "top": pysubs2.Alignment.TOP_CENTER,
        "center": pysubs2.Alignment.MIDDLE_CENTER,
        "top-left": pysubs2.Alignment.TOP_LEFT,
        "top-right": pysubs2.Alignment.TOP_RIGHT,
        "bottom-left": pysubs2.Alignment.BOTTOM_LEFT,
        "bottom-right": pysubs2.Alignment.BOTTOM_RIGHT,
    }
    return mapping.get(normalized, pysubs2.Alignment.BOTTOM_CENTER)


def generate_subtitles(
    script: str,
    audio_duration: float,
    config: SubtitleConfig | None = None,
) -> list[SubtitleSegment]:
    if audio_duration <= 0:
        raise ValueError("audio_duration must be positive")

    sentences = _split_script_into_segments(script)
    if not sentences:
        return []

    min_duration = config.min_duration if config else _DEFAULT_MIN_DURATION_SECONDS
    max_duration = config.max_duration if config else _DEFAULT_MAX_DURATION_SECONDS
    max_lines = config.max_lines if config else _DEFAULT_MAX_LINES
    max_chars_per_line = config.max_chars_per_line if config else _DEFAULT_MAX_CHARS_PER_LINE
    should_wrap_text = config is not None
    should_duration_split = config is None

    estimated_durations: list[float] = []
    while should_duration_split:
        estimated_durations = []
        for sentence in sentences:
            start, end = estimate_segment_timing(sentence, 0.0)
            estimated_durations.append(max(0.0, end - start))

        total_estimated = sum(estimated_durations)
        if total_estimated <= 0:
            estimated_durations = [1.0 for _ in sentences]
            total_estimated = float(len(sentences))

        scale_preview = audio_duration / total_estimated
        split_index = next(
            (
                i
                for i, estimated in enumerate(estimated_durations)
                if (estimated * scale_preview) > max_duration
            ),
            -1,
        )
        if split_index < 0:
            break

        oversized = sentences[split_index]
        splits = _split_script_into_segments(oversized)
        if len(splits) <= 1:
            midpoint = max(1, len(oversized) // 2)
            left = oversized[:midpoint].strip()
            right = oversized[midpoint:].strip()
            splits = [piece for piece in (left, right) if piece]
            if len(splits) <= 1:
                break
        sentences = sentences[:split_index] + splits + sentences[split_index + 1 :]

    total_estimated = sum(estimated_durations)
    if total_estimated <= 0:
        estimated_durations = [1.0 for _ in sentences]
        total_estimated = float(len(sentences))

    scale = audio_duration / total_estimated
    segments: list[SubtitleSegment] = []
    current_time = 0.0

    for index, sentence in enumerate(sentences):
        scaled_duration = estimated_durations[index] * scale
        end_time = audio_duration if index == len(sentences) - 1 else current_time + scaled_duration
        segments.append(
            SubtitleSegment(
                text=(
                    wrap_text_to_lines(sentence, max_lines=max_lines, max_chars_per_line=max_chars_per_line)
                    if should_wrap_text
                    else sentence
                ),
                start_time=round(current_time, 3),
                end_time=round(max(end_time, current_time), 3),
                style=_segment_style(sentence),
            )
        )
        duration = end_time - current_time
        clamped_duration = max(min_duration, min(max_duration, duration))
        if abs(clamped_duration - duration) > 1e-9:
            logger.warning(
                "duration clamped for segment %s from %.3fs to %.3fs",
                index,
                duration,
                clamped_duration,
            )
        segment_end = current_time + clamped_duration
        segments[-1].end_time = round(max(segment_end, current_time), 3)
        current_time = segment_end

    return segments


def export_to_ass(
    segments: list[SubtitleSegment],
    output_path: Path,
    config: SubtitleConfig,
    resolution: tuple[int, int] = (1920, 1080),
) -> Path:
    # Calculate resolution-aware margins
    resolution_width, resolution_height = resolution
    margin_v = max(50, int(resolution_height * config.bottom_margin_ratio))
    # Left/right margins: 5% of width to prevent text overflow
    margin_lr = int(resolution_width * 0.05)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_ass = rgb_to_ass_color(*config.color)
    outline_ass = rgb_to_ass_color(*config.outline_color)
    emphasis_ass = rgb_to_ass_color(*_emphasis_rgb(config.color))

    # Force bottom-center alignment for proper subtitle placement
    default_style = pysubs2.SSAStyle(
        fontname=Path(config.font_path).stem if config.font_path else "Arial",
        fontsize=float(config.font_size),
        primarycolor=_ass_hex_to_color(base_ass),
        outlinecolor=_ass_hex_to_color(outline_ass),
        alignment=pysubs2.Alignment.BOTTOM_CENTER,
        outline=2.0,
        shadow=1.0,
        marginv=margin_v,
        marginl=margin_lr,
        marginr=margin_lr,
    )
    emphasis_style = pysubs2.SSAStyle(
        fontname=Path(config.font_path).stem if config.font_path else "Arial",
        fontsize=float(config.font_size),
        primarycolor=_ass_hex_to_color(emphasis_ass),
        outlinecolor=_ass_hex_to_color(outline_ass),
        alignment=pysubs2.Alignment.BOTTOM_CENTER,
        outline=2.0,
        shadow=1.0,
        bold=True,
        marginv=margin_v,
        marginl=margin_lr,
        marginr=margin_lr,
    )

    subs = pysubs2.SSAFile()
    subs.info["Title"] = "PDF2Video Subtitles"
    subs.info["PlayResX"] = str(resolution_width)
    subs.info["PlayResY"] = str(resolution_height)
    subs.styles["Default"] = default_style
    subs.styles["Emphasis"] = emphasis_style

    for segment in segments:
        style_name = "Emphasis" if segment.style.lower() == "emphasis" else "Default"
        start_ms = int(round(segment.start_time * 1000))
        end_ms = int(round(segment.end_time * 1000))
        subs.events.append(
            pysubs2.SSAEvent(
                start=max(0, start_ms),
                end=max(start_ms, end_ms),
                text=segment.text,
                style=style_name,
            )
        )

    subs.save(str(output_path), format_="ass")
    return output_path
