import importlib
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
tts_engine = importlib.import_module("pdf2video.tts_engine")

MAX_CHARS_PER_REQUEST = tts_engine.MAX_CHARS_PER_REQUEST
TTSError = tts_engine.TTSError
text_to_speech = tts_engine.text_to_speech
_chunk_text_for_tts = tts_engine._chunk_text_for_tts


def test_text_to_speech_generates_audio_file(tmp_path):
    mock_client = Mock()
    mock_client.text_to_speech.convert.return_value = [b"audio", b"-data"]
    output_path = tmp_path / "speech.mp3"

    with patch("pdf2video.tts_engine._create_client", return_value=mock_client):
        result = text_to_speech("Hello world", str(output_path), voice_id="voice_123")

    assert output_path.read_bytes() == b"audio-data"
    assert result.file_path == output_path
    assert result.voice_id == "voice_123"
    assert result.duration > 0
    assert mock_client.text_to_speech.convert.call_count == 1


def test_text_to_speech_handles_api_failure(tmp_path):
    mock_client = Mock()
    mock_client.text_to_speech.convert.side_effect = RuntimeError("API failure")

    with patch("pdf2video.tts_engine._create_client", return_value=mock_client):
        with pytest.raises(TTSError, match="Failed to generate speech audio"):
            text_to_speech("Hello world", str(tmp_path / "failed.mp3"))


def test_chunk_text_for_long_input():
    long_text = ("Sentence. " * 600) + ("Word " * 600)

    chunks = _chunk_text_for_tts(long_text)

    assert len(chunks) > 1
    assert all(len(chunk) <= MAX_CHARS_PER_REQUEST for chunk in chunks)


def test_text_to_speech_chunks_long_text_and_combines_output(tmp_path):
    long_text = ("A" * (MAX_CHARS_PER_REQUEST + 50)) + "\n\n" + ("B" * 300)
    chunk_count = len(_chunk_text_for_tts(long_text))

    mock_client = Mock()
    chunk_bytes = [f"chunk{index}".encode("ascii") for index in range(1, chunk_count + 1)]
    mock_client.text_to_speech.convert.side_effect = [[part] for part in chunk_bytes]

    output_path = tmp_path / "combined.mp3"
    with patch("pdf2video.tts_engine._create_client", return_value=mock_client):
        text_to_speech(long_text, str(output_path))

    assert output_path.exists()
    assert output_path.read_bytes() == b"".join(chunk_bytes)
    assert mock_client.text_to_speech.convert.call_count == chunk_count


def test_create_client_raises_when_api_key_missing():
    mock_dotenv = Mock()
    mock_elevenlabs = Mock()

    with patch("pdf2video.tts_engine.os.getenv", return_value=None):
        with patch(
            "pdf2video.tts_engine.importlib.import_module",
            side_effect=[mock_dotenv, mock_elevenlabs],
        ):
            with pytest.raises(TTSError, match="ELEVENLABS_API_KEY environment variable is not set"):
                tts_engine._create_client()

    mock_dotenv.load_dotenv.assert_called_once()
    mock_elevenlabs.ElevenLabs.assert_not_called()
