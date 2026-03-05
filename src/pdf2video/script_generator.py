from __future__ import annotations

import logging
import os
import importlib
import time
from typing import Any, List

from pdf2video.extractor import extract_text
logger = logging.getLogger(__name__)


MAX_TOKENS_PER_CHUNK = 8000
CHARS_PER_TOKEN_ESTIMATE = 4
MAX_CHARS_PER_CHUNK = MAX_TOKENS_PER_CHUNK * CHARS_PER_TOKEN_ESTIMATE
# DeepSeek API configuration
DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_API_BASE = "https://api.deepseek.com"

PROMPT_TEMPLATES = {
    "research": (
        "You are an expert science communicator creating narration for a research video. "
        "Turn the provided source content into a clear spoken script. "
        "Keep factual accuracy, explain jargon briefly, and preserve key claims, methods, "
        "and outcomes. Use a confident, engaging tone suitable for voice-over. "
        "Do not use bullet points, markdown, or stage directions."
    )
}


class ScriptGenerationError(Exception):
    pass


def _create_client() -> Any:
    dotenv = importlib.import_module("dotenv")
    openai = importlib.import_module("openai")

    dotenv.load_dotenv()
    # Support both DEEPSEEK_API_KEY and legacy OPENAI_API_KEY
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ScriptGenerationError("DEEPSEEK_API_KEY or OPENAI_API_KEY environment variable is not set")
    # Configure OpenAI client to use DeepSeek API endpoint
    return openai.OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_API_BASE
    )


def _chunk_content(content: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    text = content.strip()
    if not text:
        return []

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = start + max_chars
            chunks.append(paragraph[start:end])
            start = end

    if current:
        chunks.append(current)

    return chunks


def generate_script(content: str, style: str = "research") -> str:
    logger.info("Starting script generation with style: %s", style)
    if not content or not content.strip():
        logger.error("Cannot generate script from empty content")
        raise ScriptGenerationError("Cannot generate script from empty content")

    prompt_template = PROMPT_TEMPLATES.get(style)
    if prompt_template is None:
        logger.error("Unsupported script style: %s", style)
        raise ScriptGenerationError(f"Unsupported script style: {style}")

    client = _create_client()
    chunks = _chunk_content(content)
    logger.info("Split content into %d chunks for processing", len(chunks))
    script_parts: List[str] = []

    max_retries = 3
    try:
        for index, chunk in enumerate(chunks, start=1):
            logger.debug("Processing chunk %d/%d (length: %d chars)", index, len(chunks), len(chunk))
            user_prompt = (
                f"Source content chunk {index}/{len(chunks)}:\n\n{chunk}\n\n"
                "Write only the narration text for this chunk."
            )
            
            # Retry logic for DeepSeek API call
            last_exception = None
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=DEFAULT_MODEL,
                        messages=[
                            {"role": "system", "content": prompt_template},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.7,
                    )
                    message = response.choices[0].message.content
                    if not message:
                        raise ScriptGenerationError("DeepSeek returned an empty response")
                    script_parts.append(message.strip())
                    logger.info("Generated script for chunk %d/%d (%d chars)", index, len(chunks), len(message))
                    break  # Success, exit retry loop
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            "DeepSeek API call failed (attempt %d/%d): %s. Retrying in %ds...",
                            attempt + 1, max_retries, exc, wait_time
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error("DeepSeek API call failed after %d attempts", max_retries)
                        raise ScriptGenerationError(f"Failed to generate script chunk {index}/{len(chunks)}: {exc}") from exc
    except ScriptGenerationError:
        raise
    except Exception as exc:
        logger.error("Unexpected error during script generation: %s", exc)
        raise ScriptGenerationError(f"Failed to generate script: {exc}") from exc

    total_length = len("\n\n".join(script_parts))
    logger.info("Script generation complete: %d chunks, %d total chars", len(script_parts), total_length)
    return "\n\n".join(script_parts)


def generate_script_from_pdf(pdf_path: str) -> str:
    logger.info("Generating script from PDF: %s", pdf_path)
    try:
        content = extract_text(pdf_path)
        return generate_script(content)
    except ScriptGenerationError:
        raise
    except Exception as exc:
        logger.error("Failed to generate script from PDF '%s': %s", pdf_path, exc)
        raise ScriptGenerationError(f"Failed to generate script from PDF: {exc}") from exc


def generate_script_from_txt(txt_path: str) -> str:
    """Generate script from a TXT file containing narration content."""
    logger.info("Generating script from TXT file: %s", txt_path)
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content or not content.strip():
            raise ScriptGenerationError("TXT file is empty")
        return generate_script(content)
    except ScriptGenerationError:
        raise
    except Exception as exc:
        logger.error("Failed to generate script from TXT '%s': %s", txt_path, exc)
        raise ScriptGenerationError(f"Failed to generate script from TXT: {exc}") from exc
