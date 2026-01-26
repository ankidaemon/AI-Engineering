# 🎯 Sentiment Synthesizer - Getting Started

Welcome to the Sentiment Synthesizer! This Node.js project implements a complete NLP pipeline for sentiment analysis.

## ⚡ 30-Second Start

```bash
cd "Project Persona"
npm install
npm start
```

That's it! The pipeline will run automatically with sample data.

---

## 📖 Documentation Guide

### Start Here (Pick One)

**For Fastest Start** (2 minutes)
→ Read this file (you are here!)
→ Then run: `npm install && npm start`

**For 5-Minute Tutorial** (5 minutes)
→ Open: `QUICKSTART.md`
→ Follow the examples
→ Try the commands

**For Complete Guide** (15 minutes)
→ Open: `README.md`
→ Learn all features
→ Understand the architecture

**For Real APIs** (10 minutes)
→ Open: `API-INTEGRATION.md`
→ Get Twitter/Reddit keys
→ Configure and connect

**For File Reference** (5 minutes)
→ Open: `FILE_INVENTORY.md`
→ Find what you need
→ See how it connects

---

## 🚀 What Happens When You Run It

```bash
npm start
```

### Step 1: Data Collection (📊)
Collects sample tweets and Reddit posts about sentiment analysis.
```
✅ Collected 8 samples
```

### Step 2: Preprocessing (🧹)
Cleans text, removes URLs, tokenizes into words.
```
✅ Cleaned and tokenized 8 samples
```

### Step 3: Embeddings (🧠)
Converts each text to a 768-dimensional vector using BERT-style embeddings.
```
✅ Generated embeddings with dimension 768
```

### Step 4: Classification (🎯)
Labels each text as positive, neutral, or negative with confidence scores.
```
✅ Classified sentiments: 8 samples
```

### Step 5: Synthesis (📈)
Analyzes trends, extracts insights, generates summary statistics.
```
✅ Sentiment synthesis completed
```

### Step 6: Visualization (📊)
Creates an interactive dashboard and exports data as CSV.
```
✅ Visualizations generated
```

---

## 📁 Output Files

After running, you'll find:

**Raw Data**
```
data/raw/collected_data_[timestamp].json
```
Contains original tweets and posts.

**Processed Data**
```
data/processed/processed_data_[timestamp].json
```
Contains cleaned text and tokens.

**Embeddings**
```
data/embeddings/embeddings_[timestamp].json
```
Contains 768-dimensional vectors.

**Classifications**
```
data/classifications/classifications_[timestamp].json
```
Contains sentiment labels and confidence scores.

**Synthesis Results**
```
output/synthesis/sentiment_synthesis_[timestamp].json
```
Contains aggregated analysis and insights.

**Dashboard** (Most Important!)
```
output/visualizations/dashboard.html
```
Beautiful interactive dashboard - open in browser!

**CSV Charts**
```
output/visualizations/sentiment_distribution.csv
output/visualizations/sentiment_trends.csv
output/visualizations/source_comparison.csv
output/visualizations/top_topics.csv
```

---

## 🎨 View the Dashboard

```bash
# macOS
open output/visualizations/dashboard.html

# Linux
xdg-open output/visualizations/dashboard.html

# Windows
start output/visualizations/dashboard.html

# Or just open the file in your browser
```

You'll see:
- ✅ **Sentiment breakdown**: Positive, Neutral, Negative percentages
- 📱 **Source analysis**: How each source (Twitter, Reddit) compared
- 🏷️ **Top topics**: Most mentioned keywords
- 💡 **Key insights**: Automatically generated findings
- 📊 **Confidence metrics**: How sure the model was

---

## 🔧 Individual Commands

Run only specific parts:

```bash
# Just collect data
npm run collect-data

# Just preprocess
npm run preprocess

# Just generate embeddings
npm run generate-embeddings

# Just classify
npm run classify-sentiment

# Just synthesize
npm run synthesize

# Just visualize
npm run visualize

# Full pipeline (all steps)
npm run pipeline
```

---

## 🧪 Verify Everything Works

```bash
node test.js
```

Should see:
```
✅ PASSED: Data collection returns array with samples
✅ PASSED: Preprocessing produces tokenized output
✅ PASSED: Embeddings generated with correct dimension (768)
✅ PASSED: Classification produces valid labels and scores
✅ PASSED: Synthesis produces valid summary and insights
✅ PASSED: Visualizations generated successfully
✅ PASSED: Cosine similarity calculation correct
✅ PASSED: Distribution calculation is accurate

✅ Passed: 8
❌ Failed: 0
```

---

## 🎓 Understanding the Concepts

### What is Sentiment Analysis?
Determining if text expresses positive, negative, or neutral emotion.

**Example:**
- "I love this!" → **Positive** (98% confidence)
- "This is okay" → **Neutral** (85% confidence)
- "I hate this" → **Negative** (95% confidence)

### What are BERT Embeddings?
Transforming text into mathematical vectors that capture meaning.

**Why?** Machine learning algorithms understand numbers, not words.

### What is the Pipeline?
Sequential steps:
1. Get raw text data
2. Clean it
3. Convert to numbers (embeddings)
4. Classify the sentiment
5. Analyze patterns
6. Visualize results

---

## 🔑 Key Files Explained

### Main Entry Point
**`src/index.js`** - Orchestrates the entire pipeline. This is what runs when you do `npm start`.

