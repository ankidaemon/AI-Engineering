# API Integration Guide

This guide shows how to integrate real data sources (Twitter/X, Reddit) into the Sentiment Synthesizer.

## 📱 Twitter/X API Integration

### Setup

1. **Get API Keys**
   - Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
   - Create an app and generate API keys
   - Get API Key, Secret, and Bearer Token

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```

   Add to `.env`:
   ```env
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_BEARER_TOKEN=your_bearer_token
   ```

3. **Update Data Collector**

   Edit `src/dataCollection/dataCollector.js`:

   ```javascript
   async getTwitterData() {
     if (!this.twitterApiKey) {
       console.log('⚠️  Using mock Twitter data');
       return this.getMockTwitterData();
     }

     try {
       const headers = {
         'Authorization': `Bearer ${this.twitterApiKey}`
       };

       const response = await axios.get(
         'https://api.twitter.com/2/tweets/search/recent',
         {
           params: {
             query: 'sentiment analysis',
             max_results: 100,
             'tweet.fields': 'created_at,public_metrics,author_id'
           },
           headers
         }
       );

       return response.data.data.map(tweet => ({
         id: tweet.id,
         source: 'twitter',
         text: tweet.text,
         timestamp: tweet.created_at,
         metrics: tweet.public_metrics
       }));
     } catch (error) {
       console.error('Error fetching Twitter data:', error.message);
       return this.getMockTwitterData();
     }
   }
   ```

### Search Queries

Popular queries for sentiment analysis:

```javascript
const queries = [
  'sentiment analysis -is:retweet',
  'product review lang:en',
  'customer feedback -is:retweet',
  '#productname -is:retweet',
  'happy OR satisfied OR amazing'
];
```

## 📰 Reddit API Integration

### Setup

1. **Get Reddit Credentials**
   - Go to [Reddit App Settings](https://www.reddit.com/prefs/apps)
   - Create a "script" application
   - Get Client ID and Secret

2. **Configure Environment**

   Add to `.env`:
   ```env
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=sentiment-synthesizer/1.0 (+http://example.com)
   ```

3. **Implement Reddit Integration**

   Install PRAW wrapper (Python) or create Node.js version:

   ```bash
   npm install reddit
   ```

   ```javascript
   import reddit from 'reddit';

   async getRedditData() {
     const client = new reddit.Reddit({
       clientId: this.redditClientId,
       clientSecret: this.redditClientSecret,
       userAgent: this.redditUserAgent
     });

     const subreddits = ['AskReddit', 'learnprogramming', 'technology'];
     const allPosts = [];

     for (const subreddit of subreddits) {
       const posts = await client.getSubreddit(subreddit)
         .getNew({ limit: 100 });

       allPosts.push(...posts.map(post => ({
         id: post.id,
         source: 'reddit',
         text: post.title + ' ' + post.selftext,
         timestamp: new Date(post.created_utc * 1000).toISOString(),
         author: post.author.name,
         subreddit: post.subreddit.display_name,
         metrics: {
           upvotes: post.ups,
           downvotes: post.downs,
           comments: post.num_comments
         }
       })));
     }

     return allPosts;
   }
   ```

## 🌐 Generic HTTP API Integration

### Example: Custom API

```javascript
async getCustomAPIData(url, params = {}) {
  try {
    const response = await axios.get(url, { params });
    
    return response.data.items.map(item => ({
      id: item.id,
      source: 'custom',
      text: item.content || item.text,
      timestamp: item.created_at || new Date().toISOString(),
      author: item.author || 'unknown',
      metrics: item.metrics || {}
    }));
  } catch (error) {
    console.error('API Error:', error.message);
    return [];
  }
}
```

## 📊 Database Integration

### Save Results to MongoDB

```javascript
import { MongoClient } from 'mongodb';

const mongoUrl = process.env.MONGODB_URL || 'mongodb://localhost:27017';
const client = new MongoClient(mongoUrl);

export async function saveToMongoDB(synthesis) {
  try {
    await client.connect();
    const db = client.db('sentiment_synthesizer');
    
    // Save synthesis results
    await db.collection('results').insertOne({
      timestamp: new Date(),
      ...synthesis
    });
    
    console.log('✅ Results saved to MongoDB');
  } finally {
    await client.close();
  }
}
```

### Save Results to PostgreSQL

```javascript
import pg from 'pg';

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL
});

export async function saveToPSQL(synthesis) {
  try {
    await pool.query(
      'INSERT INTO sentiment_results (data, created_at) VALUES ($1, $2)',
      [JSON.stringify(synthesis), new Date()]
    );
    
    console.log('✅ Results saved to PostgreSQL');
  } finally {
    await pool.end();
  }
}
```

## 🔄 Scheduled Data Collection

### Using Node Cron

```bash
npm install node-cron
```

```javascript
import cron from 'node-cron';
import { DataCollector } from './dataCollection/dataCollector.js';
import { runPipeline } from './index.js';

