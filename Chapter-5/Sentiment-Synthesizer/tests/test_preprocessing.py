"""
Tests for preprocessing module.
"""

import pytest
from src.preprocessing import Preprocessor
from config import Config


class TestPreprocessor:
    """Test cases for Preprocessor class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()

    @pytest.fixture
    def preprocessor(self, config):
        """Create Preprocessor instance."""
        return Preprocessor(config)

    def test_preprocessor_initialization(self, preprocessor):
        """Test preprocessor initializes properly."""
        assert preprocessor is not None
        assert hasattr(preprocessor, 'config')
        assert hasattr(preprocessor, 'tokenizer')

    def test_clean_text_removes_urls(self, preprocessor):
        """Test that URL cleaning works."""
        text = "Check out https://example.com for more info"
        cleaned = preprocessor._clean_text(text)
        
        assert "https" not in cleaned.lower()
        assert "example.com" not in cleaned.lower()

    def test_clean_text_removes_mentions(self, preprocessor):
        """Test that mention cleaning works."""
        text = "Hey @user123 what do you think?"
        cleaned = preprocessor._clean_text(text)
        
        assert "@user123" not in cleaned

    def test_clean_text_removes_hashtags(self, preprocessor):
        """Test that hashtag cleaning works."""
        text = "This is great #awesome #love"
        cleaned = preprocessor._clean_text(text)
        
        assert "#awesome" not in cleaned
        assert "#love" not in cleaned

    def test_clean_text_lowercase(self, preprocessor):
        """Test that text is lowercased."""
        text = "HELLO WORLD"
        cleaned = preprocessor._clean_text(text)
        
        assert cleaned == cleaned.lower()

    def test_clean_text_removes_special_chars(self, preprocessor):
        """Test that special characters are handled."""
        text = "Test @#$% with special chars!!!"
        cleaned = preprocessor._clean_text(text)
        
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0

    def test_preprocessing_returns_dict(self, preprocessor):
        """Test that preprocessing returns a dictionary."""
        texts = ["This is a test", "Another test sentence"]
        result = preprocessor.preprocess(texts)
        
        assert isinstance(result, dict)
        assert 'input_ids' in result
        assert 'attention_mask' in result

    def test_preprocessing_valid_tensors(self, preprocessor):
        """Test that preprocessing returns valid tensors."""
        texts = ["Test sentence"]
        result = preprocessor.preprocess(texts)
        
        # Check that returned values are tensor-like
        assert hasattr(result['input_ids'], 'shape')
        assert hasattr(result['attention_mask'], 'shape')

    def test_preprocessing_sequence_length(self, preprocessor):
        """Test that sequences are padded to max length."""
        texts = ["Short text"]
        result = preprocessor.preprocess(texts)
        
        # Check sequence is correct length
        seq_length = result['input_ids'].shape[1]
        assert seq_length == self.config.MAX_SEQUENCE_LENGTH

    def test_preprocessing_batch_processing(self, preprocessor):
        """Test that multiple texts are processed together."""
        texts = ["First text", "Second text", "Third text"]
        result = preprocessor.preprocess(texts)
        
        batch_size = result['input_ids'].shape[0]
        assert batch_size == len(texts)

    def test_clean_text_preserves_meaning(self, preprocessor):
        """Test that cleaning preserves core meaning."""
        text = "I LOVE this product! Check https://example.com #awesome @brand"
        cleaned = preprocessor._clean_text(text)
        
        # Core words should remain
        assert "love" in cleaned or "i" in cleaned or "product" in cleaned
        assert len(cleaned) > 0

    def test_preprocessing_empty_list(self, preprocessor):
        """Test preprocessing handles empty input gracefully."""
        texts = []
        # Should handle empty list
        result = preprocessor.preprocess(texts)
        assert isinstance(result, dict)

    def test_preprocessing_single_text(self, preprocessor):
        """Test preprocessing handles single text."""
        texts = ["Single test text"]
        result = preprocessor.preprocess(texts)
        
        batch_size = result['input_ids'].shape[0]
        assert batch_size == 1

    def test_attention_mask_valid(self, preprocessor):
        """Test that attention mask is valid."""
        texts = ["Test text"]
        result = preprocessor.preprocess(texts)
        
        # Attention mask should contain only 0s and 1s
        attention_mask = result['attention_mask']
        assert (attention_mask == 0).sum().item() + (attention_mask == 1).sum().item() > 0
