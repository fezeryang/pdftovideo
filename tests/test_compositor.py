import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
compositor = importlib.import_module("pdf2video.compositor")
types_module = importlib.import_module("pdf2video.types")

CompositionError = compositor.CompositionError
compose_video = compositor.compose_video
VideoClip = types_module.VideoClip
SubtitleError = types_module.SubtitleError


def _build_moviepy_mock(audio_duration: float = 4.0, video_duration: float = 5.0):
    moviepy_mock = MagicMock()

    audio_clip = MagicMock()
    audio_clip.duration = audio_duration

    video_clip = MagicMock()
    video_clip.duration = video_duration
    video_clip.fps = 24
    video_clip.resize.return_value = video_clip
    video_clip.set_audio.return_value = video_clip
    video_clip.subclip.return_value = video_clip
    video_clip.fx.return_value = video_clip

    concatenated_clip = MagicMock()
    concatenated_clip.duration = video_duration
    concatenated_clip.fps = 30
    concatenated_clip.resize.return_value = concatenated_clip
    concatenated_clip.set_audio.return_value = concatenated_clip
    concatenated_clip.subclip.return_value = concatenated_clip
    concatenated_clip.fx.return_value = concatenated_clip

    moviepy_mock.AudioFileClip.return_value = audio_clip
    moviepy_mock.VideoFileClip.return_value = video_clip
    moviepy_mock.concatenate_videoclips.return_value = concatenated_clip

    vfx = MagicMock()
    vfx.loop = object()
    moviepy_mock.vfx = vfx

    return moviepy_mock, audio_clip, video_clip, concatenated_clip


def test_compose_video_success_with_multiple_clips(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")

    first_video_path = tmp_path / "video1.mp4"
    second_video_path = tmp_path / "video2.mp4"
    first_video_path.write_bytes(b"video1")
    second_video_path.write_bytes(b"video2")

    output_path = tmp_path / "output.mp4"
    moviepy_mock, _, _, concatenated_clip = _build_moviepy_mock(audio_duration=4.0, video_duration=5.0)

    clips = [
        VideoClip(file_path=first_video_path, duration=2.0, search_query="a"),
        VideoClip(file_path=second_video_path, duration=3.0, search_query="b"),
    ]

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        result = compose_video(str(audio_path), clips, str(output_path))

    moviepy_mock.concatenate_videoclips.assert_called_once()
    concatenated_clip.resize.assert_called_once_with(newsize=(1920, 1080))
    concatenated_clip.set_audio.assert_called_once()
    concatenated_clip.write_videofile.assert_called_once_with(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
    )
    assert result.file_path == output_path
    assert result.duration == 5.0
    assert result.resolution == "1920x1080"


def test_compose_video_raises_for_missing_audio_file(tmp_path):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"video")

    clips = [VideoClip(file_path=video_path, duration=2.0, search_query="query")]

    with pytest.raises(CompositionError, match="Missing audio file"):
        compose_video(str(tmp_path / "missing_audio.mp3"), clips, str(tmp_path / "out.mp4"))


