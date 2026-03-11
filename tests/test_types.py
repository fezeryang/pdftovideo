import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
types_module = importlib.import_module("pdf2video.types")


def test_subtitle_segment_import():
    """Test that SubtitleSegment can be imported."""
    SubtitleSegment = types_module.SubtitleSegment
    assert SubtitleSegment is not None


def test_subtitle_segment_creation():
    """Test creating a SubtitleSegment instance."""
    SubtitleSegment = types_module.SubtitleSegment
    segment = SubtitleSegment(
        text="Hello world",
        start_time=0.0,
        end_time=2.5,
        style="Default"
    )
    assert segment.text == "Hello world"
    assert segment.start_time == 0.0
    assert segment.end_time == 2.5
    assert segment.style == "Default"


def test_subtitle_segment_fields_required():
    """Test that SubtitleSegment requires all fields."""
    SubtitleSegment = types_module.SubtitleSegment
    with pytest.raises(TypeError):
        SubtitleSegment(text="Hello")  # Missing fields


def test_subtitle_config_import():
    """Test that SubtitleConfig can be imported."""
    SubtitleConfig = types_module.SubtitleConfig
    assert SubtitleConfig is not None


def test_subtitle_config_creation():
    """Test creating a SubtitleConfig instance with all fields."""
    SubtitleConfig = types_module.SubtitleConfig
    config = SubtitleConfig(
        font_path="/usr/share/fonts/Arial.ttf",
        font_size=48,
        color=(255, 255, 255),
        outline_color=(0, 0, 0),
        position="bottom"
    )
    assert config.font_path == "/usr/share/fonts/Arial.ttf"
    assert config.font_size == 48
    assert config.color == (255, 255, 255)
    assert config.outline_color == (0, 0, 0)
    assert config.position == "bottom"


def test_subtitle_config_with_defaults():
    """Test creating a SubtitleConfig with default values for new fields."""
    SubtitleConfig = types_module.SubtitleConfig
    config = SubtitleConfig(
        font_path="/usr/share/fonts/Arial.ttf",
        font_size=48,
        color=(255, 255, 255),
        outline_color=(0, 0, 0),
        position="bottom"
    )
    # Check backward compatibility - old fields work
    assert config.font_path == "/usr/share/fonts/Arial.ttf"
    assert config.font_size == 48
    assert config.color == (255, 255, 255)
    assert config.outline_color == (0, 0, 0)
    assert config.position == "bottom"
    # Check new fields have expected defaults
    assert config.max_lines == 2
    assert config.max_chars_per_line == 30
    assert config.bottom_margin_ratio == 0.2
    assert config.min_duration == 0.5
    assert config.max_duration == 10.0


def test_subtitle_config_with_custom_values():
    """Test creating a SubtitleConfig with custom values for all fields."""
    SubtitleConfig = types_module.SubtitleConfig
    config = SubtitleConfig(
        font_path="/custom/font.ttf",
        font_size=64,
        color=(255, 0, 0),
        outline_color=(255, 255, 255),
        position="top",
        max_lines=3,
        max_chars_per_line=40,
        bottom_margin_ratio=0.15,
        min_duration=1.0,
        max_duration=15.0
    )
    assert config.font_path == "/custom/font.ttf"
    assert config.font_size == 64
    assert config.color == (255, 0, 0)
    assert config.outline_color == (255, 255, 255)
    assert config.position == "top"
    assert config.max_lines == 3
    assert config.max_chars_per_line == 40
    assert config.bottom_margin_ratio == 0.15
    assert config.min_duration == 1.0
    assert config.max_duration == 15.0

def test_sticker_type_enum_import():
    """Test that StickerType enum can be imported."""
    StickerType = types_module.StickerType
    assert StickerType is not None


def test_sticker_type_enum_values():
    """Test that StickerType has PNG, GIF, URL values."""
    StickerType = types_module.StickerType
    assert hasattr(StickerType, "PNG")
    assert hasattr(StickerType, "GIF")
    assert hasattr(StickerType, "URL")


def test_sticker_type_enum_instance():
    """Test creating StickerType enum instances."""
    StickerType = types_module.StickerType
    assert StickerType.PNG is not None
    assert StickerType.GIF is not None
    assert StickerType.URL is not None


def test_sticker_config_import():
    """Test that StickerConfig can be imported."""
    StickerConfig = types_module.StickerConfig
    assert StickerConfig is not None


def test_sticker_config_creation_with_tuple_position():
    """Test creating a StickerConfig with tuple position."""
    StickerConfig = types_module.StickerConfig
    StickerType = types_module.StickerType
    config = StickerConfig(
        path="/path/to/sticker.png",
        sticker_type=StickerType.PNG,
        position=(100, 200),
        start_time=1.0,
        end_time=5.0,
        scale=0.5
    )
    assert config.path == "/path/to/sticker.png"
    assert config.sticker_type == StickerType.PNG
    assert config.position == (100, 200)
    assert config.start_time == 1.0
    assert config.end_time == 5.0
    assert config.scale == 0.5


def test_sticker_config_creation_with_keyword_position():
    """Test creating a StickerConfig with keyword string position."""
    StickerConfig = types_module.StickerConfig
    StickerType = types_module.StickerType
    config = StickerConfig(
        path="https://example.com/sticker.gif",
        sticker_type=StickerType.URL,
        position="top-right",
        start_time=0.0,
        end_time=3.0,
        scale=1.0
    )
    assert config.path == "https://example.com/sticker.gif"
    assert config.sticker_type == StickerType.URL
    assert config.position == "top-right"
    assert config.start_time == 0.0
    assert config.end_time == 3.0
    assert config.scale == 1.0


def test_subtitle_error_import():
    """Test that SubtitleError can be imported."""
    SubtitleError = types_module.SubtitleError
    assert SubtitleError is not None


def test_subtitle_error_is_exception():
    """Test that SubtitleError is an Exception subclass."""
    SubtitleError = types_module.SubtitleError
    assert issubclass(SubtitleError, Exception)


def test_subtitle_error_can_be_raised():
    """Test that SubtitleError can be raised with a message."""
    SubtitleError = types_module.SubtitleError
    with pytest.raises(SubtitleError, match="Test error message"):
        raise SubtitleError("Test error message")


def test_subtitle_error_can_be_caught():
    """Test that SubtitleError can be caught as Exception."""
    SubtitleError = types_module.SubtitleError
    try:
        raise SubtitleError("Test error")
    except Exception as e:
        assert isinstance(e, SubtitleError)
        assert str(e) == "Test error"


def test_all_types_importable_from_module():
    """Test that all new types can be imported in one statement."""
    from pdf2video.types import (
        SubtitleSegment,
        SubtitleConfig,
        StickerConfig,
        StickerType,
        SubtitleError
    )
    assert SubtitleSegment is not None
    assert SubtitleConfig is not None
    assert StickerConfig is not None
    assert StickerType is not None
    assert SubtitleError is not None
