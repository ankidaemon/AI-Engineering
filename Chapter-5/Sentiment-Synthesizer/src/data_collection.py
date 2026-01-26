"""
Data collection module for gathering social media data
Supports Twitter, Reddit, and mock data sources
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import random

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects data from various social media sources"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.DATA_DIR / "raw"
        
    def collect_data(self) -> List[Dict[str, Any]]:
        """Collect data from all configured sources"""
        all_data = []
        
        # Try to collect from real APIs, fallback to mock data
        logger.info("Collecting data from configured sources...")
        
        try:
            twitter_data = self._get_twitter_data()
            all_data.extend(twitter_data)
        except Exception as e:
            logger.warning(f"Twitter API error: {e}. Using mock data instead.")
            all_data.extend(self._get_mock_twitter_data())
        
        try:
            reddit_data = self._get_reddit_data()
            all_data.extend(reddit_data)
        except Exception as e:
            logger.warning(f"Reddit API error: {e}. Using mock data instead.")
            all_data.extend(self._get_mock_reddit_data())
        
        # If no API data collected, use mock
        if not all_data:
            all_data.extend(self._get_mock_twitter_data())
            all_data.extend(self._get_mock_reddit_data())
        
        # Save collected data
        self._save_data(all_data)
        return all_data
    
    def _get_twitter_data(self) -> List[Dict[str, Any]]:
        """Collect data from Twitter API"""
        if not self.config.TWITTER_BEARER_TOKEN:
            raise ValueError("Twitter API credentials not configured")
        
        try:
            import tweepy
            client = tweepy.Client(bearer_token=self.config.TWITTER_BEARER_TOKEN)
            
            # Search for tweets about sentiment analysis
            tweets = client.search_recent_tweets(
                query="sentiment analysis -is:retweet",
                max_results=100,
                tweet_fields=['created_at', 'public_metrics', 'author_id']
            )
            
            return [
                {
                    'id': tweet.id,
                    'source': 'twitter',
                    'text': tweet.text,
                    'timestamp': tweet.created_at.isoformat(),
                    'metrics': tweet.public_metrics
                }
                for tweet in tweets.data or []
            ]
        except Exception as e:
            logger.error(f"Error fetching Twitter data: {e}")
            return []
    
    def _get_reddit_data(self) -> List[Dict[str, Any]]:
        """Collect data from Reddit API"""
        if not self.config.REDDIT_CLIENT_ID or not self.config.REDDIT_CLIENT_SECRET:
            raise ValueError("Reddit API credentials not configured")
        
        try:
            import praw
            reddit = praw.Reddit(
                client_id=self.config.REDDIT_CLIENT_ID,
                client_secret=self.config.REDDIT_CLIENT_SECRET,
                user_agent=self.config.REDDIT_USER_AGENT
            )
            
            posts = []
            for subreddit_name in ['AskReddit', 'learnprogramming', 'technology']:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.new(limit=30):
                    posts.append({
                        'id': submission.id,
                        'source': 'reddit',
                        'text': submission.title + ' ' + submission.selftext,
                        'timestamp': datetime.fromtimestamp(submission.created_utc).isoformat(),
                        'author': str(submission.author),
                        'subreddit': subreddit_name,
                        'metrics': {
                            'upvotes': submission.ups,
                            'downvotes': submission.downs,
                            'comments': submission.num_comments
                        }
                    })
            
            return posts
        except Exception as e:
            logger.error(f"Error fetching Reddit data: {e}")
            return []
    
    def _get_mock_twitter_data(self) -> List[Dict[str, Any]]:
        """Get mock Twitter data for demonstration"""
        return [
            {
                'id': 'tw_001',
                'source': 'twitter',
                'text': 'I absolutely love this new product! Best purchase ever made!',
                'timestamp': datetime.now().isoformat(),
                'author': 'user123',
                'metrics': {'likes': 234, 'retweets': 45, 'replies': 12}
            },
            {
                'id': 'tw_002',
                'source': 'twitter',
                'text': 'This is the worst experience I have ever had. Very disappointed.',
                'timestamp': datetime.now().isoformat(),
                'author': 'user456',
                'metrics': {'likes': 12, 'retweets': 5, 'replies': 3}
            },
            {
                'id': 'tw_003',
                'source': 'twitter',
                'text': 'The product is okay, nothing special but does the job.',
                'timestamp': datetime.now().isoformat(),
                'author': 'user789',
                'metrics': {'likes': 45, 'retweets': 12, 'replies': 5}
            },
            {
                'id': 'tw_004',
                'source': 'twitter',
                'text': 'Amazing customer service! They really helped me out quickly.',
                'timestamp': datetime.now().isoformat(),
                'author': 'user012',
                'metrics': {'likes': 156, 'retweets': 34, 'replies': 8}
            },
            {
                'id': 'tw_005',
                'source': 'twitter',
                'text': 'Not satisfied with the quality. Expected much better for this price.',
                'timestamp': datetime.now().isoformat(),
                'author': 'user345',
                'metrics': {'likes': 23, 'retweets': 8, 'replies': 4}
            },
        ]
    
    def _get_mock_reddit_data(self) -> List[Dict[str, Any]]:
        """Get mock Reddit data for demonstration"""
        return [
            {
                'id': 'rd_001',
                'source': 'reddit',
                'text': 'Just tried this app and it has completely transformed my workflow!',
                'timestamp': datetime.now().isoformat(),
                'author': 'redditor1',
                'subreddit': 'programming',
                'metrics': {'upvotes': 567, 'downvotes': 12, 'comments': 89}
            },
            {
                'id': 'rd_002',
                'source': 'reddit',
                'text': 'I have to warn everyone - stay away from this service. Total scam!',
                'timestamp': datetime.now().isoformat(),
                'author': 'redditor2',
                'subreddit': 'scams',
                'metrics': {'upvotes': 234, 'downvotes': 5, 'comments': 45}
            },
            {
                'id': 'rd_003',
                'source': 'reddit',
                'text': 'Great documentation and helpful community. Highly recommend!',
                'timestamp': datetime.now().isoformat(),
                'author': 'redditor3',
                'subreddit': 'learnprogramming',
                'metrics': {'upvotes': 789, 'downvotes': 2, 'comments': 123}
            },
        ]
    
    def _save_data(self, data: List[Dict[str, Any]]):
        """Save collected data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"collected_data_{timestamp}.json"
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Data saved to {filepath}")
