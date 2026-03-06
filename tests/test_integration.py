from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
pipeline = importlib.import_module("pdf2video.pipeline")
script_generator = importlib.import_module("pdf2video.script_generator")
tts_engine = importlib.import_module("pdf2video.tts_engine")
video_searcher = importlib.import_module("pdf2video.video_searcher")
video_downloader = importlib.import_module("pdf2video.video_downloader")
compositor = importlib.import_module("pdf2video.compositor")
subtitle_utils = importlib.import_module("pdf2video.subtitle_utils")
sticker_overlay = importlib.import_module("pdf2video.sticker_overlay")

PipelineError = pipeline.PipelineError
run_pipeline = pipeline.run_pipeline


def _create_pdf(path: Path, page_texts: list[str]) -> None:
    fitz = importlib.import_module("fitz")
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(72, 72, 540, 760), text)
    doc.save(path)
    doc.close()


def _mock_response(
    *,
    status_code: int,
    json_payload: dict | None = None,
    text: str = "",
    headers: dict | None = None,
    chunks: list[bytes] | None = None,
) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}
    response.json.return_value = json_payload or {}
    response.iter_content.return_value = chunks or []
    return response


class _FakeClip:
    def __init__(self, duration: float = 5.0, write_bytes: bytes = b"final-video"):
        self.duration = duration
        self.fps = 30
        self._write_bytes = write_bytes

    def resize(self, newsize: tuple[int, int]):
        return self

    def set_audio(self, audio_clip):
        return self

    def subclip(self, start: float, end: float):
        self.duration = end - start
        return self

    def fx(self, _fx, duration: float):
        self.duration = duration
        return self

    def write_videofile(self, output_path: str, codec: str, audio_codec: str, fps: int):
        Path(output_path).write_bytes(self._write_bytes)

    def close(self):
        return None
    def with_start(self, start: float):
        return self

    def with_duration(self, duration: float):
        self.duration = duration
        return self

    def with_position(self, position):
        return self


class _FakeAudioClip:
    def __init__(self, duration: float = 12.0):
        self.duration = duration

    def close(self):
        return None


class _FakeMoviePyEditor:
    def __init__(self, *, fail_export: bool = False):
        self.vfx = SimpleNamespace(loop=object())
        self._fail_export = fail_export

    def AudioFileClip(self, _path: str):
        return _FakeAudioClip()

    def VideoFileClip(self, _path: str):
        return _FakeClip(duration=4.0)

    def concatenate_videoclips(self, clips, method: str = "compose"):
        clip = _FakeClip(duration=float(sum(getattr(c, "duration", 0.0) for c in clips)))
        if self._fail_export:
            def _raise(*_args, **_kwargs):
                raise RuntimeError("ffmpeg failed")

            clip.write_videofile = _raise
        return clip

    def CompositeVideoClip(self, clips):
        # Return the first clip (base video) which is a _FakeClip
        base = clips[0] if clips else _FakeClip()
        return base

    def TextClip(self, text):
        return _FakeClip(duration=1.0)