### Core Modules
- **`dataCollection/dataCollector.js`** - Gets data from social media (or mock data)
- **`preprocessing/preprocessor.js`** - Cleans and tokenizes text
- **`embedding/embeddingGenerator.js`** - Converts text to vectors
- **`classification/sentimentClassifier.js`** - Labels sentiments
- **`synthesis/sentimentSynthesizer.js`** - Analyzes trends
- **`visualization/visualizer.js`** - Creates dashboards

### Configuration
- **`src/config.js`** - All settings in one place

### Utilities
- **`src/utils/logger.js`** - For logging messages
- **`src/utils/helpers.js`** - Useful functions (math, formatting, etc.)

---

## ⚙️ Configuration

Most things work automatically! But if you want to customize:

### Use Real Twitter/Reddit Data

Edit `.env`:
```bash
cp .env.example .env
nano .env
```

Add your API keys:
```
TWITTER_API_KEY=xxx
REDDIT_CLIENT_ID=xxx
```

### Change Settings

Edit `src/config.js`:

**Change embedding size:**
```javascript
embedding: {
  dimension: 1024,  // Change from 768
}
```

**Change confidence threshold:**
```javascript
classification: {
  confidenceThreshold: 0.5,  // Change from 0.6
}
```

---

## 🚨 Common Questions

### Q: I see "Cannot find module" error
**A:** Run `npm install` to install dependencies

### Q: The dashboard won't open
**A:** Find the HTML file manually:
```bash
ls output/visualizations/
open output/visualizations/dashboard.html
```

### Q: I want to use my own data
**A:** Edit `src/dataCollection/dataCollector.js` and modify the `getMockData()` function to return your data.

### Q: How do I use real Twitter data?
**A:** Follow `API-INTEGRATION.md` to get API keys and configure.

### Q: Can I use this in production?
**A:** Yes! The code is modular, well-documented, and production-ready.

### Q: Is Node.js required?
**A:** Yes, this is a Node.js project. Install from nodejs.org

---

## 📚 Next Steps

### Level 1: Basic Usage ✅
- [x] Install Node.js
- [x] Run `npm install`
- [x] Run `npm start`
- [x] Open dashboard.html

### Level 2: Explore More (Next)
- [ ] Read QUICKSTART.md
- [ ] Run individual commands (`npm run collect-data`, etc.)
- [ ] Customize sample data in `src/dataCollection/dataCollector.js`
- [ ] Change settings in `src/config.js`

### Level 3: Advanced Features
- [ ] Get real API keys (Twitter, Reddit)
- [ ] Follow API-INTEGRATION.md
- [ ] Connect to database (MongoDB, PostgreSQL)
- [ ] Deploy to cloud (AWS, Heroku, etc.)

### Level 4: Mastery
- [ ] Fine-tune the sentiment classifier with your data
- [ ] Add new data sources
- [ ] Create custom visualizations
- [ ] Deploy as a web service

---

## 🎯 Project Structure (Simplified)

```
Project Persona/
├── src/                    # Source code
│   ├── index.js           # Main entry point (run this)
│   ├── config.js          # Settings
│   ├── dataCollection/    # Get data
│   ├── preprocessing/     # Clean text
│   ├── embedding/         # Vector conversion
│   ├── classification/    # Sentiment labels
│   ├── synthesis/         # Analyze trends
│   ├── visualization/     # Create charts
│   └── utils/             # Helpers
│
├── data/                  # Data storage (auto-created)
│   ├── raw/              # Original data
│   ├── processed/        # Cleaned data
│   ├── embeddings/       # Vectors
│   └── classifications/  # Labels
│
├── output/               # Results (auto-created)
│   ├── synthesis/        # Analysis
│   └── visualizations/   # Dashboard & charts
│
├── package.json          # Dependencies
├── README.md             # Full documentation
├── QUICKSTART.md         # 5-minute tutorial
└── test.js              # Tests
```

---

## 💡 Tips & Tricks

### Quick Testing
```bash
node test.js
```
Validates all components work correctly.

### Watch Mode (Auto-reload)
```bash
npm run dev
```
Restarts automatically when you edit files.

### Run Full Pipeline
```bash
npm run pipeline
```
Equivalent to running all steps in sequence.

### Check Results
```bash
# View sentiment distribution
cat output/visualizations/sentiment_distribution.csv

# View analysis results
cat output/synthesis/sentiment_synthesis_*.json | jq .
```

---

## 🔐 Security Notes

- API keys go in `.env` (never in code)
- `.gitignore` prevents accidental commits
- No hardcoded secrets
- Safe for open source sharing

---

## 📞 Need Help?

| Question | File to Read |
|----------|-------------|
| "How do I get started?" | This file (you're reading it!) |
| "Show me 5-minute tutorial" | QUICKSTART.md |
| "I need complete docs" | README.md |
| "How do I use real APIs?" | API-INTEGRATION.md |
| "What files exist?" | FILE_INVENTORY.md |
| "How does it work?" | IMPLEMENTATION_SUMMARY.md |

---

## 🎉 You're Ready!

Everything is set up and working.

### Right now you can:
```bash
npm install
npm start
open output/visualizations/dashboard.html
```

### In 5 minutes you'll:
- Understand the full pipeline
- See real sentiment analysis results
- Know how to customize it

### In an hour you could:
- Add your own data
- Connect real APIs
- Deploy to production

---

## 🚀 Let's Go!

```bash
cd "Project Persona"
npm install
npm start
```

Open your browser and check: `output/visualizations/dashboard.html`

**Welcome to sentiment analysis with Node.js! 🎉**

---

For questions, check the docs:
- Quick answers → QUICKSTART.md
- Detailed answers → README.md
- API setup → API-INTEGRATION.md
- File reference → FILE_INVENTORY.md
