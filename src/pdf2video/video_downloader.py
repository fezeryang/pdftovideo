"""Video download functionality using Pexels API."""

from __future__ import annotations

import importlib
import logging
import os
import time
from pathlib import Path
from typing import Any

from pdf2video.types import VideoClip
logger = logging.getLogger(__name__)


class VideoDownloadError(Exception):
    """Exception raised for video download errors."""
    pass


def _create_client() -> Any:
    """Create and configure Pexels API client.
    
    Returns:
        Configured requests module for API calls.
        
    Raises:
        VideoDownloadError: If API key is not set.
    """
    dotenv = importlib.import_module("dotenv")
    
    dotenv.load_dotenv()
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise VideoDownloadError("PEXELS_API_KEY environment variable is not set")
    
    requests = importlib.import_module("requests")
    return requests, api_key


def _parse_video_id(file_path: Path) -> int:
    """Parse video ID from placeholder file path.
    
    Args:
        file_path: Placeholder path in format "pexels_{video_id}.mp4".
        
    Returns:
        Extracted video ID as integer.
        
    Raises:
        VideoDownloadError: If path format is invalid or video ID cannot be parsed.
    """
    try:
        filename = file_path.stem  # Get filename without extension
        if not filename.startswith("pexels_"):
            raise VideoDownloadError(
                f"Invalid placeholder path format: {file_path}. Expected 'pexels_{{video_id}}.mp4'"
            )
        
        video_id_str = filename.replace("pexels_", "")
        video_id = int(video_id_str)
        return video_id
    except (ValueError, AttributeError) as exc:
        raise VideoDownloadError(
            f"Failed to parse video ID from path '{file_path}': {exc}"
        ) from exc


def _get_download_url(requests: Any, api_key: str, video_id: int) -> tuple[str, float]:
    """Fetch video download URL from Pexels API.
    
    Args:
        requests: Requests module.
        api_key: Pexels API key.
        video_id: Video ID to fetch.
        
    Returns:
        Tuple of (download_url, duration) for the video.
        
    Raises:
        VideoDownloadError: If API request fails or video not found.
    """
    logger.debug("Fetching download URL for video ID: %d", video_id)
    url = f"https://api.pexels.com/videos/videos/{video_id}"
    headers = {"Authorization": api_key}
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug("Sending Pexels API request for video metadata (attempt %d/%d)", attempt + 1, max_retries)
            response = requests.get(url, headers=headers, timeout=30)
            
            # Check for rate limit
            if response.status_code == 429:
                rate_limit_reset = response.headers.get("X-Ratelimit-Reset", "unknown")
                logger.error("Pexels API rate limit exceeded (resets at: %s)", rate_limit_reset)
                raise VideoDownloadError(
                    f"Pexels API rate limit exceeded. Resets at timestamp: {rate_limit_reset}"
                )
            
            # Check for not found
            if response.status_code == 404:
                logger.error("Video ID %d not found", video_id)
                raise VideoDownloadError(f"Video with ID {video_id} not found")
            
            # Check for other errors
            if response.status_code != 200:
                logger.error("Pexels API request failed with status %d: %s", response.status_code, response.text[:200])
                raise VideoDownloadError(
                    f"Pexels API request failed with status {response.status_code}: {response.text}"
                )
            
            data = response.json()
            video_files = data.get("video_files", [])
            
            if not video_files:
                logger.error("No video files available for video ID %d", video_id)
                raise VideoDownloadError(f"No video files available for video ID {video_id}")
            
            # Prefer HD (1080p) quality, fallback to highest available
            hd_video = None
            sd_video = None
            
            for video_file in video_files:
                quality = video_file.get("quality", "").lower()
                if quality == "hd" or video_file.get("height") == 1080:
                    hd_video = video_file
                    break
                elif quality == "sd":
                    sd_video = video_file
            
            # Select best available video
            selected_video = hd_video or sd_video or video_files[0]
            download_url = selected_video.get("link")
            quality = selected_video.get("quality", "unknown")
            logger.info("Selected video quality: %s for video ID %d", quality, video_id)
            
            if not download_url:
                logger.error("No download URL available for video ID %d", video_id)
                raise VideoDownloadError(f"No download URL available for video ID {video_id}")
            
            # Get duration from main video data
            duration = float(data.get("duration", 0))
            logger.debug("Video ID %d: duration=%.2fs, download_url=%s", video_id, duration, download_url[:50])
            
            return download_url, duration
            
        except VideoDownloadError:
            raise
        except Exception as exc:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(
                    "Pexels API call failed for video %d (attempt %d/%d): %s. Retrying in %ds...",
                    video_id, attempt + 1, max_retries, exc, wait_time
                )
                time.sleep(wait_time)
            else:
                logger.error("Pexels API call failed for video %d after %d attempts: %s", video_id, max_retries, exc)
                raise VideoDownloadError(f"Failed to fetch video metadata: {exc}") from exc
    # Should never reach here due to raise in loop
    raise VideoDownloadError("Failed to fetch video metadata after all retries")


