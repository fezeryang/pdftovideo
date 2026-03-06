"""Tests for video download functionality."""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
video_downloader = importlib.import_module("pdf2video.video_downloader")
types_module = importlib.import_module("pdf2video.types")

VideoDownloadError = video_downloader.VideoDownloadError
download_video = video_downloader.download_video
VideoClip = types_module.VideoClip


@pytest.fixture
def mock_env_and_requests():
    real_import = importlib.import_module
    
    with patch("pdf2video.video_downloader.os.getenv") as mock_getenv, \
         patch("pdf2video.video_downloader.importlib.import_module") as mock_import:
        
        mock_getenv.return_value = "test_api_key"
        
        mock_dotenv = MagicMock()
        mock_requests = MagicMock()
        
        def import_side_effect(module_name):
            if module_name == "dotenv":
                return mock_dotenv
            elif module_name == "requests":
                return mock_requests
            return real_import(module_name)
        
        mock_import.side_effect = import_side_effect
        
        yield mock_requests, mock_getenv


def test_download_video_success(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "hd",
                "height": 1080,
                "link": "https://example.com/video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.iter_content.return_value = [b"chunk1", b"chunk2"]
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test video"
    )
    
    with patch("builtins.open", mock_open()) as mock_file, \
         patch("pathlib.Path.mkdir"):
        
        result = download_video(clip, cache_dir="./test_cache")
        
        assert mock_requests.get.call_count == 2
        
        metadata_call = mock_requests.get.call_args_list[0]
        assert "https://api.pexels.com/videos/videos/12345" in metadata_call[0]
        assert metadata_call[1]["headers"] == {"Authorization": "test_api_key"}
        
        download_call = mock_requests.get.call_args_list[1]
        assert "https://example.com/video.mp4" in download_call[0]
        assert download_call[1]["stream"] is True
        
        mock_file.assert_called_once()
        handle = mock_file()
        assert handle.write.call_count == 2
        
        assert result.file_path == Path("./test_cache/pexels_12345.mp4")
        assert result.duration == 30.5
        assert result.search_query == "test video"


def test_download_video_prefers_hd_quality(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "sd",
                "height": 720,
                "link": "https://example.com/sd_video.mp4"
            },
            {
                "quality": "hd",
                "height": 1080,
                "link": "https://example.com/hd_video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.iter_content.return_value = [b"chunk"]
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with patch("builtins.open", mock_open()), \
         patch("pathlib.Path.mkdir"):
        
        download_video(clip)
        
        download_call = mock_requests.get.call_args_list[1]
        assert "hd_video.mp4" in download_call[0][0]


def test_download_video_fallback_to_sd(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "sd",
                "height": 720,
                "link": "https://example.com/sd_video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.iter_content.return_value = [b"chunk"]
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with patch("builtins.open", mock_open()), \
         patch("pathlib.Path.mkdir"):
        
        result = download_video(clip)
        
        download_call = mock_requests.get.call_args_list[1]
        assert "sd_video.mp4" in download_call[0][0]


def test_download_video_invalid_path_format(mock_env_and_requests):
    clip = VideoClip(
        file_path=Path("invalid_format.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="Invalid placeholder path format"):
        download_video(clip)


def test_download_video_api_rate_limit(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"X-Ratelimit-Reset": "1234567890"}
    mock_requests.get.return_value = mock_response
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="rate limit exceeded"):
        download_video(clip)


def test_download_video_not_found(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_requests.get.return_value = mock_response
    
    clip = VideoClip(
        file_path=Path("pexels_99999.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="not found"):
        download_video(clip)


def test_download_video_no_video_files(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": []
    }
    mock_requests.get.return_value = mock_response
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="No video files available"):
        download_video(clip)


def test_download_video_missing_api_key(mock_env_and_requests):
    _, mock_getenv = mock_env_and_requests
    
    mock_getenv.return_value = None
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="PEXELS_API_KEY environment variable is not set"):
        download_video(clip)


def test_download_video_download_failure(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "hd",
                "link": "https://example.com/video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 500
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with pytest.raises(VideoDownloadError, match="Failed to download video"):
        download_video(clip)


def test_download_video_permission_error(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "hd",
                "link": "https://example.com/video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.iter_content.return_value = [b"chunk"]
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with patch("builtins.open", side_effect=PermissionError("Access denied")), \
         patch("pathlib.Path.mkdir"):
        
        with pytest.raises(VideoDownloadError, match="Permission denied"):
            download_video(clip)


def test_download_video_creates_cache_directory(mock_env_and_requests):
    mock_requests, _ = mock_env_and_requests
    
    mock_metadata_response = MagicMock()
    mock_metadata_response.status_code = 200
    mock_metadata_response.json.return_value = {
        "id": 12345,
        "duration": 30.5,
        "video_files": [
            {
                "quality": "hd",
                "link": "https://example.com/video.mp4"
            }
        ]
    }
    
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.iter_content.return_value = [b"chunk"]
    
    mock_requests.get.side_effect = [mock_metadata_response, mock_download_response]
    
    clip = VideoClip(
        file_path=Path("pexels_12345.mp4"),
        duration=30.0,
        search_query="test"
    )
    
    with patch("builtins.open", mock_open()) as mock_file, \
         patch("pathlib.Path.mkdir") as mock_mkdir:
        
        download_video(clip, cache_dir="./custom_cache")
        
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
