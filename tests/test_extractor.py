"""Tests for PDF extractor module."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pdf2video.extractor import extract_text, extract_images, PDFExtractionError


class TestExtractText:
    """Tests for extract_text function."""

    def test_extract_text_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_text("nonexistent.pdf")

    def test_extract_text_not_a_file(self, tmp_path):
        """Test that PDFExtractionError is raised when path is not a file."""
        directory = tmp_path / "subdir"
        directory.mkdir()
        with pytest.raises(PDFExtractionError):
            extract_text(str(directory))

    def test_extract_text_returns_string(self, tmp_path):
        """Test that extract_text returns a string."""
        # Create a temp PDF file to bypass file existence check
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()
        
        # Create a mock for fitz.open
        with patch('pdf2video.extractor.fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "Test content"
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page
            mock_open.return_value = mock_doc

            result = extract_text(str(pdf_path))
            assert isinstance(result, str)


class TestExtractImages:
    """Tests for extract_images function."""

    def test_extract_images_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_images("nonexistent.pdf")

    def test_extract_images_not_a_file(self, tmp_path):
        """Test that PDFExtractionError is raised when path is not a file."""
        directory = tmp_path / "subdir"
        directory.mkdir()
        with pytest.raises(PDFExtractionError):
            extract_images(str(directory))

    def test_extract_images_returns_list(self, tmp_path):
        """Test that extract_images returns a list."""
        # Create a temp PDF file to bypass file existence check
        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()
        
        with patch('pdf2video.extractor.fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_page = MagicMock()
            mock_page.get_images.return_value = []
            mock_doc.__getitem__.return_value = mock_page
            mock_open.return_value = mock_doc

            result = extract_images(str(pdf_path))
            assert isinstance(result, list)


class TestPDFExtractionError:
    """Tests for PDFExtractionError exception."""

    def test_exception_can_be_raised(self):
        """Test that PDFExtractionError can be raised."""
        with pytest.raises(PDFExtractionError):
            raise PDFExtractionError("Test error message")

    def test_exception_with_original_error(self):
        """Test that PDFExtractionError can wrap another exception."""
        original = ValueError("Original error")
        with pytest.raises(PDFExtractionError, match="Failed to open"):
            raise PDFExtractionError(f"Failed to open PDF: {original}")
