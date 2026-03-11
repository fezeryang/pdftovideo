import importlib
import sys
from pathlib import Path
from unittest.mock import ANY, call, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
pipeline = importlib.import_module("pdf2video.pipeline")
types_module = importlib.import_module("pdf2video.types")

PipelineError = pipeline.PipelineError
run_pipeline = pipeline.run_pipeline
TTSAudio = types_module.TTSAudio
VideoClip = types_module.VideoClip
FinalVideo = types_module.FinalVideo


def _make_placeholder_clips() -> list[VideoClip]:
    return [
        VideoClip(file_path=Path("pexels_101.mp4"), duration=3.0, search_query="query"),
        VideoClip(file_path=Path("pexels_102.mp4"), duration=4.0, search_query="query"),
    ]


def test_run_pipeline_success_end_to_end_with_cleanup(tmp_path, caplog):
    temp_dir = tmp_path / "pipeline_tmp"
    temp_dir.mkdir()

    output_path = tmp_path / "final.mp4"
    downloaded_paths = [
        temp_dir / "videos" / "pexels_101.mp4",
        temp_dir / "videos" / "pexels_102.mp4",
    ]

    def tts_side_effect(text: str, output_audio_path: str):
        path = Path(output_audio_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return TTSAudio(file_path=path, duration=5.0, voice_id="voice")

    def download_side_effect(clip: VideoClip, cache_dir: str):
        target_path = Path(cache_dir) / clip.file_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"video")
        return VideoClip(file_path=target_path, duration=clip.duration, search_query=clip.search_query)

    final_video = FinalVideo(file_path=output_path, duration=7.0, resolution="1920x1080")

    caplog.set_level("INFO")
    with patch("pdf2video.pipeline._check_video_apis_available", return_value=True), patch(
        "pdf2video.pipeline.tempfile.mkdtemp", return_value=str(temp_dir)
    ), patch("pdf2video.pipeline.extract_text", return_value="Extracted source text") as mock_extract, patch(
        "pdf2video.pipeline.generate_script", return_value="Research findings and outcomes."
    ) as mock_generate, patch(
        "pdf2video.pipeline.text_to_speech", side_effect=tts_side_effect
    ) as mock_tts, patch(
        "pdf2video.pipeline.search_videos", return_value=_make_placeholder_clips()
    ) as mock_search, patch(
        "pdf2video.pipeline.download_video", side_effect=download_side_effect
    ) as mock_download, patch(
        "pdf2video.pipeline.compose_video", return_value=final_video
    ) as mock_compose:
        result = run_pipeline("input.pdf", str(output_path), cleanup=True)

    assert result == final_video
    assert mock_extract.call_args == call("input.pdf")
    assert mock_generate.call_args == call("Extracted source text")
    assert mock_tts.call_count == 1
    assert mock_search.call_count == 1
    assert mock_download.call_count == 2
    assert mock_compose.call_args == call(str(temp_dir / "narration.mp3"), ANY, str(output_path), subtitle_path=None, stickers=None, target_duration=None)

    assert not (temp_dir / "narration.mp3").exists()
    assert all(not path.exists() for path in downloaded_paths)
    assert not temp_dir.exists()

    assert "[1/6] Extracting PDF text" in caplog.text
    assert "[2/6] Generating narration script" in caplog.text
    assert "[3/6] Converting script to audio" in caplog.text
    assert "[4/6] Searching for video clips" in caplog.text
    assert "[5/6] Downloading video clips" in caplog.text
    assert "[6/6] Composing final video" in caplog.text


@pytest.mark.parametrize(
    ("failing_function", "stage_name"),
    [
        ("extract_text", "PDF extraction"),
        ("generate_script", "script generation"),
        ("text_to_speech", "text-to-speech"),
        ("search_videos", "video search"),
        ("download_video", "video download"),
        ("compose_video", "video composition"),
    ],
)
def test_run_pipeline_wraps_failure_by_stage(tmp_path, failing_function, stage_name):
    temp_dir = tmp_path / "pipeline_tmp"
    temp_dir.mkdir()

    output_path = tmp_path / "final.mp4"
    audio_path = temp_dir / "narration.mp3"
    downloaded_path = temp_dir / "videos" / "pexels_101.mp4"

    def tts_side_effect(text: str, output_audio_path: str):
        path = Path(output_audio_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return TTSAudio(file_path=path, duration=5.0, voice_id="voice")

    def download_side_effect(clip: VideoClip, cache_dir: str):
        target_path = Path(cache_dir) / clip.file_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"video")
        return VideoClip(file_path=target_path, duration=clip.duration, search_query=clip.search_query)

    default_final = FinalVideo(file_path=output_path, duration=7.0, resolution="1920x1080")
    placeholder_clips = [VideoClip(file_path=Path("pexels_101.mp4"), duration=3.0, search_query="query")]

    with patch("pdf2video.pipeline._check_video_apis_available", return_value=True), patch(
        "pdf2video.pipeline.tempfile.mkdtemp", return_value=str(temp_dir)
    ), patch("pdf2video.pipeline.extract_text", return_value="Extracted source text"), patch(
        "pdf2video.pipeline.generate_script", return_value="Research findings and outcomes."
    ), patch("pdf2video.pipeline.text_to_speech", side_effect=tts_side_effect), patch(
        "pdf2video.pipeline.search_videos", return_value=placeholder_clips
    ), patch("pdf2video.pipeline.download_video", side_effect=download_side_effect), patch(
        "pdf2video.pipeline.compose_video", return_value=default_final
    ):
        with patch(f"pdf2video.pipeline.{failing_function}", side_effect=RuntimeError("boom")):
            with pytest.raises(PipelineError, match=f"Failed at step {stage_name}"):
                run_pipeline("input.pdf", str(output_path), cleanup=True)

    assert not audio_path.exists()
    assert not downloaded_path.exists()