def _download_file(requests: Any, url: str, output_path: Path) -> None:
    """Download file from URL to local path.
    
    Args:
        requests: Requests module.
        url: Download URL.
        output_path: Local file path to save to.
        
    Raises:
        VideoDownloadError: If download fails or disk operation fails.
    """
    logger.debug("Starting file download to: %s", output_path)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with streaming to avoid memory issues
            logger.debug("Downloading video (attempt %d/%d)", attempt + 1, max_retries)
            response = requests.get(url, stream=True, timeout=60)
            
            if response.status_code != 200:
                raise VideoDownloadError(
                    f"Failed to download video: HTTP {response.status_code}"
                )
            
            # Write in chunks
            total_bytes = 0
            with open(output_path, "wb") as fd:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        fd.write(chunk)
                        total_bytes += len(chunk)
            
            logger.info("Downloaded video successfully: %s (%.2f MB)", output_path.name, total_bytes / 1024 / 1024)
            return  # Success, exit function
                    
        except VideoDownloadError:
            raise
        except PermissionError as exc:
            raise VideoDownloadError(
                f"Permission denied writing to {output_path}: {exc}"
            ) from exc
        except OSError as exc:
            raise VideoDownloadError(
                f"Disk error writing to {output_path}: {exc}"
            ) from exc
        except Exception as exc:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(
                    "Download failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt + 1, max_retries, exc, wait_time
                )
                time.sleep(wait_time)
            else:
                logger.error("Download failed after %d attempts: %s", max_retries, exc)
                raise VideoDownloadError(f"Failed to download file: {exc}") from exc


def download_video(
    video_clip: VideoClip,
    cache_dir: str = "./cache/videos"
) -> VideoClip:
    """Download video from Pexels and save to local cache.
    
    Args:
        video_clip: VideoClip object with placeholder file path.
        cache_dir: Directory to save downloaded videos (default: "./cache/videos").
        
    Returns:
        Updated VideoClip with actual local file path.
        
    Raises:
        VideoDownloadError: If download fails, API error, or disk operation fails.
    """
    logger.info("Downloading video for query: '%s'", video_clip.search_query)
    # Parse video ID from placeholder path
    video_id = _parse_video_id(video_clip.file_path)
    logger.debug("Parsed video ID: %d", video_id)
    # Parse video ID from placeholder path
    video_id = _parse_video_id(video_clip.file_path)
    
    # Get download URL and duration
    requests, api_key = _create_client()
    download_url, duration = _get_download_url(requests, api_key, video_id)
    
    # Prepare output path
    cache_path = Path(cache_dir)
    output_filename = f"pexels_{video_id}.mp4"
    output_path = cache_path / output_filename
    logger.debug("Output path: %s", output_path)
    
    # Download video
    _download_file(requests, download_url, output_path)
    
    # Return updated VideoClip
    return VideoClip(
        file_path=output_path,
        duration=duration,
        search_query=video_clip.search_query,
    )
