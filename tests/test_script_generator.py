import sys
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
script_generator = importlib.import_module("pdf2video.script_generator")

MAX_CHARS_PER_CHUNK = script_generator.MAX_CHARS_PER_CHUNK
ScriptGenerationError = script_generator.ScriptGenerationError
generate_script = script_generator.generate_script


def _mock_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


def test_generate_script_with_mock_openai_client():
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = _mock_response("Narration output")

    with patch("pdf2video.script_generator._create_client", return_value=mock_client):
        result = generate_script("Input research content")

    assert result == "Narration output"
    assert mock_client.chat.completions.create.call_count == 1


def test_generate_script_handles_api_error():
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API failure")

    with patch("pdf2video.script_generator._create_client", return_value=mock_client):
        with pytest.raises(ScriptGenerationError, match="Failed to generate script"):
            generate_script("Input research content")


def test_generate_script_chunks_long_content():
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = [
        _mock_response("Chunk one narration"),
        _mock_response("Chunk two narration"),
        _mock_response("Chunk three narration"),
    ]

    long_content = "A" * (MAX_CHARS_PER_CHUNK + 10) + "\n\n" + "B" * 100

    with patch("pdf2video.script_generator._create_client", return_value=mock_client):
        result = generate_script(long_content)

    assert result == "Chunk one narration\n\nChunk two narration\n\nChunk three narration"
    assert mock_client.chat.completions.create.call_count == 3
