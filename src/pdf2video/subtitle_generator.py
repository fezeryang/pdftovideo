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

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_API_BASE = "https://api.deepseek.com"
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
    normalized = re.sub(r"\s+", " ", script.strip())
    if not normalized:
        return []
    sentences = [segment.strip() for segment in _SENTENCE_BOUNDARY.split(normalized) if segment.strip()]
    return sentences or [normalized]


def _segment_style(text: str) -> str:
    return "emphasis" if "!" in text else "default"


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


def generate_subtitles(script: str, audio_duration: float) -> list[SubtitleSegment]:
    if audio_duration <= 0:
        raise ValueError("audio_duration must be positive")

    sentences = _split_script_into_segments(script)
    if not sentences:
        return []

    estimated_durations: list[float] = []
    for sentence in sentences:
        start, end = estimate_segment_timing(sentence, 0.0)
        estimated_durations.append(max(0.0, end - start))

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
                text=sentence,
                start_time=round(current_time, 3),
                end_time=round(max(end_time, current_time), 3),
                style=_segment_style(sentence),
            )
        )
        current_time = end_time

    return segments


def export_to_ass(
    segments: list[SubtitleSegment], output_path: Path, config: SubtitleConfig
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_ass = rgb_to_ass_color(*config.color)
    outline_ass = rgb_to_ass_color(*config.outline_color)
    emphasis_ass = rgb_to_ass_color(*_emphasis_rgb(config.color))

    default_style = pysubs2.SSAStyle(
        fontname=Path(config.font_path).stem,
        fontsize=float(config.font_size),
        primarycolor=_ass_hex_to_color(base_ass),
        outlinecolor=_ass_hex_to_color(outline_ass),
        alignment=_map_alignment(config.position),
        outline=2.0,
        shadow=1.0,
    )
    emphasis_style = pysubs2.SSAStyle(
        fontname=Path(config.font_path).stem,
        fontsize=float(config.font_size),
        primarycolor=_ass_hex_to_color(emphasis_ass),
        outlinecolor=_ass_hex_to_color(outline_ass),
        alignment=_map_alignment(config.position),
        outline=2.0,
        shadow=1.0,
        bold=True,
    )

    subs = pysubs2.SSAFile()
    subs.info["Title"] = "PDF2Video Subtitles"
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
