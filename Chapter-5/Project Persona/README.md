# Sentiment Synthesizer - Node.js Implementation

An advanced NLP system that analyzes and synthesizes user sentiment from social media data using Transformer-based models. This project demonstrates a complete end-to-end pipeline for sentiment analysis with Node.js.

## 🎯 Project Overview

The Sentiment Synthesizer project focuses on building a production-ready NLP system that:

1. **Collects** social media data from Twitter, Reddit, and other platforms
2. **Preprocesses** text using BERT-style tokenization
3. **Generates** contextual embeddings with Transformer models
4. **Classifies** sentiment (positive, neutral, negative)
5. **Synthesizes** and aggregates sentiment trends
6. **Visualizes** results with interactive dashboards and charts

## 📋 Features

- **Data Collection**: Scrape or integrate with Twitter/X, Reddit APIs
- **Text Preprocessing**: BERT-style tokenization, cleaning, and normalization
- **Embedding Generation**: Contextual embeddings using pre-trained Transformers
- **Sentiment Classification**: Fine-tunable BERT-based sentiment classifier
- **Trend Analysis**: Temporal sentiment trends and source-based comparisons
- **Visualization**: Interactive HTML dashboard, CSV exports, ASCII charts
- **Scalable Pipeline**: Modular architecture for easy extension

## 🏗️ Project Structure

```
Project Persona/
├── src/
│   ├── index.js                           # Main pipeline orchestrator
│   ├── dataCollection/
│   │   └── dataCollector.js              # Data collection from APIs
│   ├── preprocessing/
│   │   └── preprocessor.js               # Text cleaning & tokenization
│   ├── embedding/
│   │   └── embeddingGenerator.js         # Embedding generation
│   ├── classification/
│   │   └── sentimentClassifier.js        # Sentiment classification
│   ├── synthesis/
│   │   └── sentimentSynthesizer.js       # Trend synthesis & aggregation
│   └── visualization/
│       └── visualizer.js                 # Dashboard & chart generation
├── data/
│   ├── raw/                              # Raw collected data
│   ├── processed/                        # Preprocessed data
│   ├── embeddings/                       # Generated embeddings
│   └── classifications/                  # Classification results
├── output/
│   ├── synthesis/                        # Synthesis results
│   └── visualizations/                   # Generated charts & dashboards
├── package.json                          # Node.js dependencies
├── .env.example                          # Environment variables template
└── README.md                             # This file
```

## 📦 Installation

### Prerequisites

- Node.js 16.0+
- npm or yarn

### Setup

1. **Clone the repository** (or navigate to the project directory):
```bash
cd "Project Persona"
```

2. **Install dependencies**:
```bash
npm install
```

3. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env and add your API keys
nano .env
```

## 🚀 Quick Start

### Run the Complete Pipeline

```bash
npm run pipeline
```

This executes all steps in sequence:
1. Data Collection
2. Preprocessing
3. Embedding Generation
4. Sentiment Classification
5. Sentiment Synthesis
6. Visualization

### Run Individual Steps

```bash
# Collect data from social media
npm run collect-data

# Preprocess collected data
npm run preprocess

# Generate embeddings
npm run generate-embeddings

# Classify sentiments
npm run classify-sentiment

# Synthesize sentiment trends
npm run synthesize

# Generate visualizations
npm run visualize
```

### Development Mode

Watch for changes and auto-reload:
```bash
npm run dev
```

## 📊 Step-by-Step Guide

### 1. Data Collection
The system collects data from multiple sources:
- **Twitter/X API**: Real-time tweets with metrics
- **Reddit API**: Posts and comments from relevant subreddits
- **Mock Data**: Sample data for testing without API keys

**Key Features**:
- Configurable data sources
- Automatic API fallback to mock data
- Timestamp preservation
- Engagement metrics capture

### 2. Preprocessing
Clean and normalize text data:
- Remove URLs and mentions
- Convert to lowercase
- Tokenization (word-level and subword)
- Feature extraction (exclamation marks, caps, punctuation)

**Output**: Cleaned text, tokens, and linguistic features

### 3. Embedding Generation
Generate contextual embeddings:
- BERT-style embedding dimension: 768
- Mean pooling strategy
- Cosine similarity computation
- Embedding normalization

**Features**:
- Pre-trained model integration points
- Efficient embedding storage
- Similarity search capabilities

### 4. Sentiment Classification
Classify text sentiment:
- **Labels**: Positive, Neutral, Negative
- **Approach**: Hybrid heuristic + embedding-based
- **Confidence scores**: Per-label probabilities
- **Fine-tuning**: Ready for custom model training

**Classification Method**:
- Keyword-based heuristics (50%)
- Embedding-based scoring (50%)
- Softmax normalization

### 5. Sentiment Synthesis
Aggregate and analyze trends:
- Overall sentiment distribution
- Source-specific breakdowns
- Temporal trend analysis
- Topic extraction (top keywords)
- Actionable insights generation

### 6. Visualization
Generate interactive dashboards:
- HTML dashboard with metrics
- CSV exports for data analysis
- ASCII console charts
- Source comparisons
- Topic frequency analysis

## 📈 Output Formats

### Generated Files

**Raw Data** (`data/raw/`):
```json
{
  "id": "tw_001",
  "source": "twitter",
  "text": "I love this product!",
  "timestamp": "2024-01-26T10:00:00Z",
  "author": "user123"
}
```

**Processed Data** (`data/processed/`):
```json
{
  "cleaned_text": "i love this product",
  "tokens": ["i", "love", "this", "product"],
  "word_count": 4
}
```

**Embeddings** (`data/embeddings/`):
```json
{
  "embedding": [0.123, -0.456, ...],
  "embedding_metadata": {
    "dimension": 768,
    "model": "bert-base-uncased"
  }
}
```

**Classifications** (`data/classifications/`):
```json
{
  "sentiment": {
    "label": "positive",
    "confidence": 0.92,
    "scores": [0.03, 0.05, 0.92]
  }
}
```

**Synthesis Results** (`output/synthesis/`):
```json
{
  "summary": {
    "total_samples": 8,
    "sentiment_counts": {
      "positive": 4,
      "neutral": 2,
      "negative": 2
    }
  },
  "trends": {...},
  "insights": [...]
}
```

### Visualizations

- **dashboard.html**: Interactive web-based dashboard
- **sentiment_distribution.csv**: Sentiment breakdown
- **sentiment_trends.csv**: Temporal trends
- **source_comparison.csv**: Source-based analysis
- **top_topics.csv**: Keyword frequency

## 🔧 Configuration

### Environment Variables

```env
# API Keys
TWITTER_API_KEY=xxx
REDDIT_CLIENT_ID=xxx

