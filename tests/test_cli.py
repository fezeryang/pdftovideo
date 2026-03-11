"""Tests for the CLI module."""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdf2video.cli import CLIError, cmd_config, cmd_generate, cmd_info, create_parser, main
from pdf2video.types import FinalVideo


@pytest.fixture
def mock_env_vars():
    """Fixture to mock environment variables for config command."""
    with patch("pdf2video.cli.os.getenv") as mock_getenv:
        def getenv_side_effect(key, default=None):
            env_map = {
                "OPENAI_API_KEY": "test_openai_key",
                "ELEVENLABS_API_KEY": "test_elevenlabs_key",
                "PEXELS_API_KEY": None,  # Not set
            }
            return env_map.get(key, default)
        
        mock_getenv.side_effect = getenv_side_effect
        yield mock_getenv


@pytest.fixture
def mock_run_pipeline():
    """Fixture to mock the run_pipeline function."""
    with patch("pdf2video.cli.run_pipeline") as mock:
        # Create a mock FinalVideo return value
        mock_video = FinalVideo(
            file_path=Path("output.mp4"),
            duration=120.0,
            resolution="1920x1080",
        )
        mock.return_value = mock_video
        yield mock


@pytest.fixture
def sample_pdf(temp_dir):
    """Create a sample PDF file for testing."""
    pdf_path = temp_dir / "sample.pdf"
    pdf_path.write_text("Sample PDF content")
    return pdf_path


