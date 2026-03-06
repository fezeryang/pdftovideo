"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """Create a path to a sample PDF file for testing."""
    return temp_dir / "sample.pdf"


@pytest.fixture
def output_dir(temp_dir):
    """Create an output directory for generated files."""
    output = temp_dir / "output"
    output.mkdir()
    return output