@pytest.fixture
def integration_env(tmp_path, monkeypatch):
    def _build(
        *,
        openai_error: Exception | None = None,
        tts_error: Exception | None = None,
        search_status: int = 200,
        metadata_status: int = 200,
        download_status: int = 200,
        empty_search_results: bool = False,
        fail_composition: bool = False,
        script_text: str = "Narration script for testing.",
    ):
        temp_dir = tmp_path / "pipeline_tmp"
        temp_dir.mkdir(exist_ok=True)
        monkeypatch.setattr(
            pipeline,
            "tempfile",
            SimpleNamespace(mkdtemp=lambda *args, **kwargs: str(temp_dir)),
        )
        # Enable video mode by setting PEXELS_API_KEY
        monkeypatch.setenv("PEXELS_API_KEY", "test_api_key")

        openai_client = Mock()
        if openai_error is not None:
            openai_client.chat.completions.create.side_effect = openai_error
        else:
            openai_client.chat.completions.create.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=script_text))]
            )

        elevenlabs_client = Mock()
        if tts_error is not None:
            elevenlabs_client.text_to_speech.convert.side_effect = tts_error
        else:
            elevenlabs_client.text_to_speech.convert.return_value = [b"audio-part"]

        requests_module = Mock()

        search_payload = {
            "videos": []
            if empty_search_results
            else [
                {"id": 101, "duration": 4.0, "video_files": [{"quality": "hd", "link": "unused"}]},
                {"id": 202, "duration": 4.0, "video_files": [{"quality": "hd", "link": "unused"}]},
            ]
        }
        search_response = _mock_response(status_code=search_status, json_payload=search_payload, text="search error")
        metadata_response = _mock_response(
            status_code=metadata_status,
            json_payload={
                "duration": 5.0,
                "video_files": [{"quality": "hd", "height": 1080, "link": "https://cdn.pexels.test/video.mp4"}],
            },
            text="metadata error",
        )
        download_response = _mock_response(
            status_code=download_status,
            chunks=[b"video-bytes"],
            text="download error",
        )

        def requests_get_side_effect(url: str, **kwargs):
            if url.endswith("/videos/search"):
                return search_response
            if "/videos/videos/" in url:
                return metadata_response
            if url.startswith("https://cdn.pexels.test/"):
                return download_response
            raise AssertionError(f"Unexpected URL requested: {url}")

        requests_module.get.side_effect = requests_get_side_effect

        monkeypatch.setattr(script_generator, "_create_client", lambda: openai_client)
        monkeypatch.setattr(tts_engine, "_create_client", lambda: elevenlabs_client)
        monkeypatch.setattr(video_searcher, "_create_client", lambda: (requests_module, "test_api_key"))
        monkeypatch.setattr(video_downloader, "_create_client", lambda: (requests_module, "test_api_key"))
        monkeypatch.setattr(compositor, "_load_moviepy_editor", lambda: _FakeMoviePyEditor(fail_export=fail_composition))
        # Disable FFmpeg subtitle burning in tests (fake video files won't work with FFmpeg)
        # Must mock in compositor where it's imported directly
        monkeypatch.setattr(compositor, "check_ffmpeg_available", lambda: False)
        # Mock sticker loading in compositor (which imports load_sticker directly)
        monkeypatch.setattr(compositor, "load_sticker", lambda config: _FakeClip(duration=10.0))

        return SimpleNamespace(
            temp_dir=temp_dir,
            openai_client=openai_client,
            elevenlabs_client=elevenlabs_client,
            requests_module=requests_module,
        )

    return _build


def test_full_pipeline_end_to_end_with_cleanup(tmp_path, integration_env):
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, ["Research findings page one.", "Conclusions and outcomes page two."])

    env = integration_env()
    result = run_pipeline(str(pdf_path), str(output_path), cleanup=True)

    assert result.file_path == output_path
    assert result.duration > 0
    assert output_path.exists()
    assert output_path.read_bytes() == b"final-video"
    assert env.openai_client.chat.completions.create.call_count == 1
    assert env.elevenlabs_client.text_to_speech.convert.call_count >= 1
    assert not env.temp_dir.exists()


def test_pipeline_cleanup_disabled_keeps_intermediate_files(tmp_path, integration_env):
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, ["Text-only PDF with no images."])

    env = integration_env()
    run_pipeline(str(pdf_path), str(output_path), cleanup=False)

    assert output_path.exists()
    assert (env.temp_dir / "narration.mp3").exists()
    assert (env.temp_dir / "videos" / "pexels_101.mp4").exists()
    assert (env.temp_dir / "videos" / "pexels_202.mp4").exists()


def test_pipeline_empty_pdf_raises_script_generation_error(tmp_path, integration_env):
    pdf_path = tmp_path / "empty.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, [""])

    integration_env()
    with pytest.raises(PipelineError, match="Failed at step script generation"):
        run_pipeline(str(pdf_path), str(output_path), cleanup=True)


def test_pipeline_corrupted_pdf_raises_extraction_error(tmp_path, integration_env):
    pdf_path = tmp_path / "corrupted.pdf"
    output_path = tmp_path / "final.mp4"
    pdf_path.write_bytes(b"not-a-valid-pdf")

    integration_env()
    with pytest.raises(PipelineError, match="Failed at step PDF extraction"):
        run_pipeline(str(pdf_path), str(output_path), cleanup=True)


def test_pipeline_long_pdf_triggers_script_and_tts_chunking(tmp_path, integration_env):
    pdf_path = tmp_path / "long.pdf"
    output_path = tmp_path / "final.mp4"

    large_page_texts = [
        f"Section {index}: method results discussion conclusions. " * 4
        for index in range(260)
    ]
    _create_pdf(pdf_path, large_page_texts)

    long_script = "Narration " * 2000
    env = integration_env(script_text=long_script)
    run_pipeline(str(pdf_path), str(output_path), cleanup=True)

    assert env.openai_client.chat.completions.create.call_count > 1
    assert env.elevenlabs_client.text_to_speech.convert.call_count > 1
    assert output_path.exists()


