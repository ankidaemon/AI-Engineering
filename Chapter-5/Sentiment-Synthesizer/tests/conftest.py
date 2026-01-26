"""
Pytest configuration and fixtures for Sentiment Synthesizer tests.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def mock_texts():
    """Provide sample texts for testing."""
    return [
        "I absolutely love this product! It's amazing!",
        "This is a terrible experience, very disappointed",
        "The weather today is partly cloudy",
        "Best purchase ever made",
        "Don't waste your money on this",
    ]


@pytest.fixture
def sample_embeddings():
    """Provide sample embedding vectors."""
    import numpy as np
    return np.random.randn(5, 768).astype(np.float32)


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent
