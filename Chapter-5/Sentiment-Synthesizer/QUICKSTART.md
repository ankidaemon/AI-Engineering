# Sentiment Synthesizer - Quick Start Guide

Get up and running with the Sentiment Synthesizer in **5 minutes**! 🚀

## 1️⃣ Installation (2 minutes)

### Step 1: Clone and navigate
```bash
cd /Users/ankitm/Documents/git/AI-Engineering/Chapter-5/Sentiment-Synthesizer
```

### Step 2: Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

✅ **Done!** Dependencies installed.

## 2️⃣ First Run (2 minutes)

### Run the complete pipeline:
```bash
python main.py
```

### What happens:
1. 📥 **Collects** social media data (or uses mock data)
2. 🧹 **Preprocesses** text with BERT tokenizer
3. 🧠 **Generates** embeddings
4. 🎯 **Classifies** sentiment
5. 📈 **Synthesizes** trends and insights
6. 📊 **Creates** visualizations

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

## 3️⃣ Check Results (1 minute)

### View generated files:
```bash
ls -la output/
```

### You'll see:
- 📊 `visualizations/` - Charts and HTML dashboard
- 📈 `synthesis/` - Sentiment analysis results
- 📁 `classifications/` - Classification results

### Open the dashboard:
```bash
# On Mac
open output/visualizations/dashboard.html

# Or open manually in your browser
```

## 4️⃣ Optional: Configure APIs

To use real data from Twitter/Reddit instead of mock data:

### Step 1: Get API credentials
- **Twitter**: [developer.twitter.com](https://developer.twitter.com)
- **Reddit**: [reddit.com/prefs/apps](https://reddit.com/prefs/apps)

### Step 2: Create .env file
```bash
cp .env.example .env
```

### Step 3: Add your credentials
```env
TWITTER_BEARER_TOKEN=your_token_here
REDDIT_CLIENT_ID=your_id_here
REDDIT_CLIENT_SECRET=your_secret_here
```

### Step 4: Run with real data
```bash
python main.py
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `main.py` | Main pipeline executor |
| `config.py` | Configuration settings |
| `src/data_collection.py` | Data gathering |
| `src/preprocessing.py` | Text cleaning |
| `src/embedding_generator.py` | Embedding creation |
| `src/sentiment_classifier.py` | Classification |
| `src/sentiment_synthesizer.py` | Analysis |
| `src/visualization.py` | Charts & dashboard |

## 🎯 What You Get

### After running main.py:

```
output/
├── classifications/
│   └── classifications_*.json          # Sentiment labels
├── synthesis/
│   └── sentiment_synthesis_*.json      # Analysis results
└── visualizations/
    ├── dashboard.html                  # Interactive dashboard
    ├── sentiment_distribution.png      # Pie chart
    ├── sentiment_trends.png            # Line chart
    ├── source_comparison.png           # Bar chart
    ├── top_topics.png                  # Topics chart
    ├── classifications.csv             # Results as CSV
    └── sentiment_distribution.csv      # Distribution as CSV
```

## 📊 Understanding the Results

### Sentiment Distribution
- **Positive** ✅ - Happy, satisfied, favorable
- **Neutral** ➖ - Objective, factual, no emotion
- **Negative** ❌ - Unhappy, frustrated, unfavorable

### Confidence Score
- **0.9-1.0**: Very confident
- **0.7-0.9**: Confident
- **0.5-0.7**: Somewhat confident
- **<0.5**: Low confidence

### Key Insights
Automatically generated observations like:
- "Overall sentiment is 62.5% positive"
- "High confidence in most predictions"
- "Twitter shows higher positivity"

## 🔧 Customization Tips

### Use different model
Edit `config.py`:
```python
config.MODEL_NAME = "distilbert-base-uncased"  # Faster
config.MODEL_NAME = "roberta-base"              # Better quality
```

### Adjust batch size
```python
config.BATCH_SIZE = 8  # Smaller for low memory
config.BATCH_SIZE = 32 # Larger for faster processing
```

### Change sentiment labels
```python
config.SENTIMENT_LABELS = ["neg", "neut", "pos"]
config.NUM_CLASSES = 3
```

## 🐛 Troubleshooting

### "No module named 'torch'"
```bash
pip install --upgrade -r requirements.txt
```

### "CUDA out of memory"
Edit `config.py`:
```python
config.BATCH_SIZE = 8
config.USE_GPU = False  # Use CPU instead
```

### "API connection failed"
System automatically uses mock data. Check your internet connection or API credentials.

### "No output files generated"
Ensure `output/` directory exists:
```bash
mkdir -p output/{visualizations,synthesis,classifications}
```

## 📚 Next Steps

1. **Explore the code**: Review the modules in `src/`
2. **Try Jupyter**: Run `examples/exploratory_analysis.ipynb` (if available)
3. **Customize**: Modify `config.py` for your use case
4. **Fine-tune**: Train on custom data using `src/fine_tuning.py`
5. **Deploy**: Package as a service or API

## 💡 Pro Tips

✅ **Tip 1**: First run uses mock data - perfect for testing without APIs

✅ **Tip 2**: GPU acceleration is automatic - install CUDA for faster processing

✅ **Tip 3**: Results are saved with timestamps - easy to track iterations

✅ **Tip 4**: Edit `config.py` before running for custom settings

✅ **Tip 5**: Check `data/raw/` to see collected data

## 📖 Full Documentation

For detailed information, see:
- [README.md](./README.md) - Full documentation
- [API-INTEGRATION.md](./API-INTEGRATION.md) - Real API setup

## 🎉 You're All Set!

```bash
# Run anytime with:
python main.py

# Or check out the results:
open output/visualizations/dashboard.html
```

**Happy analyzing! 🚀**
