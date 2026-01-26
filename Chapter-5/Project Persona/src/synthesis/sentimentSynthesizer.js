import fs from 'fs';
import path from 'path';

/**
 * SentimentSynthesizer - Aggregates and summarizes sentiment trends
 */
export class SentimentSynthesizer {
  constructor() {
    this.outputDir = './output/synthesis';
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Synthesize sentiment data
   */
  synthesizeSentiment(classified) {
    console.log('Synthesizing sentiment trends...');
    
    const synthesis = {
      timestamp: new Date().toISOString(),
      summary: this.generateSummary(classified),
      distribution: this.calculateDistribution(classified),
      trends: this.analyzeTrends(classified),
      topics: this.extractTopics(classified),
      insights: this.generateInsights(classified)
    };

    // Save synthesis results
    this.saveSynthesis(synthesis);
    
    return synthesis;
  }

  /**
   * Generate summary statistics
   */
  generateSummary(classified) {
    const totalSamples = classified.length;
    
    const sentimentCounts = {
      positive: 0,
      neutral: 0,
      negative: 0
    };

    let avgConfidence = 0;
    let avgConfidenceByLabel = {
      positive: [],
      neutral: [],
      negative: []
    };

    classified.forEach(item => {
      const label = item.sentiment.label;
      sentimentCounts[label]++;
      avgConfidence += item.sentiment.confidence;
      avgConfidenceByLabel[label].push(item.sentiment.confidence);
    });

    avgConfidence /= totalSamples;

    // Calculate average confidence per label
    const avgConfPerLabel = {};
    Object.keys(avgConfidenceByLabel).forEach(label => {
      const confidences = avgConfidenceByLabel[label];
      avgConfPerLabel[label] = confidences.length > 0 
        ? (confidences.reduce((a, b) => a + b, 0) / confidences.length).toFixed(3)
        : 0;
    });

    return {
      total_samples: totalSamples,
      timestamp: new Date().toISOString(),
      sentiment_counts: sentimentCounts,
      sentiment_percentages: {
        positive: ((sentimentCounts.positive / totalSamples) * 100).toFixed(2),
        neutral: ((sentimentCounts.neutral / totalSamples) * 100).toFixed(2),
        negative: ((sentimentCounts.negative / totalSamples) * 100).toFixed(2)
      },
      average_confidence: avgConfidence.toFixed(3),
      average_confidence_per_label: avgConfPerLabel,
      overall_sentiment: this.determineOverallSentiment(sentimentCounts)
    };
  }

  /**
   * Calculate sentiment distribution
   */
  calculateDistribution(classified) {
    const distribution = {};
    const sources = new Set(classified.map(item => item.source));

    sources.forEach(source => {
      const sourceItems = classified.filter(item => item.source === source);
      const counts = {
        positive: 0,
        neutral: 0,
        negative: 0
      };

      sourceItems.forEach(item => {
        counts[item.sentiment.label]++;
      });

      distribution[source] = {
        total: sourceItems.length,
        counts,
        percentages: {
          positive: ((counts.positive / sourceItems.length) * 100).toFixed(2),
          neutral: ((counts.neutral / sourceItems.length) * 100).toFixed(2),
          negative: ((counts.negative / sourceItems.length) * 100).toFixed(2)
        }
      };
    });

    return distribution;
  }

  /**
   * Analyze sentiment trends
   */
  analyzeTrends(classified) {
    // Group by time periods if timestamps are available
    const trends = {
      by_source: {},
      temporal: this.analyzeTemporal(classified),
      confidence_trends: this.analyzeConfidenceTrends(classified)
    };

    const sources = new Set(classified.map(item => item.source));
    sources.forEach(source => {
      const sourceItems = classified.filter(item => item.source === source);
      const positive = sourceItems.filter(item => item.sentiment.label === 'positive').length;
      const negative = sourceItems.filter(item => item.sentiment.label === 'negative').length;
      
      trends.by_source[source] = {
        positive_ratio: (positive / sourceItems.length).toFixed(3),
        negative_ratio: (negative / sourceItems.length).toFixed(3),
        trend: positive > negative ? 'improving' : 'declining'
      };
    });

    return trends;
  }

  /**
   * Analyze temporal trends
   */
  analyzeTemporal(classified) {
    // Group by date
    const byDate = {};
    
    classified.forEach(item => {
      const date = item.timestamp ? item.timestamp.split('T')[0] : new Date().toISOString().split('T')[0];
      
      if (!byDate[date]) {
        byDate[date] = { positive: 0, neutral: 0, negative: 0, total: 0 };
      }
      
      byDate[date][item.sentiment.label]++;
      byDate[date].total++;
    });

    return byDate;
  }

  /**
   * Analyze confidence trends
   */
  analyzeConfidenceTrends(classified) {
    const confidences = classified.map(item => item.sentiment.confidence);
    const sorted = [...confidences].sort((a, b) => a - b);
    
    return {
      min: sorted[0].toFixed(3),
      max: sorted[sorted.length - 1].toFixed(3),
      median: sorted[Math.floor(sorted.length / 2)].toFixed(3),
      mean: (confidences.reduce((a, b) => a + b, 0) / confidences.length).toFixed(3),
      std_dev: this.calculateStdDev(confidences).toFixed(3)
    };
  }

  /**
   * Extract top topics/keywords
   */
  extractTopics(classified) {
    const wordFreq = {};
    const stopwords = new Set(['the', 'a', 'is', 'and', 'or', 'to', 'of', 'in', 'this', 'that']);

    classified.forEach(item => {
      const words = item.cleaned_text.split(/\s+/).filter(w => !stopwords.has(w) && w.length > 2);
      words.forEach(word => {
        wordFreq[word] = (wordFreq[word] || 0) + 1;
      });
    });

    // Get top 10 keywords
    const topTopics = Object.entries(wordFreq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([word, count]) => ({ word, count }));

    return topTopics;
  }

  /**
   * Generate actionable insights
   */
  generateInsights(classified) {
    const summary = this.generateSummary(classified);
    const insights = [];

    // Determine if sentiment is positive or negative
    const positivePercent = parseFloat(summary.sentiment_percentages.positive);
    const negativePercent = parseFloat(summary.sentiment_percentages.negative);

    if (positivePercent > 50) {
      insights.push('Overall sentiment is predominantly positive ✅');
    } else if (negativePercent > 50) {
      insights.push('Overall sentiment is predominantly negative ⚠️');
    } else {
      insights.push('Overall sentiment is mixed with no clear trend');
    }

    // Confidence insights
    const avgConf = parseFloat(summary.average_confidence);
    if (avgConf > 0.8) {
      insights.push('High confidence in sentiment predictions (>80%)');
    } else if (avgConf < 0.6) {
      insights.push('Moderate confidence in predictions - consider reviewing');
    }

    // Source-specific insights
    if (summary.sentiment_counts.positive > summary.sentiment_counts.negative * 2) {
      insights.push('Positive sentiment significantly outweighs negative feedback');
    }

    // Topic insight
    const trends = this.analyzeTrends(classified);
    const sources = Object.keys(trends.by_source);
    const decliningSources = sources.filter(s => trends.by_source[s].trend === 'declining');
    
    if (decliningSources.length > 0) {
      insights.push(`Declining sentiment detected in: ${decliningSources.join(', ')}`);
    }

    return insights;
  }

  /**
   * Determine overall sentiment
   */
  determineOverallSentiment(counts) {
    const total = counts.positive + counts.neutral + counts.negative;
    const positiveRatio = counts.positive / total;

    if (positiveRatio > 0.6) return 'POSITIVE';
    if (positiveRatio < 0.3) return 'NEGATIVE';
    return 'NEUTRAL';
  }

  /**
   * Calculate standard deviation
   */
  calculateStdDev(values) {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    return Math.sqrt(variance);
  }

  /**
   * Save synthesis results
   */
  saveSynthesis(synthesis) {
    const filename = `sentiment_synthesis_${Date.now()}.json`;
    const filepath = path.join(this.outputDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(synthesis, null, 2));
    console.log(`✅ Synthesis results saved to ${filepath}`);
  }
}