class TestCmdGenerate:
    """Tests for the generate command."""
    
    def test_generate_success(self, sample_pdf, mock_run_pipeline, capsys):
        """Test successful PDF to video conversion."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 0
        mock_run_pipeline.assert_called_once_with(
            input_path=str(sample_pdf),
            output_path="output.mp4",
            cleanup=True,
            enable_subtitles=False,
            enable_emphasis=True,
            sticker_config=None,
            skip_tts=False,
            target_duration=None,
        )
        
        captured = capsys.readouterr()
        assert "✓ Video created successfully: output.mp4" in captured.out
    
    def test_generate_with_no_cleanup(self, sample_pdf, mock_run_pipeline):
        """Test generate command with --no-cleanup flag."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
            "--no-cleanup",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 0
        mock_run_pipeline.assert_called_once_with(
            input_path=str(sample_pdf),
            output_path="output.mp4",
            cleanup=False,
            enable_subtitles=False,
            enable_emphasis=True,
            sticker_config=None,
            skip_tts=False,
            target_duration=None,
        )
    
    def test_generate_missing_input_file(self, temp_dir, mock_run_pipeline, capsys):
        """Test generate command with missing input file."""
        missing_file = temp_dir / "missing.pdf"
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(missing_file),
            "--output", "output.mp4",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 1
        mock_run_pipeline.assert_not_called()
        
        captured = capsys.readouterr()
        assert "Error: Input file not found" in captured.err
        assert str(missing_file) in captured.err
    
    def test_generate_input_is_directory(self, temp_dir, mock_run_pipeline, capsys):
        """Test generate command when input is a directory."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(temp_dir),
            "--output", "output.mp4",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 1
        mock_run_pipeline.assert_not_called()
        
        captured = capsys.readouterr()
        assert "Error: Input path is not a file" in captured.err
    
    def test_generate_pipeline_error(self, sample_pdf, capsys):
        """Test generate command when pipeline raises PipelineError."""
        from pdf2video.pipeline import PipelineError
        
        with patch("pdf2video.cli.run_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = PipelineError("Failed at step video search: no clips found")
            
            parser = create_parser()
            args = parser.parse_args([
                "generate",
                "--input", str(sample_pdf),
                "--output", "output.mp4",
            ])
            
            exit_code = cmd_generate(args)
            
            assert exit_code == 1
            captured = capsys.readouterr()
            assert "Error: Pipeline failed" in captured.err
            assert "no clips found" in captured.err
    
    def test_generate_keyboard_interrupt(self, sample_pdf, capsys):
        """Test generate command when user cancels with Ctrl+C."""
        with patch("pdf2video.cli.run_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = KeyboardInterrupt()
            
            parser = create_parser()
            args = parser.parse_args([
                "generate",
                "--input", str(sample_pdf),
                "--output", "output.mp4",
            ])
            
            exit_code = cmd_generate(args)
            
            assert exit_code == 1
            captured = capsys.readouterr()
            assert "Operation cancelled by user" in captured.err
    
    def test_generate_unexpected_error(self, sample_pdf, capsys):
        """Test generate command with unexpected error."""
        with patch("pdf2video.cli.run_pipeline") as mock_pipeline:
            mock_pipeline.side_effect = RuntimeError("Something went wrong")
            
            parser = create_parser()
            args = parser.parse_args([
                "generate",
                "--input", str(sample_pdf),
                "--output", "output.mp4",
            ])
            
            exit_code = cmd_generate(args)
            
            assert exit_code == 1
            captured = capsys.readouterr()
            assert "Error: Unexpected error occurred" in captured.err
            assert "Something went wrong" in captured.err
            assert "Please report this issue" in captured.err

    def test_generate_with_target_duration(self, sample_pdf, mock_run_pipeline):
        """Test generate command with --target-duration flag."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
            "--no-tts",
            "--target-duration", "300.0",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 0
        mock_run_pipeline.assert_called_once_with(
            input_path=str(sample_pdf),
            output_path="output.mp4",
            cleanup=True,
            enable_subtitles=False,
            enable_emphasis=True,
            sticker_config=None,
            skip_tts=True,
            target_duration=300.0,
        )

    def test_generate_target_duration_zero_rejected(self, sample_pdf, mock_run_pipeline, capsys):
        """Test generate command rejects --target-duration 0."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
            "--target-duration", "0",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 1
        mock_run_pipeline.assert_not_called()
        
        captured = capsys.readouterr()
        assert "Error: --target-duration must be > 0" in captured.err

    def test_generate_target_duration_negative_rejected(self, sample_pdf, mock_run_pipeline, capsys):
        """Test generate command rejects negative --target-duration."""
        parser = create_parser()
        args = parser.parse_args([
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
            "--target-duration", "-10.5",
        ])
        
        exit_code = cmd_generate(args)
        
        assert exit_code == 1
        mock_run_pipeline.assert_not_called()
        
        captured = capsys.readouterr()
        assert "Error: --target-duration must be > 0" in captured.err

class TestCmdInfo:
    """Tests for the info command."""
    
    def test_info_displays_version(self, capsys):
        """Test that info command displays version information."""
        parser = create_parser()
        args = parser.parse_args(["info"])
        
        exit_code = cmd_info(args)
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "PDF to Video Conversion Pipeline" in captured.out
        assert "Version: 0.1.0" in captured.out
        assert "Author: PDF2Video Team" in captured.out
        assert "A Python package for converting PDF documents" in captured.out


class TestCmdConfig:
    """Tests for the config command."""
    
    def test_config_all_keys_set(self, capsys):
        """Test config command when all API keys are set."""
        with patch("pdf2video.cli.os.getenv") as mock_getenv:
            def getenv_side_effect(key, default=None):
                env_map = {
                    "OPENAI_API_KEY": "test_key_1",
                    "ELEVENLABS_API_KEY": "test_key_2",
                    "PEXELS_API_KEY": "test_key_3",
                }
                return env_map.get(key, default)
            
            mock_getenv.side_effect = getenv_side_effect
            
            parser = create_parser()
            args = parser.parse_args(["config"])
            
            exit_code = cmd_config(args)
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "API Configuration Status:" in captured.out
            assert "DEEPSEEK_API_KEY: ✓ set" in captured.out
            assert "ELEVENLABS_API_KEY: ✓ set" in captured.out
            assert "PEXELS_API_KEY: ✓ set" in captured.out
            # Ensure actual keys are not printed
            assert "test_key_1" not in captured.out
            assert "test_key_2" not in captured.out
            assert "test_key_3" not in captured.out
    
    def test_config_some_keys_missing(self, mock_env_vars, capsys):
        """Test config command when some API keys are missing."""
        parser = create_parser()
        args = parser.parse_args(["config"])
        
        exit_code = cmd_config(args)
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "API Configuration Status:" in captured.out
        assert "DEEPSEEK_API_KEY: ✓ set" in captured.out
        assert "ELEVENLABS_API_KEY: ✓ set" in captured.out
        assert "PEXELS_API_KEY: ✗ not set" in captured.out
    
    def test_config_no_keys_set(self, capsys):
        """Test config command when no API keys are set."""
        with patch("pdf2video.cli.os.getenv", return_value=None):
            parser = create_parser()
            args = parser.parse_args(["config"])
            
            exit_code = cmd_config(args)
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "API Configuration Status:" in captured.out
            assert "DEEPSEEK_API_KEY: ✗ not set" in captured.out
            assert "ELEVENLABS_API_KEY: ✗ not set" in captured.out
            assert "PEXELS_API_KEY: ✗ not set" in captured.out


class TestParser:
    """Tests for argument parser."""
    
    def test_parser_version(self, capsys):
        """Test --version flag."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out
    
    def test_parser_help(self, capsys):
        """Test --help flag."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "pdf2video" in captured.out
        assert "Convert PDF documents into engaging video presentations" in captured.out
    
    def test_parser_generate_help(self, capsys):
        """Test generate --help."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["generate", "--help"])
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Convert a PDF or TXT document" in captured.out
        assert "--input" in captured.out
        assert "--output" in captured.out
        assert "--no-cleanup" in captured.out
    
    def test_parser_generate_missing_required_args(self, capsys):
        """Test generate command with missing required arguments."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["generate"])
        
        # argparse exits with code 2 for argument errors
        assert exc_info.value.code == 2


class TestMain:
    """Tests for main entry point."""
    
    def test_main_no_command(self, capsys):
        """Test main with no command shows help."""
        with patch.object(sys, "argv", ["pdf2video"]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "pdf2video" in captured.out
    
    def test_main_info_command(self, capsys):
        """Test main with info command."""
        with patch.object(sys, "argv", ["pdf2video", "info"]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Version: 0.1.0" in captured.out
    
    def test_main_config_command(self, capsys):
        """Test main with config command."""
        with patch.object(sys, "argv", ["pdf2video", "config"]):
            with patch("pdf2video.cli.os.getenv", return_value=None):
                exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "API Configuration Status:" in captured.out
    
    def test_main_generate_command(self, sample_pdf, mock_run_pipeline, capsys):
        """Test main with generate command."""
        with patch.object(sys, "argv", [
            "pdf2video",
            "generate",
            "--input", str(sample_pdf),
            "--output", "output.mp4",
        ]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "✓ Video created successfully" in captured.out
    
    def test_main_keyboard_interrupt(self, sample_pdf, capsys):
        """Test main with keyboard interrupt during command execution."""
        with patch("pdf2video.cli.run_pipeline", side_effect=KeyboardInterrupt()):
            with patch.object(sys, "argv", [
                "pdf2video",
                "generate",
                "--input", str(sample_pdf),
                "--output", "output.mp4",
            ]):
                exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Operation cancelled by user" in captured.err
    
    def test_main_unexpected_error(self, sample_pdf, capsys):
        """Test main with unexpected error during command execution."""
        with patch("pdf2video.cli.run_pipeline", side_effect=RuntimeError("Unexpected")):
            with patch.object(sys, "argv", [
                "pdf2video",
                "generate",
                "--input", str(sample_pdf),
                "--output", "output.mp4",
            ]):
                exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error: Unexpected" in captured.err
