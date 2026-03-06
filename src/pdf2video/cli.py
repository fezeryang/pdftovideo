"""Command-line interface for PDF to Video conversion pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from pdf2video import __author__, __version__
from pdf2video.pipeline import PipelineError, run_pipeline

# Load environment variables from .env file
load_dotenv()


logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Exception for CLI-specific errors."""
    pass


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )


def cmd_generate(args: argparse.Namespace) -> int:
    """Execute the generate command to convert PDF or TXT to video.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    input_path = Path(args.input)
    output_path = args.output
    
    # Validate input file exists and is correct format
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1
    
    if not input_path.is_file():
        print(f"Error: Input path is not a file: {args.input}", file=sys.stderr)
        return 1
    
    # Validate file extension
    valid_extensions = {'.pdf', '.txt'}
    if input_path.suffix.lower() not in valid_extensions:
        print(f"Error: Unsupported file format. Expected .pdf or .txt, got {input_path.suffix}", file=sys.stderr)
        return 1
    try:
        logger.info("Starting document to video conversion...")
        final_video = run_pipeline(
            input_path=str(input_path),
            output_path=output_path,
            cleanup=not args.no_cleanup,
            enable_subtitles=args.subtitles,
            enable_emphasis=not args.no_emphasis,
            sticker_config=Path(args.stickers) if args.stickers else None,
            skip_tts=args.no_tts,
        )
        print(f"✓ Video created successfully: {final_video.file_path}")
        return 0
    except PipelineError as exc:
        print(f"Error: Pipeline failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nError: Operation cancelled by user", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: Unexpected error occurred: {exc}", file=sys.stderr)
        print("Please report this issue at: https://github.com/pdf2video/pdf2video/issues", file=sys.stderr)
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Display project information.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (always 0)
    """
    print("PDF to Video Conversion Pipeline")
    print(f"Version: {__version__}")
    print(f"Author: {__author__}")
    print("A Python package for converting PDF documents into engaging video presentations")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Display API configuration status.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (always 0)
    """
    api_keys = {
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        "PEXELS_API_KEY": os.getenv("PEXELS_API_KEY"),
    }
    
    print("API Configuration Status:")
    for key_name, key_value in api_keys.items():
        status = "✓ set" if key_value else "✗ not set"
        print(f"  {key_name}: {status}")
    
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="pdf2video",
        description="Convert PDF documents into engaging video presentations",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
    )
    
    # Generate command
    parser_generate = subparsers.add_parser(
        "generate",
        help="Convert PDF or TXT to video",
        description="Convert a PDF or TXT document into a video presentation with AI-generated narration",
    )
    parser_generate.add_argument(
        "--input",
        required=True,
        help="Path to input file (.pdf or .txt)",
    )
    parser_generate.add_argument(
        "--output",
        required=True,
        help="Path to output video file (e.g., video.mp4)",
    )
    parser_generate.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep intermediate files (audio, downloaded clips)",
    )
    parser_generate.add_argument(
        "--subtitles",
        action="store_true",
        help="Enable subtitle generation in the video",
    )
    parser_generate.add_argument(
        "--stickers",
        help="Path to sticker configuration JSON file",
    )
    parser_generate.add_argument(
        "--no-emphasis",
        action="store_true",
        help="Disable AI keyword detection for emphasis",
    )
    parser_generate.add_argument(
        "--no-tts",
        action="store_true",
        help="Skip TTS generation (for testing without ElevenLabs API)",
    )
    parser_generate.set_defaults(func=cmd_generate)
    
    # Info command
    parser_info = subparsers.add_parser(
        "info",
        help="Display project information",
        description="Display package version and project information",
    )
    parser_info.set_defaults(func=cmd_info)
    
    # Config command
    parser_config = subparsers.add_parser(
        "config",
        help="Display API configuration status",
        description="Check which API keys are configured",
    )
    parser_config.set_defaults(func=cmd_config)
    
    return parser


def main() -> int:
    """Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    _setup_logging(verbose=args.verbose)
    
    # If no command specified, print help
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    
    # Execute the command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
