# PDF to Video Automation Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Automatically convert PDF research documents into narrated videos with AI voiceover and stock footage.

## Features

- **PDF Extraction**: Extracts text and images from PDF documents using PyMuPDF.
- **AI Script Generation**: Automatically generates engaging video scripts from PDF content using OpenAI GPT-4.
- **Natural Voiceover**: Converts scripts into high-quality audio using ElevenLabs TTS.
- **Stock Footage Integration**: Searches for and downloads relevant stock videos from Pexels based on script content.
- **Automated Composition**: Combines audio, video clips, and transitions into a final MP4 presentation using MoviePy.
- **Robust Pipeline**: Includes retry logic with exponential backoff for all network operations.
- **Comprehensive Testing**: Over 80 tests ensuring reliability across all modules.
- **Subtitles**: Automatically generate and burn subtitles into the video.
- **Stickers**: Add images or logos as stickers with custom timing and positioning.

## Prerequisites

- Python 3.10 or higher
- API keys for OpenAI, ElevenLabs, and Pexels
- FFmpeg (optional, but recommended for optimal subtitle performance)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/pdftovideo.git
   cd pdftovideo
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

## API Setup

The pipeline requires three API keys to function. Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

### OpenAI (GPT-4)
- **Purpose**: Used for generating the video script and narration from the extracted PDF text.
- **Key**: `OPENAI_API_KEY`
- **Get it here**: [OpenAI API Keys](https://platform.openai.com/api-keys)

### ElevenLabs (TTS)
- **Purpose**: Converts the generated script into natural-sounding speech.
- **Key**: `ELEVENLABS_API_KEY`
- **Get it here**: [ElevenLabs](https://elevenlabs.io/)

### Pexels (Stock Video)
- **Purpose**: Provides relevant stock video clips to accompany the narration.
- **Key**: `PEXELS_API_KEY`
- **Get it here**: [Pexels API](https://www.pexels.com/api/)

## Usage

### Basic Example

To convert a PDF to a video:

```bash
python -m pdf2video.cli generate --input research_paper.pdf --output presentation.mp4
```
### Subtitles and Stickers

You can enhance your videos with subtitles and stickers using the following flags:

```bash
python -m pdf2video.cli generate --input doc.pdf --output video.mp4 --subtitles --stickers examples/sticker_config.json
```

#### Sticker Configuration Format

Stickers are configured via a JSON file. Example `sticker_config.json`:

```json
{
  "stickers": [
    {
      "path": "logo.png",
      "position": "top-right",
      "start_time": 0,
      "end_time": 10,
      "scale": 0.2
    }
  ]
}
```

Supported positions: `center`, `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, or a coordinate tuple `[x, y]`.

### CLI Commands

- `generate`: Convert a PDF document into a video presentation.
  - `--input`: Path to the input PDF file (required).
  - `--output`: Path to the output video file (required).
  - `--no-cleanup`: Keep intermediate files like audio and downloaded clips.
- `--subtitles`: Enable subtitle generation and burning.
- `--stickers`: Path to a JSON configuration file for sticker overlays.
- `--no-emphasis`: Disable text emphasis in generated scripts.
- `info`: Display project metadata (version, author, description).
- `config`: Check which API keys are currently configured in your environment.
- `--version`: Show the current version of the tool.
- `-v, --verbose`: Enable detailed debug logging.

## Project Structure

- `src/pdf2video/extractor.py`: PDF text and image extraction.
- `src/pdf2video/script_generator.py`: LLM-powered script generation.
- `src/pdf2video/tts_engine.py`: ElevenLabs TTS integration with chunking.
- `src/pdf2video/video_searcher.py`: Pexels API video search.
- `src/pdf2video/video_downloader.py`: Pexels video download with quality selection.
- `src/pdf2video/compositor.py`: Video composition using MoviePy.
- `src/pdf2video/pipeline.py`: End-to-end orchestration.
- `src/pdf2video/cli.py`: Command-line interface.
- `src/pdf2video/types.py`: Shared data models and enums.

## Development

### Running Tests

The project includes a comprehensive test suite with 83 tests.

```bash
pytest tests/ -v
```

### Code Quality

We use `black` for formatting and `ruff` for linting.

```bash
black src/ tests/
ruff check src/ tests/
```

## How It Works

1. **Extraction**: The pipeline extracts text from the provided PDF.
2. **Scripting**: OpenAI GPT-4 processes the text to create a structured narration script.
3. **Narration**: ElevenLabs converts the script into high-quality audio.
4. **Visuals**: The pipeline searches Pexels for video clips matching the script's themes.
5. **Download**: Selected clips are downloaded in HD quality.
6. **Composition**: MoviePy merges the audio and video clips, ensuring they are synchronized and correctly formatted.

## Limitations

- Requires an active internet connection for API calls.
- Processing time depends on PDF length and API response times.
- Stock video relevance depends on the quality of the generated search queries.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details (or `pyproject.toml`).
