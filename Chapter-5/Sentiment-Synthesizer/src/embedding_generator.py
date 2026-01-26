"""
Embedding generation module
Generates contextual embeddings using pre-trained Transformers
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm

import torch
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates contextual embeddings using Transformers"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.OUTPUT_DIR / "embeddings"
        self.device = torch.device("cuda" if torch.cuda.is_available() and config.USE_GPU else "cpu")
        
        logger.info(f"Loading model: {config.MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        self.model = AutoModel.from_pretrained(config.MODEL_NAME).to(self.device)
        self.model.eval()
        
        logger.info(f"Using device: {self.device}")
    
    def generate_embeddings(self, processed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for processed data"""
        logger.info("Generating embeddings...")
        
        embeddings = []
        
        with torch.no_grad():
            for item in tqdm(processed_data, desc="Generating embeddings"):
                # Get tokens
                tokens = item['tokens']
                
                # Convert to tensor
                input_ids = torch.tensor([tokens]).to(self.device)
                
                # Generate embedding
                outputs = self.model(input_ids)
                
                # Use [CLS] token embedding or mean pooling
                cls_embedding = outputs.last_hidden_state[0, 0, :].cpu().numpy()
                
                embeddings.append({
                    'id': item['id'],
                    'source': item['source'],
                    'text': item['original_text'],
                    'cleaned_text': item['cleaned_text'],
                    'embedding': cls_embedding.tolist(),
                    'embedding_metadata': {
                        'dimension': self.config.EMBEDDING_DIM,
                        'model': self.config.MODEL_NAME,
                        'pooling': 'cls_token'
                    },
                    'timestamp': item['timestamp'],
                    'metrics': item['metrics']
                })
        
        # Save embeddings
        self._save_embeddings(embeddings)
        return embeddings
    
    def _save_embeddings(self, embeddings: List[Dict[str, Any]]):
        """Save embeddings to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"embeddings_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(embeddings, f, indent=2)
        
        logger.info(f"✅ Embeddings saved to {filepath}")
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        embedding1 = np.array(embedding1) if not isinstance(embedding1, np.ndarray) else embedding1
        embedding2 = np.array(embedding2) if not isinstance(embedding2, np.ndarray) else embedding2
        
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
