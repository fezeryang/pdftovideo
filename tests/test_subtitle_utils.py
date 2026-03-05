"""Tests for subtitle utility functions (TDD approach)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def subtitle_utils():
    """Import subtitle_utils module dynamically."""
    return importlib.import_module("pdf2video.subtitle_utils")


class TestRgbToAssColor:
    """Test RGB to ASS color conversion (BGR format)."""

    def test_red_conversion(self, subtitle_utils):
        """RGB(255,0,0) should convert to &H0000FF& (red in BGR)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(255, 0, 0) == "&H0000FF&"

    def test_green_conversion(self, subtitle_utils):
        """RGB(0,255,0) should convert to &H00FF00& (green in BGR)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(0, 255, 0) == "&H00FF00&"

    def test_blue_conversion(self, subtitle_utils):
        """RGB(0,0,255) should convert to &HFF0000& (blue in BGR)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(0, 0, 255) == "&HFF0000&"

    def test_gold_conversion(self, subtitle_utils):
        """RGB(255,200,50) should convert to &H32C8FF& (gold in BGR)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(255, 200, 50) == "&H32C8FF&"

    def test_black_conversion(self, subtitle_utils):
        """RGB(0,0,0) should convert to &H000000& (black)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(0, 0, 0) == "&H000000&"

    def test_white_conversion(self, subtitle_utils):
        """RGB(255,255,255) should convert to &HFFFFFF& (white)."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        assert rgb_to_ass_color(255, 255, 255) == "&HFFFFFF&"

    def test_invalid_rgb_negative(self, subtitle_utils):
        """Negative RGB values should raise ValueError."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        with pytest.raises(ValueError, match="RGB values must be between 0 and 255"):
            rgb_to_ass_color(-1, 0, 0)

    def test_invalid_rgb_too_large(self, subtitle_utils):
        """RGB values > 255 should raise ValueError."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        with pytest.raises(ValueError, match="RGB values must be between 0 and 255"):
            rgb_to_ass_color(256, 0, 0)


class TestAssColorToRgb:
    """Test ASS color to RGB conversion (reverse operation)."""

    def test_red_conversion(self, subtitle_utils):
        """&H0000FF& (red in BGR) should convert to RGB(255,0,0)."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        assert ass_color_to_rgb("&H0000FF&") == (255, 0, 0)

    def test_green_conversion(self, subtitle_utils):
        """&H00FF00& (green in BGR) should convert to RGB(0,255,0)."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        assert ass_color_to_rgb("&H00FF00&") == (0, 255, 0)

    def test_blue_conversion(self, subtitle_utils):
        """&HFF0000& (blue in BGR) should convert to RGB(0,0,255)."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        assert ass_color_to_rgb("&HFF0000&") == (0, 0, 255)

    def test_gold_conversion(self, subtitle_utils):
        """&H32C8FF& (gold in BGR) should convert to RGB(255,200,50)."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        assert ass_color_to_rgb("&H32C8FF&") == (255, 200, 50)

    def test_lowercase_hex(self, subtitle_utils):
        """Should handle lowercase hex values."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        assert ass_color_to_rgb("&h0000ff&") == (255, 0, 0)

    def test_invalid_format_missing_ampersand(self, subtitle_utils):
        """Missing & should raise ValueError."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        with pytest.raises(ValueError, match="Invalid ASS color format"):
            ass_color_to_rgb("H0000FF")

    def test_invalid_format_wrong_prefix(self, subtitle_utils):
        """Wrong prefix should raise ValueError."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        with pytest.raises(ValueError, match="Invalid ASS color format"):
            ass_color_to_rgb("#0000FF")

    def test_invalid_hex_length(self, subtitle_utils):
        """Wrong hex length should raise ValueError."""
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        with pytest.raises(ValueError, match="Invalid ASS color format"):
            ass_color_to_rgb("&H00FF&")


class TestEstimateSegmentTiming:
    """Test subtitle timing estimation based on word count."""

    def test_three_words_timing(self, subtitle_utils):
        """3 words at 2.5 WPS should be ~1.2s duration."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("This is test", 0.0)
        assert start == 0.0
        assert abs(end - 1.2) < 0.01  # 3 words / 2.5 WPS = 1.2s

    def test_ten_words_timing(self, subtitle_utils):
        """10 words at 2.5 WPS should be 4.0s duration."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("One two three four five six seven eight nine ten", 0.0)
        assert start == 0.0
        assert abs(end - 4.0) < 0.01  # 10 words / 2.5 WPS = 4.0s

    def test_offset_start_time(self, subtitle_utils):
        """Start time should affect both start and end."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("Five word test sentence here", 10.5)
        assert start == 10.5
        assert abs(end - 12.5) < 0.01  # 10.5 + (5 / 2.5) = 12.5s

    def test_empty_string(self, subtitle_utils):
        """Empty string should return zero duration."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("", 5.0)
        assert start == 5.0
        assert end == 5.0  # No words = no duration

    def test_whitespace_only(self, subtitle_utils):
        """Whitespace-only string should return zero duration."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("   \n\t  ", 2.0)
        assert start == 2.0
        assert end == 2.0

    def test_single_word(self, subtitle_utils):
        """Single word at 2.5 WPS should be 0.4s duration."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        start, end = estimate_segment_timing("Hello", 0.0)
        assert start == 0.0
        assert abs(end - 0.4) < 0.01  # 1 word / 2.5 WPS = 0.4s

    def test_negative_start_time(self, subtitle_utils):
        """Negative start time should raise ValueError."""
        estimate_segment_timing = subtitle_utils.estimate_segment_timing
        with pytest.raises(ValueError, match="Start time must be non-negative"):
            estimate_segment_timing("Test text", -1.0)

    def test_words_per_second_constant_exists(self, subtitle_utils):
        """Module should define WORDS_PER_SECOND constant."""
        assert hasattr(subtitle_utils, "WORDS_PER_SECOND")
        assert subtitle_utils.WORDS_PER_SECOND == 2.5