def test_pipeline_propagates_openai_failure(tmp_path, integration_env, monkeypatch):
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, ["Content that requires script generation."])

    monkeypatch.setattr(script_generator.time, "sleep", lambda _seconds: None)
    integration_env(openai_error=RuntimeError("openai down"))

    with pytest.raises(PipelineError, match="Failed at step script generation"):
        run_pipeline(str(pdf_path), str(tmp_path / "final.mp4"), cleanup=True)


def test_pipeline_propagates_tts_failure(tmp_path, integration_env, monkeypatch):
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, ["Narration should fail at TTS stage."])

    monkeypatch.setattr(tts_engine.time, "sleep", lambda _seconds: None)
    integration_env(tts_error=RuntimeError("elevenlabs down"))

    with pytest.raises(PipelineError, match="Failed at step text-to-speech"):
        run_pipeline(str(pdf_path), str(tmp_path / "final.mp4"), cleanup=True)


def test_pipeline_propagates_pexels_search_failure(tmp_path, integration_env):
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, ["Search stage should fail."])

    integration_env(search_status=500)
    with pytest.raises(PipelineError, match="Failed at step video search"):
        run_pipeline(str(pdf_path), str(tmp_path / "final.mp4"), cleanup=True)


def test_pipeline_propagates_pexels_download_failure(tmp_path, integration_env):
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, ["Download stage should fail."])

    integration_env(download_status=500)
    with pytest.raises(PipelineError, match="Failed at step video download"):
        run_pipeline(str(pdf_path), str(tmp_path / "final.mp4"), cleanup=True)


def test_pipeline_propagates_composition_failure(tmp_path, integration_env):
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, ["Composition stage should fail."])

    integration_env(fail_composition=True)
    with pytest.raises(PipelineError, match="Failed at step video composition"):
        run_pipeline(str(pdf_path), str(tmp_path / "final.mp4"), cleanup=True)


def test_pipeline_with_subtitles_enabled(tmp_path, integration_env, monkeypatch):
    """Test that enable_subtitles=True generates video with subtitles."""
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, ["Research findings and conclusions."])

    env = integration_env()
    
    # Mock subtitle generation functions
    subtitle_generator = importlib.import_module("pdf2video.subtitle_generator")
    
    # Track calls to subtitle functions
    generate_subtitles_called = []
    export_to_ass_called = []
    
    original_generate = subtitle_generator.generate_subtitles
    original_export = subtitle_generator.export_to_ass
    
    def mock_generate(script, audio_duration):
        generate_subtitles_called.append((script, audio_duration))
        return original_generate(script, audio_duration)
    
    def mock_export(segments, output_path, config):
        export_to_ass_called.append((segments, output_path, config))
        return original_export(segments, output_path, config)
    
    # Must patch in pipeline where it's imported directly
    monkeypatch.setattr(pipeline, "generate_subtitles", mock_generate)
    monkeypatch.setattr(pipeline, "export_to_ass", mock_export)
    
    result = run_pipeline(str(pdf_path), str(output_path), cleanup=True, enable_subtitles=True)
    
    assert result.file_path == output_path
    assert output_path.exists()
    assert len(generate_subtitles_called) == 1, "generate_subtitles should be called once"
    assert len(export_to_ass_called) == 1, "export_to_ass should be called once"


def test_pipeline_with_sticker_config(tmp_path, integration_env, monkeypatch):
    """Test that sticker_config parameter loads and applies stickers."""
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    sticker_config_path = tmp_path / "stickers.json"
    _create_pdf(pdf_path, ["Research findings and conclusions."])
    
    # Create sticker config JSON
    import json
    sticker_config_path.write_text(json.dumps({
        "stickers": [
            {
                "path": str(tmp_path / "logo.png"),
                "position": "bottom-right",
                "start_time": 0,
                "end_time": 5,
                "scale": 0.5
            }
        ]
    }))
    
    # Create dummy PNG
    (tmp_path / "logo.png").write_bytes(b"fake-png")
    
    env = integration_env()
    
    # Track calls to sticker parsing
    sticker_overlay = importlib.import_module("pdf2video.sticker_overlay")
    parse_config_called = []
    
    original_parse = sticker_overlay.parse_sticker_config
    
    def mock_parse(json_path):
        parse_config_called.append(json_path)
        return original_parse(json_path)
    
    monkeypatch.setattr(pipeline, "parse_sticker_config", mock_parse)
    
    result = run_pipeline(str(pdf_path), str(output_path), cleanup=True, sticker_config=sticker_config_path)
    
    assert result.file_path == output_path
    assert output_path.exists()
    assert len(parse_config_called) == 1, "parse_sticker_config should be called once"
    assert parse_config_called[0] == sticker_config_path


