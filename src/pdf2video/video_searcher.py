"""Video search functionality using Pexels API."""

from __future__ import annotations

import importlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from pdf2video.types import VideoClip
logger = logging.getLogger(__name__)


class VideoSearchError(Exception):
    """Exception raised for video search errors."""
    pass


def _create_client() -> Any:
    """Create and configure Pexels API client.
    
    Returns:
        Configured requests module for API calls.
        
    Raises:
        VideoSearchError: If API key is not set.
    """
    dotenv = importlib.import_module("dotenv")
    
    dotenv.load_dotenv()
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise VideoSearchError("PEXELS_API_KEY environment variable is not set")
    
    requests = importlib.import_module("requests")
    return requests, api_key


def _parse_video_response(video_data: Dict[str, Any], search_query: str) -> VideoClip:
    """Parse Pexels API video response into VideoClip.
    
    Args:
        video_data: Video object from Pexels API response.
        search_query: The search query used to find this video.
        
    Returns:
        VideoClip object with video metadata.
        
    Raises:
        VideoSearchError: If video data is invalid or missing required fields.
    """
    try:
        duration = float(video_data.get("duration", 0))
        
        # For search results, file_path is initially empty (will be populated during download)
        # We store a placeholder that includes the video ID for later download
        video_id = video_data.get("id")
        if not video_id:
            raise VideoSearchError("Video data missing required 'id' field")
        
        # Use a placeholder path pattern that download module can recognize
        placeholder_path = Path(f"pexels_{video_id}.mp4")
        
        return VideoClip(
            file_path=placeholder_path,
            duration=duration,
            search_query=search_query,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise VideoSearchError(f"Failed to parse video data: {exc}") from exc


def search_videos(
    query: str,
    per_page: int = 5,
    orientation: str = "landscape"
) -> List[VideoClip]:
    """Search for videos using Pexels API.
    
    Args:
        query: Search query string (e.g., "nature", "city", "people working").
        per_page: Number of results to return (default: 5, max: 80).
        orientation: Video orientation - "landscape", "portrait", or "square" (default: "landscape").
        
    Returns:
        List of VideoClip objects with video metadata.
        
    Raises:
        VideoSearchError: If API request fails, rate limit exceeded, or invalid parameters.
    """
    logger.info("Searching videos with query: '%s' (per_page=%d, orientation=%s)", query, per_page, orientation)
    if not query or not query.strip():
        logger.error("Search query cannot be empty")
        raise VideoSearchError("Search query cannot be empty")
    
    if per_page < 1 or per_page > 80:
        logger.error("Invalid per_page value: %d (must be 1-80)", per_page)
        raise VideoSearchError("per_page must be between 1 and 80")
    
    valid_orientations = {"landscape", "portrait", "square"}
    if orientation not in valid_orientations:
        logger.error("Invalid orientation: %s (must be one of %s)", orientation, valid_orientations)
        raise VideoSearchError(
            f"orientation must be one of {valid_orientations}, got '{orientation}'"
        )
    
    requests, api_key = _create_client()
    logger.debug("Pexels API client created successfully")
    
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query.strip(),
        "per_page": per_page,
        "orientation": orientation,
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug("Sending Pexels API request (attempt %d/%d)", attempt + 1, max_retries)
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Check for rate limit
            if response.status_code == 429:
                rate_limit_reset = response.headers.get("X-Ratelimit-Reset", "unknown")
                logger.error("Pexels API rate limit exceeded (resets at: %s)", rate_limit_reset)
                raise VideoSearchError(
                    f"Pexels API rate limit exceeded. Resets at timestamp: {rate_limit_reset}"
                )
            
            # Check for other errors
            if response.status_code != 200:
                logger.error("Pexels API request failed with status %d: %s", response.status_code, response.text[:200])
                raise VideoSearchError(
                    f"Pexels API request failed with status {response.status_code}: {response.text}"
                )
            
            data = response.json()
            videos = data.get("videos", [])
            logger.info("Pexels API returned %d videos for query '%s'", len(videos), query)
            
            if not videos:
                return []
            
            return [_parse_video_response(video, query) for video in videos]
            
        except VideoSearchError:
            raise
        except Exception as exc:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(
                    "Pexels API call failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, max_retries, exc, wait_time
                )
                time.sleep(wait_time)
            else:
                logger.error("Pexels API call failed after %d attempts: %s", max_retries, exc)
                raise VideoSearchError(f"Failed to search videos: {exc}") from exc
    # Should never reach here due to raise in loop
    raise VideoSearchError("Failed to search videos after all retries")
