# Sentiment Synthesizer Package
"""
Sentiment Synthesizer - An advanced NLP system for analyzing and synthesizing 
user sentiment from social media data using pre-trained Transformer models.

Main Components:
    - DataCollector: Collects social media data
    - Preprocessor: Prepares text for analysis
    - EmbeddingGenerator: Creates contextual embeddings
    - SentimentClassifier: Classifies sentiment
    - SentimentSynthesizer: Analyzes trends
    - Visualizer: Creates dashboards and charts
"""

__version__ = "1.0.0"
__author__ = "AI Engineering"
__description__ = "Advanced NLP sentiment analysis pipeline"

from src.data_collection import DataCollector
from src.preprocessing import Preprocessor
from src.embedding_generator import EmbeddingGenerator
from src.sentiment_classifier import SentimentClassifier
from src.sentiment_synthesizer import SentimentSynthesizer
from src.visualization import Visualizer

__all__ = [
    "DataCollector",
    "Preprocessor",
    "EmbeddingGenerator",
    "SentimentClassifier",
    "SentimentSynthesizer",
    "Visualizer",
]
