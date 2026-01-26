"""
Tests for sentiment classification module.
"""

import pytest
import numpy as np
from src.sentiment_classifier import SentimentClassifier
from config import Config


class TestSentimentClassifier:
    """Test cases for SentimentClassifier class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.NUM_CLASSES = 3
        config.SENTIMENT_LABELS = ["negative", "neutral", "positive"]
        return config

    @pytest.fixture
    def classifier(self, config):
        """Create SentimentClassifier instance."""
        return SentimentClassifier(config)

    def test_classifier_initialization(self, classifier):
        """Test classifier initializes properly."""
        assert classifier is not None
        assert hasattr(classifier, 'config')
        assert hasattr(classifier, 'device')

    def test_heuristic_sentiment(self, classifier):
        """Test heuristic sentiment scoring."""
        # Test positive text
        positive_scores = classifier._heuristic_sentiment("I love this product, it's amazing!")
        assert positive_scores['positive'] > positive_scores['negative']
        
        # Test negative text
        negative_scores = classifier._heuristic_sentiment("This is terrible and awful")
        assert negative_scores['negative'] > negative_scores['positive']

    def test_heuristic_sentiment_returns_dict(self, classifier):
        """Test heuristic sentiment returns proper dictionary."""
        scores = classifier._heuristic_sentiment("test text")
        
        assert isinstance(scores, dict)
        assert 'positive' in scores
        assert 'negative' in scores
        assert 'neutral' in scores

    def test_softmax_normalization(self, classifier):
        """Test softmax normalization."""
        logits = np.array([1.0, 2.0, 3.0])
        probs = classifier._softmax(logits)
        
        # Check probabilities sum to 1
        assert np.isclose(probs.sum(), 1.0)
        
        # Check values are between 0 and 1
        assert np.all(probs >= 0)
        assert np.all(probs <= 1)

    def test_softmax_properties(self, classifier):
        """Test softmax mathematical properties."""
        logits = np.array([0.0, 0.0, 0.0])
        probs = classifier._softmax(logits)
        
        # All equal logits should give equal probabilities
        expected = np.array([1/3, 1/3, 1/3])
        assert np.allclose(probs, expected)

    def test_classification_output_structure(self, classifier):
        """Test classification output has correct structure."""
        # Mock embeddings
        embeddings = np.random.randn(1, 768).astype(np.float32)
        
        result = classifier.classify_sentiment(embeddings, ["test text"])
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert 'sentiment' in result[0]
        assert 'confidence' in result[0]
        assert 'scores' in result[0]

    def test_sentiment_labels_valid(self, classifier, config):
        """Test that sentiment labels are valid."""
        assert config.NUM_CLASSES == len(config.SENTIMENT_LABELS)
        assert "negative" in config.SENTIMENT_LABELS
        assert "neutral" in config.SENTIMENT_LABELS
        assert "positive" in config.SENTIMENT_LABELS

    def test_confidence_score_range(self, classifier):
        """Test that confidence scores are in valid range."""
        embeddings = np.random.randn(1, 768).astype(np.float32)
        
        result = classifier.classify_sentiment(embeddings, ["test"])
        
        for item in result:
            assert 0.0 <= item['confidence'] <= 1.0

    def test_heuristic_sentiment_zero_scores_possible(self, classifier):
        """Test heuristic sentiment can handle text with no keywords."""
        scores = classifier._heuristic_sentiment("Lorem ipsum dolor sit amet")
        
        assert isinstance(scores, dict)
        assert scores['positive'] == 0 or scores['positive'] > 0
        assert scores['negative'] == 0 or scores['negative'] > 0
