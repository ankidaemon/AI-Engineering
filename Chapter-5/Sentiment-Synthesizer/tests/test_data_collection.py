"""
Tests for data collection module.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.data_collection import DataCollector
from config import Config


class TestDataCollector:
    """Test cases for DataCollector class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.USE_MOCK_DATA_ON_FAILURE = True
        return config

    @pytest.fixture
    def collector(self, config):
        """Create DataCollector instance."""
        return DataCollector(config)

    def test_collector_initialization(self, collector):
        """Test DataCollector initializes properly."""
        assert collector is not None
        assert hasattr(collector, 'config')

    def test_mock_twitter_data(self, collector):
        """Test mock Twitter data generation."""
        data = collector._get_mock_twitter_data()
        
        assert isinstance(data, list)
        assert len(data) > 0
        assert all('text' in item for item in data)
        assert all('source' in item for item in data)
        assert all(item['source'] == 'twitter' for item in data)

    def test_mock_reddit_data(self, collector):
        """Test mock Reddit data generation."""
        data = collector._get_mock_reddit_data()
        
        assert isinstance(data, list)
        assert len(data) > 0
        assert all('text' in item for item in data)
        assert all('source' in item for item in data)
        assert all(item['source'] == 'reddit' for item in data)

    def test_collect_data_with_mock(self, collector):
        """Test data collection with mock data."""
        with patch.object(collector, '_get_twitter_data', return_value=[]):
            with patch.object(collector, '_get_reddit_data', return_value=[]):
                data = collector.collect_data()
        
        assert isinstance(data, list)
        # Should have mock data since APIs fail
        assert len(data) > 0

    def test_data_structure(self, collector):
        """Test collected data has correct structure."""
        data = collector._get_mock_twitter_data()
        
        for item in data:
            assert 'text' in item
            assert 'source' in item
            assert 'timestamp' in item
            assert isinstance(item['text'], str)
            assert len(item['text']) > 0

    def test_mock_data_not_empty(self, collector):
        """Test that mock data is not empty."""
        twitter_data = collector._get_mock_twitter_data()
        reddit_data = collector._get_mock_reddit_data()
        
        assert len(twitter_data) > 0
        assert len(reddit_data) > 0

    def test_data_collection_returns_list(self, collector):
        """Test that collect_data returns a list."""
        result = collector.collect_data()
        assert isinstance(result, list)

    def test_data_collection_contains_text_field(self, collector):
        """Test that collected data contains text field."""
        data = collector.collect_data()
        
        for item in data:
            assert 'text' in item
            assert isinstance(item['text'], str)
            assert len(item['text']) > 0