// Run pipeline every 6 hours
cron.schedule('0 */6 * * *', async () => {
  console.log('🔄 Running scheduled sentiment analysis');
  try {
    await runPipeline();
    console.log('✅ Scheduled analysis completed');
  } catch (error) {
    console.error('❌ Scheduled analysis failed:', error);
  }
});

console.log('📅 Scheduled analysis active');
```

### Using AWS Lambda

```javascript
// handler.js
import { runPipeline } from './index.js';

export async function handler(event, context) {
  try {
    const result = await runPipeline();
    
    return {
      statusCode: 200,
      body: JSON.stringify({
        message: 'Pipeline completed',
        result
      })
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: error.message
      })
    };
  }
}
```

## 🔐 API Rate Limiting

```javascript
import Bottleneck from 'bottleneck';

const limiter = new Bottleneck({
  minTime: 100, // Minimum time between requests (ms)
  maxConcurrent: 5 // Maximum concurrent requests
});

export async function rateLimitedRequest(url, config) {
  return limiter.schedule(
    () => axios.get(url, config)
  );
}
```

## 📈 Data Stream Processing

### Real-time Processing

```javascript
import { EventEmitter } from 'events';

class DataStream extends EventEmitter {
  async startStream(source) {
    const dataCollector = new DataCollector();
    
    setInterval(async () => {
      const newData = await dataCollector.collectData();
      this.emit('data', newData);
    }, 5000); // Every 5 seconds
  }
}

const stream = new DataStream();
stream.on('data', async (data) => {
  // Process new data immediately
  const processed = preprocessor.preprocess(data);
  const embeddings = await embeddingGenerator.generateEmbeddings(processed);
  // ...
});

stream.startStream('twitter');
```

## 🛡️ Error Handling

```javascript
async function collectDataWithRetry(source) {
  const maxRetries = 3;
  let lastError;

  for (let i = 0; i < maxRetries; i++) {
    try {
      const collector = new DataCollector();
      return await collector.collectData();
    } catch (error) {
      lastError = error;
      
      // Exponential backoff
      const delay = Math.pow(2, i) * 1000;
      console.log(`Retry ${i + 1}/${maxRetries} after ${delay}ms`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
```

## 📝 Example: Complete Integration

```javascript
import { DataCollector } from './dataCollection/dataCollector.js';
import { Preprocessor } from './preprocessing/preprocessor.js';
import { EmbeddingGenerator } from './embedding/embeddingGenerator.js';
import { SentimentClassifier } from './classification/sentimentClassifier.js';
import { SentimentSynthesizer } from './synthesis/sentimentSynthesizer.js';
import { Visualizer } from './visualization/visualizer.js';

async function integratedPipeline() {
  console.log('Starting integrated sentiment pipeline...');

  // 1. Collect from Twitter API
  const collector = new DataCollector();
  const twitterData = await collector.getTwitterData();
  const redditData = await collector.getRedditData();
  const rawData = [...twitterData, ...redditData];

  console.log(`Collected ${rawData.length} samples`);

  // 2. Process
  const preprocessor = new Preprocessor();
  const processed = preprocessor.preprocess(rawData);

  // 3. Generate embeddings
  const embeddingGen = new EmbeddingGenerator();
  const embeddings = await embeddingGen.generateEmbeddings(processed);

  // 4. Classify
  const classifier = new SentimentClassifier();
  const classified = classifier.classifySentiment(embeddings);

  // 5. Synthesize
  const synthesizer = new SentimentSynthesizer();
  const synthesis = synthesizer.synthesizeSentiment(classified);

  // 6. Visualize
  const visualizer = new Visualizer();
  await visualizer.generateVisualizations(synthesis);

  // 7. Save to database (optional)
  // await saveToMongoDB(synthesis);

  return synthesis;
}

// Run
await integratedPipeline();
```

## 🧪 Testing API Integration

```javascript
// test-api-integration.js
async function testAPIs() {
  const collector = new DataCollector();

  console.log('Testing Twitter API...');
  try {
    const tweets = await collector.getTwitterData();
    console.log(`✅ Retrieved ${tweets.length} tweets`);
  } catch (error) {
    console.error('❌ Twitter API failed:', error.message);
  }

  console.log('Testing Reddit API...');
  try {
    const posts = await collector.getRedditData();
    console.log(`✅ Retrieved ${posts.length} posts`);
  } catch (error) {
    console.error('❌ Reddit API failed:', error.message);
  }
}

await testAPIs();
```

---

For production deployments, ensure you:
- ✅ Secure API keys with encryption
- ✅ Implement proper error handling
- ✅ Add rate limiting and backoff
- ✅ Log all API interactions
- ✅ Monitor quota and rate limits
- ✅ Cache responses when appropriate
