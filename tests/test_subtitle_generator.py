from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

types_module = importlib.import_module("pdf2video.types")
SubtitleConfig = types_module.SubtitleConfig
SubtitleSegment = types_module.SubtitleSegment
pysubs2 = importlib.import_module("pysubs2")


def _subtitle_generator_module():
    return importlib.import_module("pdf2video.subtitle_generator")


def _make_config() -> SubtitleConfig:
    return SubtitleConfig(
        font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        font_size=42,
        color=(255, 255, 255),
        outline_color=(0, 0, 0),
        position="bottom",
    )


class TestGenerateSubtitles:
    def test_empty_script_returns_no_segments(self):
        module = _subtitle_generator_module()
        assert module.generate_subtitles("", 5.0) == []

    def test_whitespace_script_returns_no_segments(self):
        module = _subtitle_generator_module()
        assert module.generate_subtitles("   \n\t  ", 5.0) == []

    def test_zero_audio_duration_raises(self):
        module = _subtitle_generator_module()
        with pytest.raises(ValueError, match="audio_duration must be positive"):
            module.generate_subtitles("Hello world.", 0.0)

    def test_negative_audio_duration_raises(self):
        module = _subtitle_generator_module()
        with pytest.raises(ValueError, match="audio_duration must be positive"):
            module.generate_subtitles("Hello world.", -2.0)

    def test_sentence_split_produces_multiple_segments(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("Hello world. This is a test.", 4.0)
        assert len(segments) == 2
        assert segments[0].text == "Hello world."
        assert segments[1].text == "This is a test."

    def test_text_without_sentence_punctuation_is_single_segment(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("This text has no punctuation at all", 3.0)
        assert len(segments) == 1
        assert segments[0].text == "This text has no punctuation at all"

    def test_timing_is_monotonic_and_non_overlapping(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("One short sentence. Another short sentence.", 6.0)
        assert segments[0].start_time == pytest.approx(0.0)
        for previous, current in zip(segments, segments[1:]):
            assert previous.end_time == pytest.approx(current.start_time)
            assert current.end_time >= current.start_time

    def test_timing_is_strictly_increasing_for_many_short_segments(self):
        module = _subtitle_generator_module()
        script = " ".join(["Hi." for _ in range(25)])
        segments = module.generate_subtitles(script, 2.0)

        assert len(segments) == 25
        for segment in segments:
            assert segment.end_time > segment.start_time
        for previous, current in zip(segments, segments[1:]):
            assert previous.end_time <= current.start_time

    def test_total_timing_matches_audio_duration_within_tolerance(self):
        module = _subtitle_generator_module()
        audio_duration = 8.0
        segments = module.generate_subtitles(
            "This is sentence one. This is sentence two. This is sentence three.",
            audio_duration,
        )
        final_end = segments[-1].end_time
        tolerance = audio_duration * 0.05
        assert math.isclose(final_end, audio_duration, abs_tol=tolerance)

    def test_segment_durations_are_clamped_to_config_bounds(self):
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=42,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            position="bottom",
            min_duration=0.8,
            max_duration=1.0,
        )
        script = "Hi. " + (" ".join(["word" for _ in range(200)]) + ".")
        segments = module.generate_subtitles(script, 20.0, config)

        durations = [segment.end_time - segment.start_time for segment in segments]
        assert len(segments) == 2
        assert all(duration >= 0.8 for duration in durations)
        assert all(duration <= 1.0 for duration in durations)

    def test_logs_warning_when_segment_duration_is_clamped(self, caplog):
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=42,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            position="bottom",
            min_duration=0.8,
            max_duration=1.0,
        )
        script = "Hi. " + (" ".join(["word" for _ in range(200)]) + ".")

        with caplog.at_level("WARNING"):
            module.generate_subtitles(script, 20.0, config)

        assert "duration clamped" in caplog.text

    def test_estimate_segment_timing_is_used(self, monkeypatch):
        module = _subtitle_generator_module()
        calls: list[tuple[str, float]] = []

        def fake_estimate_segment_timing(text: str, start_time: float) -> tuple[float, float]:
            calls.append((text, start_time))
            return (start_time, start_time + 1.0)

        monkeypatch.setattr(module, "estimate_segment_timing", fake_estimate_segment_timing)
        module.generate_subtitles("A first sentence. A second sentence.", 4.0)
        assert len(calls) == 2
        assert calls[0][0] == "A first sentence."
        assert calls[1][0] == "A second sentence."

    def test_default_style_is_applied_for_normal_sentences(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("Calm sentence.", 2.0)
        assert segments[0].style == "default"

    def test_emphasis_style_is_applied_for_exclamation_sentences(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("Watch out!", 2.0)
        assert segments[0].style == "emphasis"

    def test_both_styles_are_present_when_mixed_input(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("Normal line. Excited line!", 4.0)
        styles = {segment.style for segment in segments}
        assert "default" in styles
        assert "emphasis" in styles

    def test_newlines_and_extra_spaces_are_ignored_in_splitting(self):
        module = _subtitle_generator_module()
        script = "First sentence.\n\n   Second sentence!\nThird sentence?"
        segments = module.generate_subtitles(script, 6.0)
        assert len(segments) == 3
        assert segments[0].text == "First sentence."
        assert segments[1].text == "Second sentence!"
        assert segments[2].text == "Third sentence?"

    def test_long_sentence_wraps_to_two_lines_with_char_cap(self):
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=42,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            position="bottom",
            max_lines=2,
            max_chars_per_line=30,
        )
        script = (
            "We optimize throughput, reduce latency significantly, "
            "and keep outputs deterministic for production systems."
        )

        segments = module.generate_subtitles(script, 4.0, config)

        assert len(segments) == 1
        lines = segments[0].text.split("\\N")
        assert len(lines) <= 2
        assert all(len(line) <= 30 for line in lines)
        assert lines[0].endswith(",")

    def test_wrap_text_overflow_is_deterministic_and_capped(self):
        module = _subtitle_generator_module()
        text = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 "
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 "
            "tail words"
        )

        wrapped_once = module.wrap_text_to_lines(text, max_lines=2, max_chars_per_line=30)
        wrapped_twice = module.wrap_text_to_lines(text, max_lines=2, max_chars_per_line=30)

        assert wrapped_once == wrapped_twice
        lines = wrapped_once.split("\\N")
        assert len(lines) <= 2
        assert all(len(line) <= 30 for line in lines)
        assert wrapped_once.endswith("...")

    def test_returns_subtitle_segment_instances(self):
        module = _subtitle_generator_module()
        segments = module.generate_subtitles("One. Two.", 2.0)
        assert all(isinstance(segment, SubtitleSegment) for segment in segments)


class TestExportToAss:
    def test_export_to_ass_creates_file_and_returns_path(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "subtitles.ass"
        segments = [SubtitleSegment(text="Hello", start_time=0.0, end_time=1.0, style="default")]
        result_path = module.export_to_ass(segments, output_path, _make_config())
        assert result_path == output_path
        assert output_path.exists()

    def test_export_to_ass_contains_required_ass_sections(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "sections.ass"
        segments = [SubtitleSegment(text="Hello", start_time=0.0, end_time=1.0, style="default")]
        module.export_to_ass(segments, output_path, _make_config())
        content = output_path.read_text(encoding="utf-8")
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

    def test_export_to_ass_includes_default_and_emphasis_styles(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "styles.ass"
        segments = [
            SubtitleSegment(text="Normal", start_time=0.0, end_time=1.0, style="default"),
            SubtitleSegment(text="Loud!", start_time=1.0, end_time=2.0, style="emphasis"),
        ]
        module.export_to_ass(segments, output_path, _make_config())
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert "Default" in parsed.styles
        assert "Emphasis" in parsed.styles
        assert parsed.styles["Default"].primarycolor != parsed.styles["Emphasis"].primarycolor

    def test_export_to_ass_roundtrip_parses_successfully(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "roundtrip.ass"
        segments = [SubtitleSegment(text="Roundtrip", start_time=0.0, end_time=1.5, style="default")]
        module.export_to_ass(segments, output_path, _make_config())
        content = output_path.read_text(encoding="utf-8")
        reparsed = pysubs2.SSAFile.from_string(content)
        assert len(reparsed.events) == 1
        assert reparsed.events[0].text == "Roundtrip"

    def test_export_to_ass_event_count_matches_segments(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "events.ass"
        segments = [
            SubtitleSegment(text="One", start_time=0.0, end_time=1.0, style="default"),
            SubtitleSegment(text="Two", start_time=1.0, end_time=2.0, style="emphasis"),
            SubtitleSegment(text="Three", start_time=2.0, end_time=3.0, style="default"),
        ]
        module.export_to_ass(segments, output_path, _make_config())
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert len(parsed.events) == len(segments)

    def test_export_to_ass_maps_style_names_to_ass_style_keys(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "style-map.ass"
        segments = [
            SubtitleSegment(text="Default line", start_time=0.0, end_time=1.0, style="default"),
            SubtitleSegment(text="Emphasis line", start_time=1.0, end_time=2.0, style="emphasis"),
        ]
        module.export_to_ass(segments, output_path, _make_config())
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert parsed.events[0].style == "Default"
        assert parsed.events[1].style == "Emphasis"

    def test_export_to_ass_uses_color_conversion_utility(self, tmp_path, monkeypatch):
        module = _subtitle_generator_module()
        calls: list[tuple[int, int, int]] = []

        def fake_rgb_to_ass_color(r: int, g: int, b: int) -> str:
            calls.append((r, g, b))
            return "&H000000&"

        monkeypatch.setattr(module, "rgb_to_ass_color", fake_rgb_to_ass_color)
        output_path = tmp_path / "color-hook.ass"
        segments = [SubtitleSegment(text="Color", start_time=0.0, end_time=1.0, style="default")]
        module.export_to_ass(segments, output_path, _make_config())
        assert len(calls) >= 2

    def test_export_to_ass_preserves_segment_timing_in_milliseconds(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "timing.ass"
        segments = [SubtitleSegment(text="Timed", start_time=1.25, end_time=2.75, style="default")]
        module.export_to_ass(segments, output_path, _make_config())
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert parsed.events[0].start == 1250
        assert parsed.events[0].end == 2750

    def test_export_to_ass_handles_empty_segments(self, tmp_path):
        module = _subtitle_generator_module()
        output_path = tmp_path / "empty.ass"
        module.export_to_ass([], output_path, _make_config())
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert len(parsed.events) == 0

    def test_export_to_ass_respects_bottom_margin_ratio(self, tmp_path):
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=42,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            position="bottom",
            bottom_margin_ratio=0.15,
        )
        output_path = tmp_path / "margin.ass"
        segments = [SubtitleSegment(text="Test", start_time=0.0, end_time=1.0, style="default")]
        module.export_to_ass(segments, output_path, config, resolution=(1920, 1080))
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        expected_margin_v = int(1080 * 0.15)
        assert parsed.styles["Default"].marginv == expected_margin_v

    def test_export_to_ass_compatibility_with_ffmpeg_burn(self, tmp_path):
        """Ensure exported ASS is valid for FFmpeg subtitle burning."""
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=48,
            color=(255, 255, 0),
            outline_color=(0, 0, 0),
            position="bottom",
            max_lines=2,
            max_chars_per_line=40,
            bottom_margin_ratio=0.1,
        )
        output_path = tmp_path / "ffmpeg_test.ass"
        segments = [
            SubtitleSegment(
                text="This is a test\\Nwith multiple lines",
                start_time=0.0,
                end_time=2.5,
                style="default",
            ),
            SubtitleSegment(
                text="Another subtitle!",
                start_time=2.5,
                end_time=5.0,
                style="emphasis",
            ),
        ]
        module.export_to_ass(segments, output_path, config)
        
        # Verify file is created and readable
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        
        # Verify ASS format structure required by FFmpeg
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Format:" in content
        assert "Dialogue:" in content
        
        # Verify parseable by pysubs2 (same library FFmpeg uses internally)
        parsed = pysubs2.SSAFile.from_string(content)
        assert len(parsed.events) == 2
        assert parsed.events[0].text == "This is a test\\Nwith multiple lines"
        assert parsed.events[1].text == "Another subtitle!"
        
        # Verify styles are correctly defined
        assert "Default" in parsed.styles
        assert "Emphasis" in parsed.styles
        assert parsed.styles["Default"].fontsize == 48.0
        assert parsed.styles["Emphasis"].bold is True
    def test_export_to_ass_includes_playres_metadata(self, tmp_path):
        """Verify PlayResX/PlayResY are set for correct FFmpeg rendering."""
        module = _subtitle_generator_module()
        config = SubtitleConfig(
            font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            font_size=42,
            color=(255, 255, 255),
            outline_color=(0, 0, 0),
            position="bottom",
        )
        output_path = tmp_path / "playres.ass"
        segments = [SubtitleSegment(text="Test", start_time=0.0, end_time=1.0, style="default")]
        module.export_to_ass(segments, output_path, config, resolution=(1920, 1080))
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert parsed.info.get("PlayResX") == "1920"
        assert parsed.info.get("PlayResY") == "1080"

    def test_export_to_ass_playres_uses_custom_resolution(self, tmp_path):
        """Verify PlayResX/PlayResY adapt to custom resolution."""
        module = _subtitle_generator_module()
        config = _make_config()
        output_path = tmp_path / "custom_res.ass"
        segments = [SubtitleSegment(text="Test", start_time=0.0, end_time=1.0, style="default")]
        module.export_to_ass(segments, output_path, config, resolution=(3840, 2160))
        parsed = pysubs2.SSAFile.from_string(output_path.read_text(encoding="utf-8"))
        assert parsed.info.get("PlayResX") == "3840"
        assert parsed.info.get("PlayResY") == "2160"


def _mock_keyword_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


class TestKeywordDetection:
    def test_detect_keywords_mocked(self):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response('["AI", "John Doe", "2024"]')
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis("In 2024, John Doe built an AI model.")

        assert keywords == ["AI", "John Doe", "2024"]
        assert 3 <= len(keywords) <= 10

    def test_keyword_detection(self):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response('["gravity", "Einstein", "1915"]')
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis(
                "Einstein published general relativity in 1915 and changed gravity research."
            )
            call_kwargs = mock_create_client.return_value.chat.completions.create.call_args.kwargs

        assert keywords == ["gravity", "Einstein", "1915"]
        assert call_kwargs["model"] == "deepseek-chat"
        prompt_text = call_kwargs["messages"][0]["content"].lower()
        assert "extracting key terms from video scripts" in prompt_text
        assert "extract 3-10 important keywords" in prompt_text
        assert "return only a json array of strings" in prompt_text

    def test_keyword_detection_api_unavailable(self, caplog):
        module = _subtitle_generator_module()
        with patch("pdf2video.subtitle_generator._create_client", side_effect=RuntimeError("network down")):
            keywords = module.detect_keywords_for_emphasis("Any script text")

        assert keywords == []
        assert "Keyword detection failed" in caplog.text

    def test_detect_keywords_limits_to_ten_keywords(self):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response(
            '["k1","k2","k3","k4","k5","k6","k7","k8","k9","k10","k11"]'
        )
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis("A script with many key terms")

        assert keywords == ["k1", "k2", "k3", "k4", "k5", "k6", "k7", "k8", "k9", "k10"]

    def test_detect_keywords_returns_empty_when_fewer_than_three(self):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response('["alpha", "beta"]')
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis("Script with too few terms")

        assert keywords == []

    def test_detect_keywords_returns_empty_for_invalid_json(self, caplog):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response("not-json")
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis("Script text")

        assert keywords == []
        assert "invalid response format" in caplog.text

    def test_detect_keywords_returns_empty_for_empty_script(self):
        module = _subtitle_generator_module()
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            keywords = module.detect_keywords_for_emphasis("   \n  ")

        assert keywords == []
        mock_create_client.assert_not_called()

    def test_detect_keywords_returns_empty_for_zero_keywords(self):
        module = _subtitle_generator_module()
        mock_response = _mock_keyword_response("[]")
        with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
            mock_create_client.return_value.chat.completions.create.return_value = mock_response
            keywords = module.detect_keywords_for_emphasis("Script text")

        assert keywords == []


class TestApplyEmphasis:
    def test_apply_emphasis(self):
        module = _subtitle_generator_module()
        segments = [
            SubtitleSegment(text="The AI model is great", start_time=0.0, end_time=2.0, style="default"),
            SubtitleSegment(text="No match here", start_time=2.0, end_time=4.0, style="default"),
        ]

        result = module.apply_emphasis_to_segments(segments, ["AI", "model"])

        assert result[0].style == "emphasis"
        assert result[1].style == "default"
        assert result[0].text == "The AI model is great"
        assert result[1].text == "No match here"

    def test_apply_emphasis_is_case_insensitive_and_non_mutating(self):
        module = _subtitle_generator_module()
        original = SubtitleSegment(text="Neural Networks", start_time=1.0, end_time=3.0, style="default")
        result = module.apply_emphasis_to_segments([original], ["neural"])

        assert result[0].style == "emphasis"
        assert result[0].text == original.text
        assert result[0].start_time == original.start_time
        assert result[0].end_time == original.end_time
        assert original.style == "default"
        assert result[0] is not original


def test_detect_keywords_mocked():
    module = _subtitle_generator_module()
    mock_response = _mock_keyword_response('["AI", "John Doe", "2024"]')
    with patch("pdf2video.subtitle_generator._create_client") as mock_create_client:
        mock_create_client.return_value.chat.completions.create.return_value = mock_response
        keywords = module.detect_keywords_for_emphasis("In 2024, John Doe built an AI model.")

    assert keywords == ["AI", "John Doe", "2024"]


def test_apply_emphasis():
    module = _subtitle_generator_module()
    segments = [
        SubtitleSegment(text="The AI model is great", start_time=0.0, end_time=2.0, style="default"),
        SubtitleSegment(text="No match here", start_time=2.0, end_time=4.0, style="default"),
    ]

    result = module.apply_emphasis_to_segments(segments, ["AI", "model"])

    assert result[0].style == "emphasis"
    assert result[1].style == "default"
    assert result[0].text == "The AI model is great"
    assert result[1].text == "No match here"
