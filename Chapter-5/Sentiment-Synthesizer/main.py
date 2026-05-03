"""
Main entry point for the Sentiment Synthesizer pipeline
Orchestrates all steps: collection, preprocessing, embedding, classification, synthesis, visualization
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from src.data_collection import DataCollector
from src.preprocessing import Preprocessor
from src.embedding_generator import EmbeddingGenerator
from src.sentiment_classifier import SentimentClassifier
from src.sentiment_synthesizer import SentimentSynthesizer
from src.visualization import Visualizer
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)


class SentimentSynthesizerPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Config = None):
        """Initialize pipeline with configuration"""
        self.config = config or Config()
        logger.info("Initializing Sentiment Synthesizer Pipeline...")
        
    def run(self) -> dict:
        """Execute complete pipeline"""
        try:
            logger.info("🚀 Starting Sentiment Synthesizer Pipeline...\n")
            
            # Step 1: Data Collection
            logger.info("📊 Step 1: Data Collection")
            collector = DataCollector(self.config)
            raw_data = collector.collect_data()
            logger.info(f"✅ Collected {len(raw_data)} samples\n")
            
            # Step 2: Preprocessing
            logger.info("🧹 Step 2: Preprocessing")
            preprocessor = Preprocessor(self.config)
            processed_data = preprocessor.preprocess(raw_data)
            logger.info(f"✅ Cleaned and tokenized {len(processed_data)} samples\n")
            
            # Step 3: Embedding Generation
            logger.info("🧠 Step 3: Embedding Generation")
            embedder = EmbeddingGenerator(self.config)
            embeddings = embedder.generate_embeddings(processed_data)
            logger.info(f"✅ Generated embeddings with dimension {len(embeddings[0]['embedding'])}\n")
            
            # Step 4: Sentiment Classification
            logger.info("🎯 Step 4: Sentiment Classification")
            classifier = SentimentClassifier(self.config)
            classified = classifier.classify_sentiment(embeddings)
            logger.info(f"✅ Classified sentiments: {len(classified)} samples\n")
            
            # Step 5: Sentiment Synthesis
            logger.info("📈 Step 5: Sentiment Synthesis")
            synthesizer = SentimentSynthesizer(self.config)
            synthesis = synthesizer.synthesize_sentiment(classified)
            logger.info("✅ Sentiment synthesis completed\n")
            
            # Step 6: Visualization
            logger.info("📊 Step 6: Visualization")
            visualizer = Visualizer(self.config)
            visualizer.generate_visualizations(synthesis, classified)
            logger.info("✅ Visualizations generated\n")
            
            logger.info("🎉 Pipeline completed successfully!")
            logger.info("Results saved to output/ directory")
            
            return {
                'raw_data': raw_data,
                'processed_data': processed_data,
                'embeddings': embeddings,
                'classified': classified,
                'synthesis': synthesis
            }
            
        except Exception as e:
            logger.error(f"❌ Error in pipeline: {str(e)}", exc_info=True)
            raise


def main():
    """Main entry point"""
    pipeline = SentimentSynthesizerPipeline()
    results = pipeline.run()
    return results


if __name__ == "__main__":
    main()
