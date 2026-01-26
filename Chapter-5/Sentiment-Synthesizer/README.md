# Sentiment Synthesizer - Python Implementation

An advanced NLP system for analyzing and synthesizing user sentiment from social media data using pre-trained Transformer models from Hugging Face.

## 🎯 Project Overview

The Sentiment Synthesizer is a production-ready Python pipeline that:

1. **Collects** social media data from Twitter, Reddit, and other platforms
2. **Preprocesses** text using BERT-style tokenization and cleaning
3. **Generates** contextual embeddings with pre-trained Transformers
4. **Classifies** sentiment (positive, neutral, negative)
5. **Synthesizes** and aggregates sentiment trends
6. **Visualizes** results with interactive dashboards and charts

## 📋 Features

- Data collection from Twitter, Reddit, and mock sources
- BERT-style text preprocessing with Hugging Face tokenizers
- 768-dimensional contextual embeddings
- Fine-tunable sentiment classifier
- Hybrid heuristic + model-based classification
- Temporal trend analysis
- Automated insight generation
- Interactive HTML dashboard
- Multiple visualization types (matplotlib, plotly)
- CSV exports for data analysis
- GPU acceleration support

## 🏗️ Project Structure

```
Sentiment-Synthesizer/
├── main.py                          # Main pipeline entry point
├── config.py                        # Configuration management
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore patterns
│
├── src/
│   ├── data_collection.py          # Twitter, Reddit, mock data collection
│   ├── preprocessing.py            # BERT-style preprocessing
│   ├── embedding_generator.py      # Embedding generation
│   ├── sentiment_classifier.py     # Sentiment classification
│   ├── sentiment_synthesizer.py    # Trend synthesis & analysis
│   ├── visualization.py            # Dashboard & charts
│   ├── fine_tuning.py              # Model fine-tuning (optional)
│   └── utils/
│       └── logger.py               # Logging utility
│
├── data/
│   ├── raw/                        # Raw collected data
│   ├── processed/                  # Preprocessed data
│   └── embeddings/                 # Generated embeddings
│
├── output/
│   ├── visualizations/             # Generated charts & dashboard
│   ├── synthesis/                  # Synthesis results
│   └── classifications/            # Classification results
│
└── notebooks/
    └── exploratory_analysis.ipynb  # Jupyter notebook for exploration
```

## 📦 Installation

### Prerequisites
- Python 3.9+
- pip or conda

### Setup

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (optional):
```bash
cp .env.example .env
# Edit .env with your API keys
```

## 🚀 Quick Start

### Run the complete pipeline:
```bash
python main.py
```

### Expected output:
```
🚀 Starting Sentiment Synthesizer Pipeline...

📊 Step 1: Data Collection
✅ Collected 8 samples

🧹 Step 2: Preprocessing
✅ Cleaned and tokenized 8 samples

🧠 Step 3: Embedding Generation
✅ Generated embeddings with dimension 768

🎯 Step 4: Sentiment Classification
✅ Classified sentiments: 8 samples

📈 Step 5: Sentiment Synthesis
✅ Sentiment synthesis completed

📊 Step 6: Visualization
✅ Visualizations generated

🎉 Pipeline completed successfully!
Results saved to output/ directory
```

## 📊 Output Files

### Generated Artifacts

**Data Files:**
- `data/raw/collected_data_YYYYMMDD_HHMMSS.json` - Raw collected data
- `data/processed/processed_data_YYYYMMDD_HHMMSS.json` - Preprocessed data
- `output/embeddings/embeddings_YYYYMMDD_HHMMSS.json` - Generated embeddings

**Classification Results:**
- `output/classifications/classifications_YYYYMMDD_HHMMSS.json` - Sentiment labels & scores

**Synthesis Results:**
- `output/synthesis/sentiment_synthesis_YYYYMMDD_HHMMSS.json` - Aggregated analysis

**Visualizations:**
- `output/visualizations/dashboard.html` - Interactive dashboard
- `output/visualizations/sentiment_distribution.png` - Pie chart
- `output/visualizations/sentiment_trends.png` - Line chart
- `output/visualizations/source_comparison.png` - Bar chart
- `output/visualizations/top_topics.png` - Horizontal bar chart
- `output/visualizations/sentiment_distribution.csv` - CSV export
- `output/visualizations/classifications.csv` - Classification results CSV

## 🔧 Configuration

### Environment Variables

Create `.env` file with:
```env
# Twitter API (optional)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_secret
TWITTER_BEARER_TOKEN=your_bearer_token

# Reddit API (optional)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=sentiment-synthesizer/1.0
```

### Configuration File

Edit `config.py` to customize:
- Model name and embedding dimensions
- Batch size and training parameters
- Classification thresholds
- Output directories
- GPU usage

## 📚 Step-by-Step Guide

### 1. Data Collection
The system gathers data from:
- Twitter/X API (real-time tweets)
- Reddit API (posts and comments)
- Mock data (for testing without APIs)

