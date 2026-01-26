"""
Test package for Sentiment Synthesizer.

This package contains unit tests and integration tests for all modules.

Test Organization:
    - test_data_collection.py: Tests for data collection module
    - test_preprocessing.py: Tests for preprocessing module  
    - test_sentiment_classifier.py: Tests for sentiment classification
    - test_utils.py: Tests for utility functions
    - conftest.py: Shared pytest fixtures and configuration

Running Tests:
    # Run all tests
    pytest
    
    # Run specific test file
    pytest tests/test_data_collection.py
    
    # Run with coverage
    pytest --cov=src
    
    # Run specific marker
    pytest -m unit  # Only unit tests
    
    # Run verbose output
    pytest -v
"""

__version__ = "1.0.0"
