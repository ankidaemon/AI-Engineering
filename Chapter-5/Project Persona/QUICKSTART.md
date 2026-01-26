# Sentiment Synthesizer - Quick Start Guide

Get started with the Sentiment Synthesizer in 5 minutes!

## 📋 Prerequisites

- Node.js 16+ installed
- npm or yarn package manager
- Basic understanding of sentiment analysis concepts

## 🚀 Quick Installation

### Step 1: Navigate to Project
```bash
cd "Project Persona"
```

### Step 2: Install Dependencies
```bash
npm install
```

This installs:
- `axios` - HTTP requests for APIs
- `cheerio` - Web scraping
- `dotenv` - Environment variable management
- `onnxruntime-node` - Model inference
- `xlsx` - Excel/CSV handling

### Step 3: Configure Environment (Optional)

For API integration, create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
TWITTER_API_KEY=your_key_here
REDDIT_CLIENT_ID=your_id_here
```

**Note**: Without API keys, the system uses mock data automatically.

## ⚡ Quick Start Commands

### Run Complete Pipeline
```bash
npm start
```

**What happens**:
1. Collects sample data
2. Preprocesses text
3. Generates embeddings
4. Classifies sentiments
5. Synthesizes insights
6. Creates visualizations

**Expected output**:
- Console logs with processing status
- Files in `data/` and `output/` directories
- Interactive dashboard at `output/visualizations/dashboard.html`

### Run Individual Steps

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
```

### Run Tests
```bash
node test.js
```

Validates all core functionality without APIs.

### Development Mode
```bash
npm run dev
```

Auto-restarts on file changes.

## 📁 Where to Find Results

After running the pipeline, check:

| Directory | Purpose |
|-----------|---------|
| `data/raw/` | Raw collected data |
| `data/processed/` | Cleaned & tokenized text |
| `data/embeddings/` | Embedding vectors (768-dim) |
| `data/classifications/` | Sentiment labels & scores |
| `output/synthesis/` | Aggregated insights |
| `output/visualizations/` | Charts & dashboard |

### View the Dashboard

```bash
# macOS
open output/visualizations/dashboard.html

# Linux
xdg-open output/visualizations/dashboard.html

# Windows
start output/visualizations/dashboard.html
```

### Check Results

View sentiment distribution:
```bash
cat output/visualizations/sentiment_distribution.csv
```

View trends:
```bash
cat output/visualizations/sentiment_trends.csv
```

## 🎯 Understanding the Output

### Console Output Example

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
✅ Saved: sentiment_distribution.csv
✅ Saved: sentiment_trends.csv
✅ Saved: source_comparison.csv
✅ Saved: top_topics.csv
✅ Saved: dashboard.html
✅ All visualizations generated

🎉 Pipeline completed successfully!
Results saved to output/ directory
```

### Sentiment Distribution Example

```
========================================
   Sentiment Distribution
========================================
positive   │ ████████ 50% (4)
neutral    │ ████ 25% (2)
negative   │ ████ 25% (2)
========================================
```

### Dashboard Metrics

The HTML dashboard shows:
- ✅ **Positive**: Number and percentage
- ⚠️ **Neutral**: Number and percentage  
- ❌ **Negative**: Number and percentage
- 📊 **Source Breakdown**: Per-platform stats
- 🏷️ **Top Topics**: Most frequent keywords
- 💡 **Key Insights**: Actionable findings

## 📊 Example Workflow

### 1. Basic Usage
```bash
# Start with sample data
npm start

# Check the results
open output/visualizations/dashboard.html
```

### 2. With Custom Data

Edit `src/dataCollection/dataCollector.js`:

```javascript
getMockTwitterData() {
  return [
    {
      id: 'custom_001',
      source: 'twitter',
      text: 'Your custom text here',
      timestamp: new Date().toISOString(),
      author: 'user'
    }
  ];
}
```

Then run:
```bash
npm run collect-data
npm run pipeline
```

### 3. Analyze Results

```javascript
// After running, examine the JSON files:
cat data/processed/processed_data_*.json
cat output/synthesis/sentiment_synthesis_*.json
```

## 🔧 Common Customizations

### Change Sentiment Labels
Edit `src/classification/sentimentClassifier.js`:
```javascript
this.sentimentLabels = ['negative', 'neutral', 'positive'];
```

### Adjust Confidence Threshold
Edit `src/classification/sentimentClassifier.js`:
```javascript
this.confidenceThreshold = 0.5; // Lower = more sensitive
```

### Increase Embedding Dimension
Edit `src/embedding/embeddingGenerator.js`:
```javascript
this.embeddingDim = 1024; // Default is 768
```

### Change Top Topics Count
Edit `src/synthesis/sentimentSynthesizer.js`:
```javascript
topTopics = Object.entries(wordFreq)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 15); // Changed from 10
```

## 🐛 Troubleshooting

### Issue: "Cannot find module"
```bash
# Solution: Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Issue: "Output directories don't exist"
```bash
# Solution: Create them manually
mkdir -p data/{raw,processed,embeddings,classifications}
mkdir -p output/{synthesis,visualizations}
```

### Issue: Out of memory
```bash
# Solution: Run with increased heap size
node --max-old-space-size=4096 src/index.js
```

### Issue: Slow processing
```bash
# Solution: Process smaller batch size
# Edit in src/index.js and reduce sample count
```

## 📚 Next Steps

### Learn More

1. **Examine the code**: Read comments in `src/` modules
2. **Modify heuristics**: Update sentiment keywords in each module
3. **Add new sources**: Integrate real Twitter/Reddit APIs
4. **Fine-tune models**: Implement model training with your data
5. **Deploy**: Package for production use

### Explore Features

- [ ] Configure with your own API keys
- [ ] Customize sentiment keywords
- [ ] Generate dashboards for your data
- [ ] Implement fine-tuning with labeled data
- [ ] Add more visualization types
- [ ] Integrate with databases

### Integration Examples

**Save to Database**:
```javascript
// Add MongoDB or PostgreSQL integration
const sentiment = classification[0];
await db.sentiments.insert(sentiment);
```

**Send to API**:
```javascript
// Forward results to your service
axios.post('https://api.example.com/sentiments', synthesis);
```

**Schedule Recurring Analysis**:
```javascript
// Run pipeline daily with cron
import cron from 'node-cron';
cron.schedule('0 0 * * *', () => {
  // Run pipeline daily
});
```

## 💡 Tips

- **Mock data enabled**: Test without APIs
- **Modular design**: Easily swap out components
- **Fast execution**: Completes in seconds
- **Visual feedback**: Console and HTML outputs
- **Extensible**: Add custom analysis steps

## 📞 Need Help?

1. Check the full [README.md](./README.md) for detailed documentation
2. Review module comments in `src/` directory
3. Run `node test.js` to verify setup
4. Check console output for error messages

---

**You're ready to go! Happy sentiment analyzing! 🎉**
