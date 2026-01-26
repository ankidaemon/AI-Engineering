"""
Sentiment classification module
Fine-tuned BERT model for sentiment classification
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


class SentimentClassifier:
    """Classifies sentiment using fine-tuned BERT"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.OUTPUT_DIR / "classifications"
        self.device = torch.device("cuda" if torch.cuda.is_available() and config.USE_GPU else "cpu")
        
        logger.info(f"Loading sentiment classifier: {config.MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        
        # Try to load fine-tuned model, fall back to base model
        try:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                config.MODELS_DIR / "sentiment_model"
            ).to(self.device)
        except:
            logger.info("Fine-tuned model not found. Using base model with heuristic scoring.")
            self.model = AutoModelForSequenceClassification.from_pretrained(
                config.MODEL_NAME,
                num_labels=config.NUM_CLASSES
            ).to(self.device)
        
        self.model.eval()
        logger.info(f"Using device: {self.device}")
    
    def classify_sentiment(self, embeddings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify sentiment for embeddings"""
        logger.info("Classifying sentiments...")
        
        classified = []
        
        with torch.no_grad():
            for item in tqdm(embeddings, desc="Classifying"):
                text = item['cleaned_text']
                
                # Tokenize
                inputs = self.tokenizer(
                    text,
                    truncation=True,
                    padding=True,
                    max_length=self.config.MAX_SEQUENCE_LENGTH,
                    return_tensors="pt"
                ).to(self.device)
                
                # Get predictions
                outputs = self.model(**inputs)
                logits = outputs.logits[0].cpu().numpy()
                probabilities = self._softmax(logits)
                
                # Get label
                label_idx = np.argmax(probabilities)
                label = self.config.SENTIMENT_LABELS[label_idx]
                confidence = float(probabilities[label_idx])
                
                # Also compute heuristic score
                heuristic_label, heuristic_scores = self._heuristic_sentiment(text)
                
                # Combine scores (60% model, 40% heuristic)
                final_probs = 0.6 * probabilities + 0.4 * np.array(heuristic_scores)
                final_label_idx = np.argmax(final_probs)
                final_label = self.config.SENTIMENT_LABELS[final_label_idx]
                final_confidence = float(final_probs[final_label_idx])
                
                classified.append({
                    'id': item['id'],
                    'source': item['source'],
                    'text': item['text'],
                    'embedding': item['embedding'],
                    'sentiment': {
                        'label': final_label,
                        'confidence': final_confidence,
                        'scores': final_probs.tolist(),
                        'model_scores': probabilities.tolist(),
                        'heuristic_scores': heuristic_scores
                    },
                    'timestamp': item['timestamp'],
                    'metrics': item['metrics']
                })
        
        # Save classifications
        self._save_classifications(classified)
        return classified
    
    def _heuristic_sentiment(self, text: str) -> tuple:
        """Rule-based sentiment scoring"""
        text_lower = text.lower()
        
        positive_words = [
            'love', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'awesome', 'best', 'perfect', 'good', 'happy', 'beautiful', 'brilliant',
            'impressed', 'satisfied', 'delighted'
        ]
        
        negative_words = [
            'hate', 'bad', 'terrible', 'awful', 'horrible', 'worst', 'poor',
            'disappointed', 'angry', 'sad', 'disgusting', 'useless', 'waste',
            'frustrated', 'upset', 'scam'
        ]
        
        neutral_words = [
            'ok', 'okay', 'alright', 'fine', 'average', 'normal', 'regular'
        ]
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        neu_count = sum(1 for word in neutral_words if word in text_lower)
        
        exclamation_count = text.count('!')
        question_count = text.count('?')
        
        total = pos_count + neg_count + neu_count + exclamation_count + question_count
        
        if total == 0:
            return 'neutral', [0.33, 0.34, 0.33]
        
        pos_score = (pos_count + exclamation_count * 0.2) / total
        neg_score = (neg_count + question_count * 0.1) / total
        neu_score = neu_count / total
        
        scores = [neg_score, neu_score, pos_score]
        scores = [s / sum(scores) for s in scores]  # Normalize
        
        label = self.config.SENTIMENT_LABELS[np.argmax(scores)]
        return label, scores
    
    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """Compute softmax"""
        exp_logits = np.exp(logits - np.max(logits))
        return exp_logits / np.sum(exp_logits)
    
    def _save_classifications(self, classified: List[Dict[str, Any]]):
        """Save classifications"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"classifications_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(classified, f, indent=2)
        
        logger.info(f"✅ Classifications saved to {filepath}")
