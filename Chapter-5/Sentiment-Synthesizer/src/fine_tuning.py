"""
Fine-tuning module for adapting BERT to the sentiment classification task
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW

logger = logging.getLogger(__name__)


class _SentimentDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=max_length,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = self.labels[idx]
        return item


class FineTuner:
    """Fine-tunes a pre-trained BERT model on labeled sentiment data"""

    def __init__(self, config):
        self.config = config
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and config.USE_GPU else "cpu"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
        self.label_map = {label: i for i, label in enumerate(config.SENTIMENT_LABELS)}
        logger.info(f"FineTuner ready — device: {self.device}")

    def finetune(self, training_data: List[Dict[str, Any]]):
        """
        Fine-tune the model on labeled examples.

        Args:
            training_data: list of dicts with keys 'text' (str) and 'label'
                           (one of config.SENTIMENT_LABELS)

        Returns:
            The fine-tuned model (also saved to config.MODELS_DIR/sentiment_model)
        """
        texts = [item["text"] for item in training_data]
        labels = [self.label_map[item["label"]] for item in training_data]

        model = AutoModelForSequenceClassification.from_pretrained(
            self.config.MODEL_NAME, num_labels=self.config.NUM_CLASSES
        ).to(self.device)

        dataset = _SentimentDataset(
            texts, labels, self.tokenizer, self.config.MAX_SEQUENCE_LENGTH
        )
        loader = DataLoader(
            dataset, batch_size=self.config.BATCH_SIZE, shuffle=True
        )

        optimizer = AdamW(
            model.parameters(),
            lr=self.config.LEARNING_RATE,
            weight_decay=self.config.WEIGHT_DECAY,
        )
        total_steps = len(loader) * self.config.NUM_EPOCHS
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=total_steps
        )

        logger.info(
            f"Fine-tuning {self.config.MODEL_NAME} for {self.config.NUM_EPOCHS} epochs "
            f"on {len(training_data)} samples..."
        )

        model.train()
        for epoch in range(self.config.NUM_EPOCHS):
            total_loss = 0.0
            for batch in loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = model(**batch)
                outputs.loss.backward()
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                total_loss += outputs.loss.item()
            avg_loss = total_loss / len(loader)
            logger.info(
                f"Epoch {epoch + 1}/{self.config.NUM_EPOCHS} — avg loss: {avg_loss:.4f}"
            )

        save_path: Path = self.config.MODELS_DIR / "sentiment_model"
        model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        logger.info(f"Fine-tuned model saved to {save_path}")
        return model
