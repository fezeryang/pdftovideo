"""Type definitions for the PDF-to-Video pipeline."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union


class VideoQuality(Enum):
    """Video quality presets."""
    HD_720 = "720p"
    HD_1080 = "1080p"
    UHD_4K = "4k"


class OutputFormat(Enum):
    """Supported output video formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"


@dataclass
class PDFDocument:
    """Represents a parsed PDF document."""
    path: Path
    text: str
    images: List[Path]
    page_count: int


@dataclass
class ScriptSegment:
    """Represents a segment of the video script with timing."""
    text: str
    start_time: float
    end_time: float


@dataclass
class VideoScript:
    """Represents the complete video script."""
    full_script: str
    segments: List[ScriptSegment]


@dataclass
class TTSAudio:
    """Represents generated text-to-speech audio."""
    file_path: Path
    duration: float
    voice_id: Optional[str] = None


@dataclass
class VideoClip:
    """Represents a video clip from stock footage."""
    file_path: Path
    duration: float
    search_query: str


@dataclass
class FinalVideo:
    """Represents the final rendered video."""
    file_path: Path
    duration: float
    resolution: str



@dataclass
class SubtitleSegment:
    """Represents a subtitle segment with timing and styling."""
    text: str
    start_time: float
    end_time: float
    style: str


@dataclass
class SubtitleConfig:
    """Configuration for subtitle appearance and positioning."""
    font_path: str
    font_size: int
    color: Tuple[int, int, int]
    outline_color: Tuple[int, int, int]
    position: str


class StickerType(Enum):
    """Supported sticker types."""
    PNG = "png"
    GIF = "gif"
    URL = "url"


@dataclass
class StickerConfig:
    """Configuration for sticker overlay with positioning and timing."""
    path: str
    sticker_type: StickerType
    position: Union[Tuple[int, int], str]
    start_time: float
    end_time: float
    scale: float


class SubtitleError(Exception):
    """Exception raised when subtitle generation or processing fails."""
