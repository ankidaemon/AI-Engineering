import axios from 'axios';
import fs from 'fs';
import path from 'path';

/**
 * DataCollector - Handles data collection from various sources
 * Supports Twitter/X API, Reddit, and local datasets
 */
export class DataCollector {
  constructor() {
    this.twitterApiKey = process.env.TWITTER_API_KEY;
    this.redditClientId = process.env.REDDIT_CLIENT_ID;
    this.redditClientSecret = process.env.REDDIT_CLIENT_SECRET;
    this.outputDir = './data/raw';
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Collect data from multiple sources
   */
  async collectData() {
    console.log('Collecting data from configured sources...');
    
    const allData = [];
    
    // Collect from mock sources if APIs not available
    const mockData = this.getMockData();
    allData.push(...mockData);

    // Save collected data
    this.saveData(allData);
    
    return allData;
  }

  /**
   * Get mock Twitter data for demonstration
   */
  async getTwitterData() {
    if (!this.twitterApiKey) {
      console.log('⚠️  Twitter API key not configured. Using mock data.');
      return this.getMockTwitterData();
    }

    try {
      const headers = {
        'Authorization': `Bearer ${this.twitterApiKey}`
      };

      const response = await axios.get('https://api.twitter.com/2/tweets/search/recent', {
        params: {
          query: 'sentiment analysis',
          max_results: 100,
          'tweet.fields': 'created_at,public_metrics'
        },
        headers
      });

      return response.data.data.map(tweet => ({
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

  /**
   * Get mock Reddit data for demonstration
   */
  async getRedditData() {
    if (!this.redditClientId || !this.redditClientSecret) {
      console.log('⚠️  Reddit credentials not configured. Using mock data.');
      return this.getMockRedditData();
    }

    try {
      // Reddit API integration would go here
      return this.getMockRedditData();
    } catch (error) {
      console.error('Error fetching Reddit data:', error.message);
      return this.getMockRedditData();
    }
  }

  /**
   * Generate mock data for demonstration
   */
  getMockData() {
    const tweets = this.getMockTwitterData();
    const redditPosts = this.getMockRedditData();
    return [...tweets, ...redditPosts];
  }

  getMockTwitterData() {
    return [
      {
        id: 'tw_001',
        source: 'twitter',
        text: 'I absolutely love this new product! Best purchase ever made!',
        timestamp: new Date().toISOString(),
        author: 'user123',
        metrics: { likes: 234, retweets: 45 }
      },
      {
        id: 'tw_002',
        source: 'twitter',
        text: 'This is the worst experience I have ever had. Very disappointed.',
        timestamp: new Date().toISOString(),
        author: 'user456',
        metrics: { likes: 12, retweets: 5 }
      },
      {
        id: 'tw_003',
        source: 'twitter',
        text: 'The product is okay, nothing special but does the job.',
        timestamp: new Date().toISOString(),
        author: 'user789',
        metrics: { likes: 45, retweets: 12 }
      },
      {
        id: 'tw_004',
        source: 'twitter',
        text: 'Amazing customer service! They really helped me out quickly.',
        timestamp: new Date().toISOString(),
        author: 'user012',
        metrics: { likes: 156, retweets: 34 }
      },
      {
        id: 'tw_005',
        source: 'twitter',
        text: 'Not satisfied with the quality. Expected much better for this price.',
        timestamp: new Date().toISOString(),
        author: 'user345',
        metrics: { likes: 23, retweets: 8 }
      }
    ];
  }

  getMockRedditData() {
    return [
      {
        id: 'rd_001',
        source: 'reddit',
        text: 'Just tried this app and it has completely transformed my workflow!',
        timestamp: new Date().toISOString(),
        author: 'redditor1',
        subreddit: 'programming',
        metrics: { upvotes: 567, comments: 89 }
      },
      {
        id: 'rd_002',
        source: 'reddit',
        text: 'I have to warn everyone - stay away from this service. Total scam!',
        timestamp: new Date().toISOString(),
        author: 'redditor2',
        subreddit: 'scams',
        metrics: { upvotes: 234, comments: 45 }
      },
      {
        id: 'rd_003',
        source: 'reddit',
        text: 'Great documentation and helpful community. Highly recommend!',
        timestamp: new Date().toISOString(),
        author: 'redditor3',
        subreddit: 'learnprogramming',
        metrics: { upvotes: 789, comments: 123 }
      }
    ];
  }

  /**
   * Save collected data to file
   */
  saveData(data) {
    const filename = `collected_data_${Date.now()}.json`;
    const filepath = path.join(this.outputDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
    console.log(`✅ Data saved to ${filepath}`);
  }

  /**
   * Load existing dataset from file
   */
  loadDataset(filepath) {
    try {
      const data = fs.readFileSync(filepath, 'utf-8');
      return JSON.parse(data);
    } catch (error) {
      console.error('Error loading dataset:', error.message);
      return [];
    }
  }
}
