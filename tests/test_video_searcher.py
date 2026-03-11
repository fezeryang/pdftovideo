import importlib
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

pytest = importlib.import_module("pytest")
video_searcher = importlib.import_module("pdf2video.video_searcher")

VideoSearchError = video_searcher.VideoSearchError
search_videos = video_searcher.search_videos


def test_search_videos_returns_video_clips():
    """Test successful video search returns list of VideoClip objects."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 12345,
                "duration": 30,
                "width": 1920,
                "height": 1080,
                "url": "https://www.pexels.com/video/12345/",
                "video_files": [
                    {
                        "id": 1,
                        "quality": "hd",
                        "link": "https://example.com/video.mp4"
                    }
                ]
            },
            {
                "id": 67890,
                "duration": 15.5,
                "width": 1920,
                "height": 1080,
                "url": "https://www.pexels.com/video/67890/",
                "video_files": [
                    {
                        "id": 2,
                        "quality": "hd",
                        "link": "https://example.com/video2.mp4"
                    }
                ]
            }
        ],
        "page": 1,
        "per_page": 5,
        "total_results": 100
    }
    mock_requests.get.return_value = mock_response
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            results = search_videos("nature", per_page=5, orientation="landscape")
    
    assert len(results) == 2
    assert results[0].duration == 30
    assert results[1].duration == 15.5
    assert results[0].search_query == "nature"
    assert results[1].search_query == "nature"
    assert str(results[0].file_path) == "pexels_12345.mp4"
    assert str(results[1].file_path) == "pexels_67890.mp4"
    
    mock_requests.get.assert_called_once()
    call_args = mock_requests.get.call_args
    assert call_args[0][0] == "https://api.pexels.com/videos/search"
    assert call_args[1]["headers"] == {"Authorization": "test_api_key"}
    assert call_args[1]["params"]["query"] == "nature"
    assert call_args[1]["params"]["per_page"] == 5
    assert call_args[1]["params"]["orientation"] == "landscape"


def test_search_videos_returns_empty_list_when_no_results():
    """Test that empty results list is returned when no videos found."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [],
        "page": 1,
        "per_page": 5,
        "total_results": 0
    }
    mock_requests.get.return_value = mock_response
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            results = search_videos("nonexistent_query_xyz")
    
    assert results == []


def test_search_videos_handles_rate_limit_error():
    """Test that rate limit error is handled properly."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {"X-Ratelimit-Reset": "1234567890"}
    mock_response.text = "Rate limit exceeded"
    mock_requests.get.return_value = mock_response
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            with pytest.raises(VideoSearchError, match="rate limit exceeded"):
                search_videos("nature")


def test_search_videos_handles_api_failure():
    """Test that API failure is handled properly."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    mock_requests.get.return_value = mock_response
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            with pytest.raises(VideoSearchError, match="Pexels API request failed with status 500"):
                search_videos("nature")


def test_search_videos_raises_when_api_key_missing():
    """Test that missing API key raises VideoSearchError."""
    mock_dotenv = Mock()
    
    with patch("pdf2video.video_searcher.os.getenv", return_value=None):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            return_value=mock_dotenv,
        ):
            with pytest.raises(VideoSearchError, match="PEXELS_API_KEY environment variable is not set"):
                search_videos("nature")
    
    mock_dotenv.load_dotenv.assert_called_once()


def test_search_videos_validates_empty_query():
    """Test that empty query raises VideoSearchError."""
    with pytest.raises(VideoSearchError, match="Search query cannot be empty"):
        search_videos("")


def test_search_videos_validates_per_page_range():
    """Test that per_page parameter is validated."""
    with pytest.raises(VideoSearchError, match="per_page must be between 1 and 80"):
        search_videos("nature", per_page=0)
    
    with pytest.raises(VideoSearchError, match="per_page must be between 1 and 80"):
        search_videos("nature", per_page=100)


def test_search_videos_validates_orientation():
    """Test that orientation parameter is validated."""
    with pytest.raises(VideoSearchError, match="orientation must be one of"):
        search_videos("nature", orientation="invalid")


def test_search_videos_handles_network_error():
    """Test that network errors are handled properly."""
    mock_requests = Mock()
    mock_requests.get.side_effect = Exception("Network timeout")
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            with pytest.raises(VideoSearchError, match="Failed to search videos"):
                search_videos("nature")


def test_search_videos_handles_invalid_video_data():
    """Test that invalid video data in response is handled."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [
            {
                # Missing 'id' field
                "duration": 30,
                "width": 1920,
                "height": 1080,
            }
        ],
        "page": 1,
        "per_page": 5,
        "total_results": 1
    }
    mock_requests.get.return_value = mock_response
    
    with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
        with patch(
            "pdf2video.video_searcher.importlib.import_module",
            side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
        ):
            with pytest.raises(VideoSearchError, match="Video data missing required 'id' field"):
                search_videos("nature")


def test_search_videos_uses_correct_orientation():
    """Test that different orientation values are passed correctly."""
    mock_requests = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"videos": []}
    mock_requests.get.return_value = mock_response
    
    for orientation in ["landscape", "portrait", "square"]:
        with patch("pdf2video.video_searcher.os.getenv", return_value="test_api_key"):
            with patch(
                "pdf2video.video_searcher.importlib.import_module",
                side_effect=lambda name: Mock() if name == "dotenv" else mock_requests,
            ):
                search_videos("nature", orientation=orientation)
        
        call_args = mock_requests.get.call_args
        assert call_args[1]["params"]["orientation"] == orientation