# Model Settings
TRANSFORMER_MODEL=bert-base-uncased
EMBEDDING_DIMENSION=768
MAX_SEQUENCE_LENGTH=128

# Processing
BATCH_SIZE=32
CONFIDENCE_THRESHOLD=0.6
```

### Adjusting Parameters

Edit directly in each module:

**Data Collection** (`src/dataCollection/dataCollector.js`):
```javascript
const mockData = this.getMockData(); // Add real API calls here
```

**Preprocessing** (`src/preprocessing/preprocessor.js`):
```javascript
const maxLength = 128; // Adjust sequence length
```

**Classification** (`src/classification/sentimentClassifier.js`):
```javascript
this.confidenceThreshold = 0.6; // Adjust threshold
```

## 🤖 Using Different Models

### With Local ONNX Runtime

```javascript
import { InferenceSession } from 'onnxruntime-node';

// Load BERT model
const session = await InferenceSession.create('bert-model.onnx');
```

### With Hugging Face API

```bash
npm install @huggingface/inference
```

```javascript
import { HfInference } from "@huggingface/inference";
const client = new HfInference(process.env.HF_TOKEN);
```

## 📊 Analyzing Results

### View the Dashboard

```bash
# Open the generated HTML dashboard
open output/visualizations/dashboard.html
```

### Analyze CSV Data

```bash
# View sentiment distribution
cat output/visualizations/sentiment_distribution.csv

# View trends
cat output/visualizations/sentiment_trends.csv
```

### Check Console Output

The pipeline prints:
- Real-time processing status
- Sample counts at each stage
- Sentiment distribution percentages
- Top topics identified
- Key insights

## 🔍 Understanding Outputs

### Sentiment Distribution
- **Positive**: Favorable opinions and emotions
- **Neutral**: Factual statements without emotion
- **Negative**: Unfavorable opinions and complaints

### Confidence Scores
- Higher values (0.8-1.0): High confidence in prediction
- Medium values (0.6-0.8): Moderate confidence
- Lower values (<0.6): Uncertain classification

### Key Insights
Automatically generated observations:
- Overall sentiment tendency
- Confidence level assessment
- Source-specific trends
- Declining/improving indicators

## 🛠️ Extending the Project

### Add New Data Sources

```javascript
// src/dataCollection/dataCollector.js
async getNewSourceData() {
  // Implement your data collection logic
  return formattedData;
}
```

### Implement Fine-tuning

```javascript
// src/classification/sentimentClassifier.js
finetuneModel(trainingData, epochs = 3) {
  // Implement actual fine-tuning
}
```

### Add Custom Visualizations

```javascript
// src/visualization/visualizer.js
generateCustomChart(data) {
  // Create new visualization type
}
```

## 📚 Learning Outcomes

By working with this project, you'll understand:

- ✅ **Transformer Architecture**: BERT and contextual embeddings
- ✅ **NLP Pipelines**: End-to-end text analysis workflows
- ✅ **Fine-tuning**: Adapting models to custom tasks
- ✅ **Sentiment Analysis**: Classification approaches and evaluation
- ✅ **Data Visualization**: Creating actionable dashboards
- ✅ **Production NLP**: Scalable, modular architecture

## 📖 Additional Resources

- [Hugging Face Transformers Documentation](https://huggingface.co/transformers/)
- [BERT: Pre-training of Deep Bidirectional Transformers](https://arxiv.org/abs/1810.04805)
- [Attention is All You Need](https://arxiv.org/abs/1706.03762)
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)

## 🚨 Troubleshooting

### API Key Issues
- Ensure `.env` file is properly configured
- Check API quotas and rate limits
- Use mock data for development

### Out of Memory
- Reduce `BATCH_SIZE` in .env
- Process data in smaller chunks
- Increase Node.js heap size: `node --max-old-space-size=4096 src/index.js`

### Missing Dependencies
```bash
npm install
npm list  # Verify all packages installed
```

## 📄 License

MIT License - see LICENSE file for details

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit changes with clear messages
4. Submit a pull request

## 📧 Support

For issues and questions, please open a GitHub issue or contact the project maintainers.

---

**Happy Sentiment Synthesizing! 🎉**
