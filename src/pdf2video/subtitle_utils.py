"""Subtitle utility functions for ASS format and timing estimation.

This module provides utilities for:
- Converting between RGB and ASS color formats (BGR)
- Estimating subtitle segment timing based on word count
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pdf2video.types import SubtitleError

# Constants
WORDS_PER_SECOND = 2.5  # Speech rate for timing estimation


def rgb_to_ass_color(r: int, g: int, b: int) -> str:
    """Convert RGB color to ASS BGR color format.
    
    ASS subtitle format uses BGR (Blue-Green-Red) instead of RGB.
    The format is &HBBGGRR& where BB, GG, RR are 2-digit hex values.
    
    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)
        
    Returns:
        ASS color string in format &HBBGGRR&
        
    Raises:
        ValueError: If any RGB value is not between 0 and 255
        
    Examples:
        >>> rgb_to_ass_color(255, 0, 0)  # Red
        '&H0000FF&'
        >>> rgb_to_ass_color(0, 255, 0)  # Green
        '&H00FF00&'
        >>> rgb_to_ass_color(0, 0, 255)  # Blue
        '&HFF0000&'
    """
    # Validate input ranges
    if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
        raise ValueError("RGB values must be between 0 and 255")
    
    # Convert to BGR format: &HBBGGRR&
    return f"&H{b:02X}{g:02X}{r:02X}&"


def ass_color_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert ASS BGR color format to RGB tuple.
    
    Reverses the conversion from rgb_to_ass_color().
    
    Args:
        color: ASS color string in format &HBBGGRR& (case-insensitive)
        
    Returns:
        Tuple of (r, g, b) values (0-255)
        
    Raises:
        ValueError: If color string is not in valid ASS format
        
    Examples:
        >>> ass_color_to_rgb('&H0000FF&')  # Red
        (255, 0, 0)
        >>> ass_color_to_rgb('&H00FF00&')  # Green
        (0, 255, 0)
        >>> ass_color_to_rgb('&HFF0000&')  # Blue
        (0, 0, 255)
    """
    # Validate format
    if not color:
        raise ValueError("Invalid ASS color format: empty string")
    
    # Normalize to uppercase
    color = color.upper()
    
    # Check format: &HXXXXXX&
    if not (color.startswith("&H") and color.endswith("&") and len(color) == 9):
        raise ValueError(f"Invalid ASS color format: {color}")
    
    # Extract hex value (remove &H and &)
    hex_value = color[2:-1]
    
    # Validate hex string length
    if len(hex_value) != 6:
        raise ValueError(f"Invalid ASS color format: {color}")
    
    try:
        # Parse BGR components
        b = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        r = int(hex_value[4:6], 16)
        return (r, g, b)
    except ValueError as e:
        raise ValueError(f"Invalid ASS color format: {color}") from e


def estimate_segment_timing(text: str, start_time: float) -> tuple[float, float]:
    """Estimate subtitle segment timing based on word count.
    
    Uses WORDS_PER_SECOND constant to calculate duration.
    
    Args:
        text: The subtitle text to time
        start_time: Start time in seconds (must be non-negative)
        
    Returns:
        Tuple of (start_time, end_time) in seconds
        
    Raises:
        ValueError: If start_time is negative
        
    Examples:
        >>> estimate_segment_timing("This is test", 0.0)
        (0.0, 1.2)  # 3 words / 2.5 WPS = 1.2s
        >>> estimate_segment_timing("One two three four five", 10.0)
        (10.0, 12.0)  # 5 words / 2.5 WPS = 2.0s
    """
    # Validate start time
    if start_time < 0:
        raise ValueError("Start time must be non-negative")
    
    # Count words (split by whitespace)
    word_count = len(text.split())
    
    # Calculate duration based on word count
    duration = word_count / WORDS_PER_SECOND
    
    # Return start and end times
    end_time = start_time + duration
    return (start_time, end_time)


def check_ffmpeg_available() -> bool:
    """Check if FFmpeg is installed and available in PATH.
    
    Returns:
        True if FFmpeg is available, False otherwise
    
    Example:
        >>> check_ffmpeg_available()
        True  # If FFmpeg is installed
    """
    return shutil.which("ffmpeg") is not None


def burn_subtitles_ffmpeg(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
) -> Path:
    """Burn ASS subtitles into video using FFmpeg.
    
    Uses FFmpeg's ASS subtitle filter to permanently embed subtitles.
    Audio stream is copied without re-encoding for speed.
    
    Args:
        video_path: Path to input video file
        ass_path: Path to ASS subtitle file
        output_path: Path to output video file
    
    Returns:
        Path to output video file
    
    Raises:
        SubtitleError: If FFmpeg processing fails
    
    Example:
        >>> burn_subtitles_ffmpeg(
        ...     Path("input.mp4"),
        ...     Path("subs.ass"),
        ...     Path("output.mp4")
        ... )
        Path("output.mp4")
    """
    # Construct FFmpeg command
    # -y: Overwrite output without asking
    # -i: Input video
    # -vf "ass=...": Video filter for subtitle burning
    # -c:a copy: Copy audio stream without re-encoding
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"ass={ass_path}",
        "-c:a",
        "copy",
        str(output_path),
    ]
    
    # Run FFmpeg subprocess
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,  # Don't auto-raise, handle errors manually
    )
    
    if result.returncode != 0:
        raise SubtitleError(
            f"FFmpeg failed to burn subtitles: {result.stderr}"
        )
    
    return output_path
