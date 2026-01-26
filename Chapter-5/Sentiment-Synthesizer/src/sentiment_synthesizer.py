"""
Sentiment synthesis module
Aggregates and analyzes sentiment trends
"""

import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


class SentimentSynthesizer:
    """Synthesizes sentiment data and generates insights"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.OUTPUT_DIR / "synthesis"
    
    def synthesize_sentiment(self, classified: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate sentiment synthesis and insights"""
        logger.info("Synthesizing sentiment data...")
        
        synthesis = {
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(classified),
            'distribution': self._calculate_distribution(classified),
            'trends': self._analyze_trends(classified),
            'topics': self._extract_topics(classified),
            'insights': self._generate_insights(classified)
        }
        
        # Save synthesis
        self._save_synthesis(synthesis)
        return synthesis
    
    def _generate_summary(self, classified: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total = len(classified)
        
        sentiments = [item['sentiment']['label'] for item in classified]
        sentiment_counts = Counter(sentiments)
        confidences = [item['sentiment']['confidence'] for item in classified]
        
        return {
            'total_samples': total,
            'timestamp': datetime.now().isoformat(),
            'sentiment_counts': dict(sentiment_counts),
            'sentiment_percentages': {
                label: round((count / total) * 100, 2)
                for label, count in sentiment_counts.items()
            },
            'average_confidence': round(np.mean(confidences), 3),
            'confidence_stats': {
                'min': round(float(np.min(confidences)), 3),
                'max': round(float(np.max(confidences)), 3),
                'mean': round(float(np.mean(confidences)), 3),
                'std': round(float(np.std(confidences)), 3)
            },
            'overall_sentiment': self._determine_overall_sentiment(sentiment_counts, total)
        }
    
    def _calculate_distribution(self, classified: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate distribution by source"""
        distribution = {}
        sources = set(item['source'] for item in classified)
        
        for source in sources:
            source_items = [item for item in classified if item['source'] == source]
            sentiments = [item['sentiment']['label'] for item in source_items]
            sentiment_counts = Counter(sentiments)
            
            distribution[source] = {
                'total': len(source_items),
                'counts': dict(sentiment_counts),
                'percentages': {
                    label: round((count / len(source_items)) * 100, 2)
                    for label, count in sentiment_counts.items()
                }
            }
        
        return distribution
    
    def _analyze_trends(self, classified: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment trends"""
        # Group by date
        by_date = {}
        for item in classified:
            date = item['timestamp'][:10] if item['timestamp'] else datetime.now().isoformat()[:10]
            
            if date not in by_date:
                by_date[date] = {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}
            
            sentiment = item['sentiment']['label']
            by_date[date][sentiment] += 1
            by_date[date]['total'] += 1
        
        # By source
        by_source = {}
        sources = set(item['source'] for item in classified)
        for source in sources:
            source_items = [item for item in classified if item['source'] == source]
            positives = sum(1 for item in source_items if item['sentiment']['label'] == 'positive')
            negatives = sum(1 for item in source_items if item['sentiment']['label'] == 'negative')
            
            by_source[source] = {
                'positive_ratio': round(positives / len(source_items), 3),
                'negative_ratio': round(negatives / len(source_items), 3),
                'trend': 'improving' if positives > negatives else 'declining'
            }
        
        return {
            'by_date': by_date,
            'by_source': by_source
        }
    
    def _extract_topics(self, classified: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract top topics/keywords"""
        stop_words = {'the', 'a', 'is', 'and', 'or', 'to', 'of', 'in', 'this', 'that', 'it'}
        
        word_freq = Counter()
        for item in classified:
            words = item['text'].lower().split()
            for word in words:
                word = word.strip('.,!?;:')
                if word not in stop_words and len(word) > 2:
                    word_freq[word] += 1
        
        top_topics = [
            {'word': word, 'count': count}
            for word, count in word_freq.most_common(10)
        ]
        
        return top_topics
    
    def _generate_insights(self, classified: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable insights"""
        insights = []
        summary = self._generate_summary(classified)
        
        # Overall sentiment
        positive_pct = summary['sentiment_percentages'].get('positive', 0)
        negative_pct = summary['sentiment_percentages'].get('negative', 0)
        
        if positive_pct > 50:
            insights.append('Overall sentiment is predominantly positive ✅')
        elif negative_pct > 50:
            insights.append('Overall sentiment is predominantly negative ⚠️')
        else:
            insights.append('Overall sentiment is mixed with no clear trend')
        
        # Confidence
        avg_conf = summary['average_confidence']
        if avg_conf > 0.8:
            insights.append('High confidence in sentiment predictions (>80%)')
        elif avg_conf < 0.6:
            insights.append('Moderate confidence in predictions - consider reviewing')
        
        # Magnitude
        if positive_pct > negative_pct * 2:
            insights.append('Positive sentiment significantly outweighs negative feedback')
        
        # Source specific
        trends = self._analyze_trends(classified)
        declining = [s for s, t in trends['by_source'].items() if t['trend'] == 'declining']
        if declining:
            insights.append(f"Declining sentiment detected in: {', '.join(declining)}")
        
        return insights
    
    def _determine_overall_sentiment(self, sentiment_counts: Counter, total: int) -> str:
        """Determine overall sentiment"""
        positive = sentiment_counts.get('positive', 0)
        positive_ratio = positive / total if total > 0 else 0
        
        if positive_ratio > 0.6:
            return 'POSITIVE'
        elif positive_ratio < 0.3:
            return 'NEGATIVE'
        return 'NEUTRAL'
    
    def _save_synthesis(self, synthesis: Dict[str, Any]):
        """Save synthesis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"sentiment_synthesis_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(synthesis, f, indent=2)
        
        logger.info(f"✅ Synthesis saved to {filepath}")