**Key Features:**
- Automatic API fallback to mock data
- Timestamp and engagement metrics capture
- Multiple source support

### 2. Preprocessing
Text cleaning and normalization:
- Remove URLs and mentions
- Convert to lowercase
- Tokenization using BERT tokenizer
- Sequence padding to max length

**Output:** Tokenized sequences ready for embedding

### 3. Embedding Generation
Contextual embeddings using pre-trained BERT:
- 768-dimensional vectors
- [CLS] token pooling strategy
- GPU-accelerated generation

**Output:** Embedding vectors with metadata

### 4. Sentiment Classification
Multi-class sentiment classification:
- Hybrid approach (60% model, 40% heuristic)
- Three labels: negative, neutral, positive
- Confidence scores (softmax probabilities)
- Fine-tuning ready

**Output:** Sentiment labels with confidence scores

### 5. Sentiment Synthesis
Aggregate and analyze sentiment:
- Distribution by sentiment and source
- Temporal trend analysis
- Top keyword extraction
- Statistical summaries
- Actionable insights

### 6. Visualization
Create interactive dashboards and charts:
- HTML dashboard with metrics
- Matplotlib/Seaborn charts (PNG)
- CSV exports for analysis
- Multiple visualization types

## 🔍 Understanding the Output

### Sentiment Distribution
- **Positive**: Favorable opinions and emotions
- **Neutral**: Factual statements without clear emotion
- **Negative**: Unfavorable opinions and complaints

### Confidence Scores
- 0.8-1.0: High confidence
- 0.6-0.8: Moderate confidence
- <0.6: Low confidence (review recommended)

### Key Insights
Automatically generated observations about:
- Overall sentiment tendency
- Confidence levels
- Source-specific trends
- Declining/improving indicators
- Notable patterns

## 🤖 Advanced Usage

### Fine-tuning the Model

```python
from src.fine_tuning import FineTuner
from config import Config

config = Config()
finetuner = FineTuner(config)

# Prepare training data
training_data = [
    {"text": "Great product!", "label": "positive"},
    {"text": "Terrible experience", "label": "negative"},
    # ...
]

# Fine-tune
finetuner.finetune(training_data)
```

### Using Different Models

```python
config = Config()
config.MODEL_NAME = "distilbert-base-uncased"  # Faster
config.MODEL_NAME = "roberta-base"              # Better performance
config.MODEL_NAME = "albert-base-v2"            # Lighter weight
```

### GPU Acceleration

```python
config = Config()
config.USE_GPU = True  # Automatic CUDA detection
```

## 📊 Analysis Examples

### Analyzing Results

```python
import json
from pathlib import Path

# Load synthesis results
result_file = Path("output/synthesis/sentiment_synthesis_*.json")
with open(result_file) as f:
    synthesis = json.load(f)

# Access key metrics
print(f"Total samples: {synthesis['summary']['total_samples']}")
print(f"Overall sentiment: {synthesis['summary']['overall_sentiment']}")
print(f"Avg confidence: {synthesis['summary']['average_confidence']}")
print(f"Insights: {synthesis['insights']}")
```

### Custom Analysis

```python
import pandas as pd

# Load classifications
df = pd.read_csv("output/visualizations/classifications.csv")

# Analyze by source
print(df.groupby('source')['sentiment'].value_counts())

# Filter high confidence predictions
high_conf = df[df['confidence'] > 0.8]
print(f"High confidence predictions: {len(high_conf)}")
```

## 🧪 Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 🛠️ Troubleshooting

### Memory Issues
```bash
# Process in smaller batches
# Edit config.py:
config.BATCH_SIZE = 8  # Reduce from 16
```

### GPU Not Detected
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU usage
# Edit config.py:
config.USE_GPU = False
```

### Missing Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### API Connection Issues
- System automatically falls back to mock data
- Check API credentials in .env
- Verify rate limits and quotas

## 📈 Performance Characteristics

**Processing Speed:**
- Data collection: 0.5-2s (API dependent)
- Preprocessing: 0.1-0.5s (per sample)
- Embedding generation: 0.05-0.2s (per sample with GPU)
- Classification: 0.02-0.1s (per sample)
- Total pipeline: ~5-10s for 8 samples

**Model Sizes:**
- BERT-base: ~340MB
- DistilBERT: ~260MB (faster, smaller)

## 📚 Learning Outcomes

By working with this project, you'll learn:

- ✅ BERT architecture and contextual embeddings
- ✅ Transformer fine-tuning for downstream tasks
- ✅ NLP pipeline design and orchestration
- ✅ Sentiment analysis techniques
- ✅ Data visualization best practices
- ✅ Python best practices for ML projects

## 🔗 References

- [Hugging Face Transformers](https://huggingface.co/transformers/)
- [BERT Paper](https://arxiv.org/abs/1810.04805)
- [Sentiment Analysis Tutorial](https://huggingface.co/docs/transformers/tasks/sequence_classification)
- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)

## 📝 License

MIT License

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Happy sentiment analyzing! 🚀**
