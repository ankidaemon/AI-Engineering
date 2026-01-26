"""
Text preprocessing module
Implements BERT-style tokenization and cleaning
"""

import re
import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import numpy as np
from tqdm import tqdm

from transformers import AutoTokenizer

logger = logging.getLogger(__name__)


class Preprocessor:
    """Handles text preprocessing and tokenization"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.DATA_DIR / "processed"
        self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        
    def preprocess(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess raw data"""
        logger.info("Starting preprocessing pipeline...")
        
        processed = []
        for item in tqdm(raw_data, desc="Preprocessing"):
            cleaned_text = self._clean_text(item['text'])
            tokens = self.tokenizer.encode(
                cleaned_text,
                max_length=self.config.MAX_SEQUENCE_LENGTH,
                truncation=True,
                padding='max_length',
                return_tensors=None
            )
            
            processed.append({
                'id': item['id'],
                'source': item.get('source'),
                'original_text': item['text'],
                'cleaned_text': cleaned_text,
                'tokens': tokens,
                'token_count': len(tokens),
                'timestamp': item.get('timestamp'),
                'metrics': item.get('metrics', {})
            })
        
        # Save processed data
        self._save_data(processed)
        return processed
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing URLs, mentions, etc."""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove mentions (@user)
        text = re.sub(r'@\w+', '', text)
        # Remove hashtags but keep text
        text = re.sub(r'#(\w+)', r'\1', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters except basic punctuation
        text = re.sub(r'[^\w\s.!?-]', '', text)
        return text.lower()
    
    def _save_data(self, data: List[Dict[str, Any]]):
        """Save processed data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"processed_data_{timestamp}.json"
        
        # Convert tokens to list for JSON serialization
        data_to_save = []
        for item in data:
            item_copy = item.copy()
            item_copy['tokens'] = item_copy['tokens']  # Already a list
            data_to_save.append(item_copy)
        
        with open(filepath, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        
        logger.info(f"✅ Processed data saved to {filepath}")
