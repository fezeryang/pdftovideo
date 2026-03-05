"""Tests for sticker overlay functionality - TDD approach."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest

from pdf2video.types import StickerConfig, StickerType


class TestLoadStickerPNG:
    """Tests for loading PNG stickers as ImageClip."""

    def test_load_png_sticker_returns_image_clip(self, tmp_path):
        """PNG sticker should be loaded as ImageClip."""
        from pdf2video.sticker_overlay import load_sticker

        # Create a simple PNG file (1x1 pixel)
        png_path = tmp_path / "test_sticker.png"
        # Create minimal PNG file (1x1 red pixel)
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_image_clip.return_value = mock_clip

            result = load_sticker(config)

            mock_image_clip.assert_called_once_with(str(png_path))
            # Duration must be set for PNG (CRITICAL)
            mock_clip.with_duration.assert_called_once_with(5.0)

    def test_load_png_sticker_sets_duration(self, tmp_path):
        """PNG sticker MUST have duration set or MoviePy crashes."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "logo.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position=(100, 200),
            start_time=2.0,
            end_time=8.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 200
            mock_clip.h = 200
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            # Duration should be end_time - start_time = 6.0
            mock_clip.with_duration.assert_called_once_with(6.0)

    def test_load_png_raises_on_missing_file(self):
        """Should raise error when PNG file doesn't exist."""
        from pdf2video.sticker_overlay import load_sticker, StickerError

        config = StickerConfig(
            path="/nonexistent/path/sticker.png",
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with pytest.raises(StickerError, match="not found"):
            load_sticker(config)


class TestLoadStickerGIF:
    """Tests for loading GIF stickers as VideoFileClip (NOT ImageClip)."""

    def test_load_gif_sticker_uses_video_file_clip(self, tmp_path):
        """GIF sticker MUST use VideoFileClip for animation support."""
        from pdf2video.sticker_overlay import load_sticker

        # Create a minimal GIF file
        gif_path = tmp_path / "animation.gif"
        # Minimal valid GIF (1x1 pixel, single frame)
        gif_data = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,'
            b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        gif_path.write_bytes(gif_data)

        config = StickerConfig(
            path=str(gif_path),
            sticker_type=StickerType.GIF,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_VideoFileClip") as mock_video_clip:
            mock_clip = MagicMock()
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_video_clip.return_value = mock_clip

            result = load_sticker(config)

            # MUST use VideoFileClip, NOT ImageClip
            mock_video_clip.assert_called_once_with(str(gif_path))

    def test_load_gif_does_not_set_duration(self, tmp_path):
        """GIF has its own duration, should not override it."""
        from pdf2video.sticker_overlay import load_sticker

        gif_path = tmp_path / "animation.gif"
        gif_data = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,'
            b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        gif_path.write_bytes(gif_data)

        config = StickerConfig(
            path=str(gif_path),
            sticker_type=StickerType.GIF,
            position="center",
            start_time=0.0,
            end_time=10.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_VideoFileClip") as mock_video_clip:
            mock_clip = MagicMock()
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            # VideoFileClip doesn't need with_duration
            mock_clip.with_duration = MagicMock()
            mock_video_clip.return_value = mock_clip

            load_sticker(config)

            # with_duration should NOT be called for GIF
            mock_clip.with_duration.assert_not_called()


class TestPositionKeywords:
    """Tests for position keyword mapping."""

    @pytest.mark.parametrize("keyword,expected", [
        ("center", ("center", "center")),
        ("top", ("center", "top")),
        ("bottom", ("center", "bottom")),
        ("left", ("left", "center")),
        ("right", ("right", "center")),
        ("top-left", ("left", "top")),
        ("top-right", ("right", "top")),
        ("bottom-left", ("left", "bottom")),
        ("bottom-right", ("right", "bottom")),
    ])
    def test_position_keyword_mapping(self, tmp_path, keyword, expected):
        """Position keywords should map to correct MoviePy position tuples."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position=keyword,
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            mock_clip.with_position.assert_called_once_with(expected)

    def test_position_tuple_passthrough(self, tmp_path):
        """(x, y) position tuples should pass through directly."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position=(150, 300),
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            mock_clip.with_position.assert_called_once_with((150, 300))


class TestScaling:
    """Tests for sticker scaling functionality."""

    def test_scale_applied_with_resized(self, tmp_path):
        """Scale factor should be applied using .resized()."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=0.5,  # Scale to 50%
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.resized.return_value = mock_clip
            mock_clip.w = 200
            mock_clip.h = 200
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            # Should resize to 50% of original width (200 * 0.5 = 100)
            mock_clip.resized.assert_called_once_with(width=100)

    def test_scale_1_0_does_not_resize(self, tmp_path):
        """Scale of 1.0 should not call resized (no scaling needed)."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,  # No scaling
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.w = 200
            mock_clip.h = 200
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            # resized should NOT be called when scale=1.0
            mock_clip.resized.assert_not_called()

    def test_scale_larger_than_1(self, tmp_path):
        """Scale greater than 1.0 should enlarge the sticker."""
        from pdf2video.sticker_overlay import load_sticker

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=2.0,  # Double size
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.with_position.return_value = mock_clip
            mock_clip.resized.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_image_clip.return_value = mock_clip

            load_sticker(config)

            # Should resize to 200% of original width (100 * 2.0 = 200)
            mock_clip.resized.assert_called_once_with(width=200)


class TestURLStickers:
    """Tests for URL sticker downloading and loading."""

    def test_url_sticker_downloads_to_temp(self):
        """URL sticker should download to temp file before loading."""
        from pdf2video.sticker_overlay import load_sticker

        config = StickerConfig(
            path="https://example.com/sticker.png",
            sticker_type=StickerType.URL,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [png_data]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
                mock_clip = MagicMock()
                mock_clip.with_duration.return_value = mock_clip
                mock_clip.with_position.return_value = mock_clip
                mock_clip.w = 100
                mock_clip.h = 100
                mock_image_clip.return_value = mock_clip

                load_sticker(config)

                # Should download with stream=True
                mock_get.assert_called_once_with(
                    "https://example.com/sticker.png",
                    stream=True,
                    timeout=30
                )

    def test_url_sticker_determines_type_from_extension(self):
        """URL sticker should detect GIF from URL extension."""
        from pdf2video.sticker_overlay import load_sticker

        config = StickerConfig(
            path="https://example.com/animation.gif",
            sticker_type=StickerType.URL,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        gif_data = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff'
            b'\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,'
            b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [gif_data]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            with patch("pdf2video.sticker_overlay._load_moviepy_VideoFileClip") as mock_video_clip:
                mock_clip = MagicMock()
                mock_clip.with_position.return_value = mock_clip
                mock_clip.w = 100
                mock_clip.h = 100
                mock_video_clip.return_value = mock_clip

                load_sticker(config)

                # Should use VideoFileClip for GIF URL
                mock_video_clip.assert_called_once()

    def test_url_sticker_handles_download_error(self):
        """Should raise StickerError on download failure."""
        from pdf2video.sticker_overlay import load_sticker, StickerError
        import requests

        config = StickerConfig(
            path="https://example.com/missing.png",
            sticker_type=StickerType.URL,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(StickerError, match="download"):
                load_sticker(config)


class TestStickerError:
    """Tests for StickerError exception."""

    def test_sticker_error_exists(self):
        """StickerError should be importable."""
        from pdf2video.sticker_overlay import StickerError

        assert issubclass(StickerError, Exception)

    def test_sticker_error_message(self):
        """StickerError should preserve error message."""
        from pdf2video.sticker_overlay import StickerError

        error = StickerError("Test error message")
        assert str(error) == "Test error message"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_sticker_type_raises_error(self, tmp_path):
        """Unknown sticker type should raise StickerError."""
        from pdf2video.sticker_overlay import load_sticker, StickerError

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        # Create config with mocked invalid type
        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )
        # Override type to something invalid
        config.sticker_type = MagicMock()
        config.sticker_type.value = "invalid"
        config.sticker_type.__eq__ = lambda self, other: False

        with pytest.raises(StickerError, match="Unsupported"):
            load_sticker(config)

    def test_zero_duration_raises_error(self, tmp_path):
        """Zero duration (start_time == end_time) should raise error."""
        from pdf2video.sticker_overlay import load_sticker, StickerError

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=5.0,
            end_time=5.0,  # Zero duration
            scale=1.0,
        )

        with pytest.raises(StickerError, match="duration"):
            load_sticker(config)

    def test_negative_duration_raises_error(self, tmp_path):
        """Negative duration (end_time < start_time) should raise error."""
        from pdf2video.sticker_overlay import load_sticker, StickerError

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="center",
            start_time=10.0,
            end_time=5.0,  # Negative duration
            scale=1.0,
        )

        with pytest.raises(StickerError, match="duration"):
            load_sticker(config)

    def test_invalid_position_keyword_raises_error(self, tmp_path):
        """Invalid position keyword should raise StickerError."""
        from pdf2video.sticker_overlay import load_sticker, StickerError

        png_path = tmp_path / "sticker.png"
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01'
            b'\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_path.write_bytes(png_data)

        config = StickerConfig(
            path=str(png_path),
            sticker_type=StickerType.PNG,
            position="invalid-position",
            start_time=0.0,
            end_time=5.0,
            scale=1.0,
        )

        with patch("pdf2video.sticker_overlay._load_moviepy_ImageClip") as mock_image_clip:
            mock_clip = MagicMock()
            mock_clip.with_duration.return_value = mock_clip
            mock_clip.w = 100
            mock_clip.h = 100
            mock_image_clip.return_value = mock_clip

            with pytest.raises(StickerError, match="Invalid position"):
                load_sticker(config)



import json


class TestParseStickerConfigDict:
    """Test parse_sticker_config_dict function."""

    def test_parse_png_sticker(self):
        """Test parsing a PNG sticker configuration."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "logo.png",
            "position": "center",
            "start_time": 0,
            "end_time": 5
        }
        result = parse_sticker_config_dict(config_dict)
        
        assert isinstance(result, StickerConfig)
        assert result.path == "logo.png"
        assert result.sticker_type == StickerType.PNG
        assert result.position == "center"
        assert result.start_time == 0
        assert result.end_time == 5
        assert result.scale == 1.0  # Default value

    def test_parse_gif_sticker(self):
        """Test parsing a GIF sticker configuration."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "animated.gif",
            "position": [100, 200],
            "start_time": 2.5,
            "end_time": 7.5,
            "scale": 0.5
        }
        result = parse_sticker_config_dict(config_dict)
        
        assert result.path == "animated.gif"
        assert result.sticker_type == StickerType.GIF
        assert result.position == [100, 200]
        assert result.start_time == 2.5
        assert result.end_time == 7.5
        assert result.scale == 0.5

    def test_parse_url_sticker_https(self):
        """Test parsing a URL sticker with HTTPS."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "https://example.com/sticker.png",
            "position": [50, 50],
            "start_time": 0,
            "end_time": 10
        }
        result = parse_sticker_config_dict(config_dict)
        
        assert result.sticker_type == StickerType.URL
        assert result.path == "https://example.com/sticker.png"

    def test_parse_url_sticker_http(self):
        """Test parsing a URL sticker with HTTP."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "http://example.com/sticker.gif",
            "position": "bottom-right",
            "start_time": 1,
            "end_time": 3
        }
        result = parse_sticker_config_dict(config_dict)
        
        assert result.sticker_type == StickerType.URL

    def test_missing_required_field_path(self):
        """Test that missing 'path' raises KeyError."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "position": "center",
            "start_time": 0,
            "end_time": 5
        }
        with pytest.raises(KeyError):
            parse_sticker_config_dict(config_dict)

    def test_missing_required_field_position(self):
        """Test that missing 'position' raises KeyError."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "logo.png",
            "start_time": 0,
            "end_time": 5
        }
        with pytest.raises(KeyError):
            parse_sticker_config_dict(config_dict)

    def test_missing_required_field_start_time(self):
        """Test that missing 'start_time' raises KeyError."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "logo.png",
            "position": "center",
            "end_time": 5
        }
        with pytest.raises(KeyError):
            parse_sticker_config_dict(config_dict)

    def test_missing_required_field_end_time(self):
        """Test that missing 'end_time' raises KeyError."""
        from pdf2video.sticker_overlay import parse_sticker_config_dict

        config_dict = {
            "path": "logo.png",
            "position": "center",
            "start_time": 0
        }
        with pytest.raises(KeyError):
            parse_sticker_config_dict(config_dict)


class TestParseStickerConfig:
    """Test parse_sticker_config function."""

    def test_parse_valid_config_single_sticker(self, tmp_path):
        """Test parsing a valid config with a single sticker."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        config_data = {
            "stickers": [
                {
                    "path": "logo.png",
                    "position": "center",
                    "start_time": 0,
                    "end_time": 5,
                    "scale": 0.8
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))
        
        result = parse_sticker_config(config_file)
        
        assert len(result) == 1
        assert result[0].path == "logo.png"
        assert result[0].scale == 0.8

    def test_parse_valid_config_multiple_stickers(self, tmp_path):
        """Test parsing a valid config with multiple stickers."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        config_data = {
            "stickers": [
                {
                    "path": "logo.png",
                    "position": "top-left",
                    "start_time": 0,
                    "end_time": 5
                },
                {
                    "path": "animated.gif",
                    "position": [100, 200],
                    "start_time": 5,
                    "end_time": 10,
                    "scale": 0.5
                },
                {
                    "path": "https://example.com/icon.png",
                    "position": "bottom-right",
                    "start_time": 10,
                    "end_time": 15
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))
        
        result = parse_sticker_config(config_file)
        
        assert len(result) == 3
        assert result[0].sticker_type == StickerType.PNG
        assert result[1].sticker_type == StickerType.GIF
        assert result[2].sticker_type == StickerType.URL

    def test_parse_config_exactly_five_stickers(self, tmp_path):
        """Test parsing a config with exactly 5 stickers (max allowed)."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        stickers = []
        for i in range(5):
            stickers.append({
                "path": f"sticker_{i}.png",
                "position": "center",
                "start_time": i,
                "end_time": i + 1
            })
        config_data = {"stickers": stickers}
        config_file.write_text(json.dumps(config_data))
        
        result = parse_sticker_config(config_file)
        
        assert len(result) == 5

    def test_reject_six_stickers(self, tmp_path):
        """Test that config with 6 stickers raises ValueError."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        stickers = []
        for i in range(6):
            stickers.append({
                "path": f"sticker_{i}.png",
                "position": "center",
                "start_time": i,
                "end_time": i + 1
            })
        config_data = {"stickers": stickers}
        config_file.write_text(json.dumps(config_data))
        
        with pytest.raises(ValueError, match="Max 5 stickers allowed"):
            parse_sticker_config(config_file)

    def test_reject_ten_stickers(self, tmp_path):
        """Test that config with 10 stickers raises ValueError."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        stickers = []
        for i in range(10):
            stickers.append({
                "path": f"sticker_{i}.png",
                "position": "center",
                "start_time": i,
                "end_time": i + 1
            })
        config_data = {"stickers": stickers}
        config_file.write_text(json.dumps(config_data))
        
        with pytest.raises(ValueError, match="Max 5 stickers allowed"):
            parse_sticker_config(config_file)

    def test_parse_empty_stickers_list(self, tmp_path):
        """Test parsing a config with an empty stickers list."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        config_data = {"stickers": []}
        config_file.write_text(json.dumps(config_data))
        
        result = parse_sticker_config(config_file)
        
        assert len(result) == 0

    def test_missing_stickers_key(self, tmp_path):
        """Test that missing 'stickers' key raises KeyError."""
        from pdf2video.sticker_overlay import parse_sticker_config

        config_file = tmp_path / "config.json"
        config_data = {"other_key": "value"}
        config_file.write_text(json.dumps(config_data))
        
        with pytest.raises(KeyError):
            parse_sticker_config(config_file)