"""
Configuration module for Sentiment Synthesizer
Centralized settings for all components
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any
import os
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration class for the entire pipeline"""
    
    # Project structure
    PROJECT_ROOT: Path = Path(__file__).parent
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    OUTPUT_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "output")
    MODELS_DIR: Path = field(default_factory=lambda: Path(__file__).parent / "models")
    
    # Data collection
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "sentiment-synthesizer/1.0"
    
    # Transformer model
    MODEL_NAME: str = "bert-base-uncased"
    EMBEDDING_DIM: int = 768
    MAX_SEQUENCE_LENGTH: int = 128
    
    # Classification
    NUM_CLASSES: int = 3
    SENTIMENT_LABELS: list = field(default_factory=lambda: ["negative", "neutral", "positive"])
    CONFIDENCE_THRESHOLD: float = 0.5
    
    # Training (for fine-tuning)
    BATCH_SIZE: int = 16
    NUM_EPOCHS: int = 3
    LEARNING_RATE: float = 2e-5
    WEIGHT_DECAY: float = 0.01
    
    # Processing
    USE_GPU: bool = True
    NUM_WORKERS: int = 4
    
    # Visualization
    PLOT_DPI: int = 100
    PLOT_STYLE: str = "seaborn-v0_8-darkgrid"
    FIGURE_SIZE: tuple = field(default_factory=lambda: (12, 6))
    
    def __post_init__(self):
        """Initialize directories and load environment variables"""
        # Load environment variables
        load_dotenv()
        
        # Override with environment variables if available
        self.TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", self.TWITTER_API_KEY)
        self.TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", self.TWITTER_API_SECRET)
        self.TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", self.TWITTER_BEARER_TOKEN)
        self.REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", self.REDDIT_CLIENT_ID)
        self.REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", self.REDDIT_CLIENT_SECRET)
        
        # Create directories
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_DIR / "embeddings").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_DIR / "visualizations").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_DIR / "synthesis").mkdir(parents=True, exist_ok=True)
        (self.OUTPUT_DIR / "classifications").mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'model_name': self.MODEL_NAME,
            'embedding_dim': self.EMBEDDING_DIM,
            'max_sequence_length': self.MAX_SEQUENCE_LENGTH,
            'num_classes': self.NUM_CLASSES,
            'batch_size': self.BATCH_SIZE,
            'learning_rate': self.LEARNING_RATE,
            'num_epochs': self.NUM_EPOCHS,
        }