def test_compose_video_raises_for_missing_video_file(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")

    clips = [VideoClip(file_path=tmp_path / "missing_video.mp4", duration=2.0, search_query="query")]

    with pytest.raises(CompositionError, match="Missing video file"):
        compose_video(str(audio_path), clips, str(tmp_path / "out.mp4"))


def test_compose_video_wraps_encoding_error(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")

    moviepy_mock, _, video_clip, _ = _build_moviepy_mock(audio_duration=3.0, video_duration=3.0)
    video_clip.write_videofile.side_effect = RuntimeError("ffmpeg failed")

    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        with pytest.raises(CompositionError, match="Failed to compose video"):
            compose_video(str(audio_path), clips, str(output_path))


def test_compose_video_applies_custom_resolution(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")

    moviepy_mock, _, video_clip, _ = _build_moviepy_mock(audio_duration=3.0, video_duration=3.0)
    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        result = compose_video(str(audio_path), clips, str(output_path), resolution=(1280, 720))

    video_clip.resize.assert_called_once_with(newsize=(1280, 720))
    assert result.resolution == "1280x720"


def test_compose_with_subtitles_ffmpeg(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    subtitle_path = tmp_path / "subs.ass"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")
    subtitle_path.write_text("[Script Info]\n", encoding="utf-8")

    moviepy_mock, _, video_clip, _ = _build_moviepy_mock(audio_duration=3.0, video_duration=3.0)
    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        with patch("pdf2video.compositor.check_ffmpeg_available", return_value=True):
            with patch("pdf2video.compositor.burn_subtitles_ffmpeg", return_value=output_path) as mock_burn:
                result = compose_video(
                    str(audio_path),
                    clips,
                    str(output_path),
                    subtitle_path=subtitle_path,
                )

    burn_args = mock_burn.call_args[0]
    assert burn_args[1] == subtitle_path
    assert burn_args[2] == output_path
    assert burn_args[0].suffix == ".mp4"
    video_clip.write_videofile.assert_called_once()
    assert result.file_path == output_path


def test_compose_with_subtitles_moviepy_fallback(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    subtitle_path = tmp_path / "subs.ass"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")
    subtitle_path.write_text("[Script Info]\n", encoding="utf-8")

    moviepy_mock, _, video_clip, _ = _build_moviepy_mock(audio_duration=3.0, video_duration=3.0)
    text_clip = MagicMock()
    text_clip.with_start.return_value = text_clip
    text_clip.with_duration.return_value = text_clip
    text_clip.with_position.return_value = text_clip
    moviepy_mock.TextClip.return_value = text_clip

    composited_clip = MagicMock()
    composited_clip.duration = 3.0
    composited_clip.fps = 30
    composited_clip.resize.return_value = composited_clip
    composited_clip.set_audio.return_value = composited_clip
    moviepy_mock.CompositeVideoClip.return_value = composited_clip

    event = MagicMock()
    event.start = 0
    event.end = 1200
    event.text = "Fallback subtitle"
    subtitle_data = MagicMock()
    subtitle_data.events = [event]
    pysubs2_mock = MagicMock()
    pysubs2_mock.load.return_value = subtitle_data

    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]
    real_import_module = importlib.import_module

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        with patch("pdf2video.compositor.check_ffmpeg_available", return_value=False):
            with patch("pdf2video.compositor.importlib.import_module") as mock_import_module:
                mock_import_module.side_effect = (
                    lambda name: pysubs2_mock if name == "pysubs2" else real_import_module(name)
                )
                result = compose_video(
                    str(audio_path),
                    clips,
                    str(output_path),
                    subtitle_path=subtitle_path,
                )

    pysubs2_mock.load.assert_called_once_with(str(subtitle_path))
    moviepy_mock.TextClip.assert_called_once_with("Fallback subtitle")
    moviepy_mock.CompositeVideoClip.assert_called_once()
    composited_clip.write_videofile.assert_called_once()
    assert result.file_path == output_path


def test_compose_backward_compatibility(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")

    moviepy_mock, _, video_clip, _ = _build_moviepy_mock(audio_duration=3.0, video_duration=3.0)
    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]

    with patch("pdf2video.compositor._load_moviepy_editor", return_value=moviepy_mock):
        with patch("pdf2video.compositor.check_ffmpeg_available", side_effect=AssertionError):
            result = compose_video(str(audio_path), clips, str(output_path))

    video_clip.write_videofile.assert_called_once_with(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=24,
    )
    assert result.file_path == output_path


def test_compose_with_missing_subtitle_file_raises_subtitle_error(tmp_path):
    audio_path = tmp_path / "audio.mp3"
    video_path = tmp_path / "video.mp4"
    output_path = tmp_path / "output.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video")

    clips = [VideoClip(file_path=video_path, duration=3.0, search_query="query")]

    with pytest.raises(SubtitleError, match="subtitle"):
        compose_video(
            str(audio_path),
            clips,
            str(output_path),
            subtitle_path=tmp_path / "missing.ass",
        )