class TestRoundTripConversion:
    """Test that color conversions are reversible."""

    def test_rgb_to_ass_to_rgb(self, subtitle_utils):
        """Converting RGB->ASS->RGB should return original."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        
        original = (128, 64, 192)
        ass_color = rgb_to_ass_color(*original)
        result = ass_color_to_rgb(ass_color)
        assert result == original

    def test_ass_to_rgb_to_ass(self, subtitle_utils):
        """Converting ASS->RGB->ASS should return original."""
        rgb_to_ass_color = subtitle_utils.rgb_to_ass_color
        ass_color_to_rgb = subtitle_utils.ass_color_to_rgb
        
        original = "&H4080C0&"
        rgb = ass_color_to_rgb(original)
        result = rgb_to_ass_color(*rgb)
        assert result.upper() == original.upper()


class TestFFmpegAvailability:
    """Test FFmpeg availability detection."""

    def test_ffmpeg_available_when_installed(self, subtitle_utils):
        """FFmpeg check should return True when ffmpeg is in PATH."""
        from unittest.mock import patch
        
        check_ffmpeg_available = subtitle_utils.check_ffmpeg_available
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert check_ffmpeg_available() is True

    def test_ffmpeg_not_available(self, subtitle_utils):
        """FFmpeg check should return False when ffmpeg is not in PATH."""
        from unittest.mock import patch
        
        check_ffmpeg_available = subtitle_utils.check_ffmpeg_available
        with patch("shutil.which", return_value=None):
            assert check_ffmpeg_available() is False


class TestBurnSubtitlesFFmpeg:
    """Test FFmpeg subtitle burning wrapper."""

    def test_burn_subtitles_constructs_correct_command(self, subtitle_utils, tmp_path):
        """Should construct correct FFmpeg command with proper arguments."""
        from unittest.mock import Mock, patch
        from pathlib import Path
        
        burn_subtitles_ffmpeg = subtitle_utils.burn_subtitles_ffmpeg
        
        video_path = tmp_path / "input.mp4"
        ass_path = tmp_path / "subtitles.ass"
        output_path = tmp_path / "output.mp4"
        
        # Create dummy files
        video_path.write_text("dummy")
        ass_path.write_text("dummy")
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = burn_subtitles_ffmpeg(video_path, ass_path, output_path)
        
        # Verify command structure
        expected_cmd = [
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
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        assert actual_cmd == expected_cmd
        assert result == output_path

    def test_burn_subtitles_handles_paths_with_spaces(self, subtitle_utils, tmp_path):
        """Should properly handle paths containing spaces."""
        from unittest.mock import Mock, patch
        
        burn_subtitles_ffmpeg = subtitle_utils.burn_subtitles_ffmpeg
        
        video_dir = tmp_path / "test video"
        video_dir.mkdir()
        video_path = video_dir / "input file.mp4"
        ass_path = video_dir / "subtitle file.ass"
        output_path = video_dir / "output file.mp4"
        
        video_path.write_text("dummy")
        ass_path.write_text("dummy")
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = burn_subtitles_ffmpeg(video_path, ass_path, output_path)
        
        # Command should contain str(path) which includes spaces
        actual_cmd = mock_run.call_args[0][0]
        assert str(video_path) in actual_cmd
        assert str(output_path) in actual_cmd
        assert result == output_path

    def test_burn_subtitles_raises_on_ffmpeg_failure(self, subtitle_utils, tmp_path):
        """Should raise SubtitleError when FFmpeg fails."""
        from unittest.mock import Mock, patch
        
        burn_subtitles_ffmpeg = subtitle_utils.burn_subtitles_ffmpeg
        
        video_path = tmp_path / "input.mp4"
        ass_path = tmp_path / "subtitles.ass"
        output_path = tmp_path / "output.mp4"
        
        video_path.write_text("dummy")
        ass_path.write_text("dummy")
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Invalid codec"
        
        with patch("subprocess.run", return_value=mock_result):
            # Import SubtitleError from types module
            from pdf2video.types import SubtitleError
            
            with pytest.raises(SubtitleError, match="FFmpeg failed"):
                burn_subtitles_ffmpeg(video_path, ass_path, output_path)