def test_run_pipeline_cleanup_disabled_keeps_intermediate_files(tmp_path):
    temp_dir = tmp_path / "pipeline_tmp"
    temp_dir.mkdir()
    output_path = tmp_path / "final.mp4"
    audio_path = temp_dir / "narration.mp3"
    downloaded_path = temp_dir / "videos" / "pexels_101.mp4"

    def tts_side_effect(text: str, output_audio_path: str):
        path = Path(output_audio_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return TTSAudio(file_path=path, duration=5.0, voice_id="voice")

    def download_side_effect(clip: VideoClip, cache_dir: str):
        target_path = Path(cache_dir) / clip.file_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"video")
        return VideoClip(file_path=target_path, duration=clip.duration, search_query=clip.search_query)

    final_video = FinalVideo(file_path=output_path, duration=7.0, resolution="1920x1080")

    with patch("pdf2video.pipeline._check_video_apis_available", return_value=True), patch(
        "pdf2video.pipeline.tempfile.mkdtemp", return_value=str(temp_dir)
    ), patch("pdf2video.pipeline.extract_text", return_value="Extracted source text"), patch(
        "pdf2video.pipeline.generate_script", return_value="Research findings and outcomes."
    ), patch("pdf2video.pipeline.text_to_speech", side_effect=tts_side_effect), patch(
        "pdf2video.pipeline.search_videos",
        return_value=[VideoClip(file_path=Path("pexels_101.mp4"), duration=3.0, search_query="query")],
    ), patch("pdf2video.pipeline.download_video", side_effect=download_side_effect), patch(
        "pdf2video.pipeline.compose_video", return_value=final_video
    ):
        run_pipeline("input.pdf", str(output_path), cleanup=False)

    assert audio_path.exists()
    assert downloaded_path.exists()
    assert temp_dir.exists()


def test_run_pipeline_raises_when_video_search_returns_empty(tmp_path):
    temp_dir = tmp_path / "pipeline_tmp"
    temp_dir.mkdir()

    output_path = tmp_path / "final.mp4"

    def tts_side_effect(text: str, output_audio_path: str):
        path = Path(output_audio_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return TTSAudio(file_path=path, duration=5.0, voice_id="voice")

    with patch("pdf2video.pipeline._check_video_apis_available", return_value=True), patch(
        "pdf2video.pipeline.tempfile.mkdtemp", return_value=str(temp_dir)
    ), patch("pdf2video.pipeline.extract_text", return_value="Extracted source text"), patch(
        "pdf2video.pipeline.generate_script", return_value="Research findings and outcomes."
    ), patch("pdf2video.pipeline.text_to_speech", side_effect=tts_side_effect), patch(
        "pdf2video.pipeline.search_videos", return_value=[]
    ):
        with pytest.raises(PipelineError, match="no clips found"):
            run_pipeline("input.pdf", str(output_path), cleanup=True)


def test_run_pipeline_with_target_duration_skip_tts(tmp_path, caplog):
    """Test that target_duration is passed to compose_video when skip_tts is True."""
    temp_dir = tmp_path / "pipeline_tmp"
    temp_dir.mkdir()

    output_path = tmp_path / "final.mp4"
    downloaded_paths = [
        temp_dir / "videos" / "pexels_101.mp4",
    ]

    def download_side_effect(clip: VideoClip, cache_dir: str):
        target_path = Path(cache_dir) / clip.file_path.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"video")
        return VideoClip(file_path=target_path, duration=clip.duration, search_query=clip.search_query)

    final_video = FinalVideo(file_path=output_path, duration=300.0, resolution="1920x1080")

    caplog.set_level("INFO")
    with patch("pdf2video.pipeline._check_video_apis_available", return_value=True), patch(
        "pdf2video.pipeline.tempfile.mkdtemp", return_value=str(temp_dir)
    ), patch("pdf2video.pipeline.extract_text", return_value="Extracted source text"), patch(
        "pdf2video.pipeline.generate_script", return_value="Research findings and outcomes."
    ), patch(
        "pdf2video.pipeline.search_videos", return_value=[VideoClip(file_path=Path("pexels_101.mp4"), duration=10.0, search_query="query")]
    ), patch(
        "pdf2video.pipeline.download_video", side_effect=download_side_effect
    ), patch(
        "pdf2video.pipeline.compose_video", return_value=final_video
    ) as mock_compose:
        result = run_pipeline(
            "input.pdf",
            str(output_path),
            cleanup=True,
            skip_tts=True,
            target_duration=300.0,
        )

    # Verify compose_video was called with target_duration
    assert mock_compose.call_count == 1
    call_kwargs = mock_compose.call_args
    # audio_path should be None for skip_tts
    assert call_kwargs[0][0] is None
    assert call_kwargs.kwargs.get("target_duration") == 300.0 or call_kwargs[1].get("target_duration") == 300.0
    assert result == final_video
