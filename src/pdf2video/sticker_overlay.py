"""Sticker overlay functionality for video composition.

This module provides functions to load and configure sticker overlays
(PNG images and GIF animations) for video composition.
"""

from __future__ import annotations

import importlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, List, Tuple, Union

import requests

from pdf2video.types import StickerConfig, StickerType

logger = logging.getLogger(__name__)


class StickerError(Exception):
    """Exception raised when sticker loading or processing fails."""
    pass


# Position keyword mapping: keyword -> (horizontal, vertical)
POSITION_KEYWORDS = {
    "center": ("center", "center"),
    "top": ("center", "top"),
    "bottom": ("center", "bottom"),
    "left": ("left", "center"),
    "right": ("right", "center"),
    "top-left": ("left", "top"),
    "top-right": ("right", "top"),
    "bottom-left": ("left", "bottom"),
    "bottom-right": ("right", "bottom"),
}


def _load_moviepy_ImageClip(path: str) -> Any:
    """Lazily load and create an ImageClip from moviepy."""
    moviepy = importlib.import_module("moviepy")
    return moviepy.ImageClip(path)


def _load_moviepy_VideoFileClip(path: str) -> Any:
    """Lazily load and create a VideoFileClip from moviepy."""
    moviepy = importlib.import_module("moviepy")
    return moviepy.VideoFileClip(path)


def _resolve_position(position: Union[Tuple[int, int], str]) -> Union[Tuple[int, int], Tuple[str, str]]:
    """Resolve position to MoviePy-compatible format.
    
    Args:
        position: Either (x, y) tuple or position keyword string
        
    Returns:
        Position tuple compatible with MoviePy's with_position()
        
    Raises:
        StickerError: If position keyword is invalid
    """
    if isinstance(position, tuple):
        return position
    
    if position in POSITION_KEYWORDS:
        return POSITION_KEYWORDS[position]
    
    raise StickerError(f"Invalid position keyword: '{position}'. Valid keywords: {list(POSITION_KEYWORDS.keys())}")


def _download_url_sticker(url: str) -> Tuple[str, str]:
    """Download sticker from URL to temporary file.
    
    Args:
        url: URL of the sticker to download
        
    Returns:
        Tuple of (temp_file_path, file_extension)
        
    Raises:
        StickerError: If download fails
    """
    logger.debug("Downloading sticker from URL: %s", url)
    
    # Determine extension from URL
    url_path = url.split("?")[0]  # Remove query params
    extension = Path(url_path).suffix.lower() or ".png"
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temp file with appropriate suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
        
        temp_file.close()
        logger.debug("Sticker downloaded to: %s", temp_file.name)
        return temp_file.name, extension
        
    except requests.RequestException as e:
        raise StickerError(f"Failed to download sticker from URL: {e}") from e


def load_sticker(config: StickerConfig) -> Any:
    """Load a sticker as a MoviePy clip.
    
    Supports PNG images, GIF animations, and URL-based stickers.
    
    Args:
        config: StickerConfig with path, type, position, timing, and scale
        
    Returns:
        MoviePy clip (ImageClip for PNG, VideoFileClip for GIF)
        configured with position, duration (PNG only), and scaling
        
    Raises:
        StickerError: If sticker file not found, download fails, or config invalid
    """
    # Validate duration
    duration = config.end_time - config.start_time
    if duration <= 0:
        raise StickerError(
            f"Invalid sticker duration: {duration}s (start={config.start_time}, end={config.end_time})"
        )
    
    # Determine file path and type
    sticker_path: str
    actual_type: StickerType
    
    if config.sticker_type == StickerType.URL:
        # Download URL sticker to temp file
        sticker_path, extension = _download_url_sticker(config.path)
        # Determine type from extension
        if extension.lower() == ".gif":
            actual_type = StickerType.GIF
        else:
            actual_type = StickerType.PNG
    else:
        sticker_path = config.path
        actual_type = config.sticker_type
        
        # Verify local file exists
        if not Path(sticker_path).exists():
            raise StickerError(f"Sticker file not found: {sticker_path}")
    
    # Load clip based on type
    clip: Any
    
    if actual_type == StickerType.PNG:
        logger.debug("Loading PNG sticker: %s", sticker_path)
        clip = _load_moviepy_ImageClip(sticker_path)
        # CRITICAL: PNG must have duration set or MoviePy crashes
        clip = clip.with_duration(duration)
        
    elif actual_type == StickerType.GIF:
        logger.debug("Loading GIF sticker: %s", sticker_path)
        # GIF must use VideoFileClip for animation support
        clip = _load_moviepy_VideoFileClip(sticker_path)
        # GIF has its own duration, don't override
        
    else:
        raise StickerError(f"Unsupported sticker type: {config.sticker_type}")
    
    # Apply scaling if needed
    if config.scale != 1.0:
        new_width = int(clip.w * config.scale)
        logger.debug("Scaling sticker to width=%d (scale=%.2f)", new_width, config.scale)
        clip = clip.resized(width=new_width)
    
    # Apply position
    resolved_position = _resolve_position(config.position)
    logger.debug("Setting sticker position: %s", resolved_position)
    clip = clip.with_position(resolved_position)
    
    return clip


def parse_sticker_config_dict(config: dict) -> StickerConfig:
    """Parse a single sticker configuration dictionary.
    
    Args:
        config: Dictionary containing sticker configuration with keys:
            - path (str): File path or URL to sticker
            - position (str or list): Position keyword or [x, y] coordinates
            - start_time (float): Start time in seconds
            - end_time (float): End time in seconds
            - scale (float, optional): Scale factor (default 1.0)
    
    Returns:
        StickerConfig object
    
    Raises:
        KeyError: If required fields are missing
    """
    # Extract required fields (will raise KeyError if missing)
    path = config["path"]
    position = config["position"]
    start_time = config["start_time"]
    end_time = config["end_time"]
    
    # Optional field with default
    scale = config.get("scale", 1.0)
    
    # Detect sticker type from path
    if path.startswith("http://") or path.startswith("https://"):
        sticker_type = StickerType.URL
    elif path.endswith(".gif"):
        sticker_type = StickerType.GIF
    else:
        sticker_type = StickerType.PNG
    
    return StickerConfig(
        path=path,
        sticker_type=sticker_type,
        position=position,
        start_time=start_time,
        end_time=end_time,
        scale=scale
    )


def parse_sticker_config(json_path: Path) -> list[StickerConfig]:
    """Parse sticker configuration from JSON file.
    
    Args:
        json_path: Path to JSON configuration file
    
    Returns:
        List of StickerConfig objects
    
    Raises:
        ValueError: If more than 5 stickers are specified
        KeyError: If required fields are missing
        json.JSONDecodeError: If JSON is invalid
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    stickers = data["stickers"]
    
    # Enforce memory limit: max 5 stickers
    if len(stickers) > 5:
        raise ValueError("Max 5 stickers allowed")
    
    return [parse_sticker_config_dict(s) for s in stickers]