def test_pipeline_backward_compatible_without_new_features(tmp_path, integration_env):
    """Test that pipeline works without enable_subtitles or sticker_config (backward compat)."""
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, ["Research findings page one."])

    env = integration_env()
    
    # Call without new parameters - should work exactly like before
    result = run_pipeline(str(pdf_path), str(output_path), cleanup=True)

    assert result.file_path == output_path
    assert result.duration > 0
    assert output_path.exists()
    assert output_path.read_bytes() == b"final-video"
    # Verify original behavior unchanged
    assert env.openai_client.chat.completions.create.call_count == 1
    assert env.elevenlabs_client.text_to_speech.convert.call_count >= 1


def test_pipeline_with_both_subtitles_and_stickers(tmp_path, integration_env, monkeypatch):
    """Test that both enable_subtitles=True AND sticker_config work together."""
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    sticker_config_path = tmp_path / "stickers.json"
    _create_pdf(pdf_path, ["Research findings! Important data here."])
    
    # Create sticker config JSON
    import json
    sticker_config_path.write_text(json.dumps({
        "stickers": [
            {
                "path": str(tmp_path / "logo.png"),
                "position": "center",
                "start_time": 1,
                "end_time": 3,
                "scale": 1.0
            }
        ]
    }))
    
    # Create dummy PNG
    (tmp_path / "logo.png").write_bytes(b"fake-png")
    
    env = integration_env()
    
    subtitle_generator = importlib.import_module("pdf2video.subtitle_generator")
    sticker_overlay = importlib.import_module("pdf2video.sticker_overlay")
    
    generate_subtitles_called = []
    parse_config_called = []
    
    original_generate = subtitle_generator.generate_subtitles
    original_parse = sticker_overlay.parse_sticker_config
    
    def mock_generate(script, audio_duration):
        generate_subtitles_called.append(True)
        return original_generate(script, audio_duration)
    
    def mock_parse(json_path):
        parse_config_called.append(json_path)
        return original_parse(json_path)
    
    # Must patch in pipeline where these are imported directly
    monkeypatch.setattr(pipeline, "generate_subtitles", mock_generate)
    monkeypatch.setattr(pipeline, "parse_sticker_config", mock_parse)
    
    result = run_pipeline(
        str(pdf_path), 
        str(output_path), 
        cleanup=True, 
        enable_subtitles=True, 
        sticker_config=sticker_config_path
    )
    
    assert result.file_path == output_path
    assert output_path.exists()
    assert len(generate_subtitles_called) == 1, "Subtitles should be generated"
    assert len(parse_config_called) == 1, "Sticker config should be parsed"


def test_pipeline_subtitles_disabled_by_default(tmp_path, integration_env, monkeypatch):
    """Test that subtitles are NOT generated when enable_subtitles=False (default)."""
    pdf_path = tmp_path / "input.pdf"
    output_path = tmp_path / "final.mp4"
    _create_pdf(pdf_path, ["Content without subtitles."])

    env = integration_env()
    
    subtitle_generator = importlib.import_module("pdf2video.subtitle_generator")
    generate_subtitles_called = []
    
    original_generate = subtitle_generator.generate_subtitles
    
    def mock_generate(script, audio_duration):
        generate_subtitles_called.append(True)
        return original_generate(script, audio_duration)
    
    monkeypatch.setattr(pipeline, "generate_subtitles", mock_generate)
    
    # Call with enable_subtitles=False explicitly
    result = run_pipeline(str(pdf_path), str(output_path), cleanup=True, enable_subtitles=False)
    
    assert result.file_path == output_path
    assert output_path.exists()
    assert len(generate_subtitles_called) == 0, "Subtitles should NOT be generated when disabled"
