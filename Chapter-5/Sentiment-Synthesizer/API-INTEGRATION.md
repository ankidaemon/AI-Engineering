# API Integration Guide

Complete guide to configure real data collection from Twitter and Reddit APIs.

## 🔑 Getting API Credentials

### Twitter/X API Setup

#### Step 1: Create Developer Account
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Click "Sign up for free"
3. Choose "I want to create an app or bot"
4. Fill out use case details

#### Step 2: Create Application
1. Go to [developer.twitter.com/en/portal/dashboard](https://developer.twitter.com/en/portal/dashboard)
2. Click "Create App"
3. Give it a name: "Sentiment-Synthesizer"
4. Accept terms and create

#### Step 3: Get Credentials
1. Go to "Keys and tokens" tab
2. Copy the following:
   - **API Key** (API_KEY)
   - **API Secret Key** (API_SECRET)
   - **Bearer Token** (BEARER_TOKEN)

⚠️ **Important**: Store these securely. Never commit them to git.

#### Step 4: Update .env
```env
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_BEARER_TOKEN=your_bearer_token_here
```

#### Step 5: Set API Permissions
1. In Twitter Developer Portal, go to "App settings"
2. Under "Authentication settings", enable:
   - ✅ OAuth 1.0a User context
   - ✅ OAuth 2.0 Authorization Code with PKCE
   - ✅ OAuth 2.0 Bearer Token

---

### Reddit API Setup

#### Step 1: Create Application
1. Go to [reddit.com/prefs/apps](https://reddit.com/prefs/apps)
2. Scroll to bottom, click "Create App"
3. Fill form:
   - **Name**: "Sentiment-Synthesizer"
   - **App type**: "Script"
   - **Description**: "Social media sentiment analysis"
4. Click "Create app"

#### Step 2: Get Credentials
After creating, you'll see:
- **Client ID** (shown below the app name)
- **Client Secret** (click "show" button)
- Copy both values

#### Step 3: Update .env
```env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=sentiment-synthesizer/1.0.0 by your_reddit_username
```

**Note**: USER_AGENT should be in format: `app_name/version by reddit_username`

#### Step 4: Required Reddit Settings
- Account must be 30+ days old
- Recommended: Enable 2FA for security

---

## 🔐 Environment Configuration

### Create .env File

1. **Copy template**:
```bash
cp .env.example .env
```

2. **Edit .env** with your credentials:
```env
# Twitter API
TWITTER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
TWITTER_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
TWITTER_BEARER_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# Reddit API
REDDIT_CLIENT_ID=xxxxxxxxxxxxxxxx
REDDIT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
REDDIT_USER_AGENT=sentiment-synthesizer/1.0.0 by your_username

# Optional Configuration
DEBUG=False
LOG_LEVEL=INFO
```

3. **Verify permissions** - File should only be readable by you:
```bash
chmod 600 .env
```

### .gitignore Protection

Ensure `.gitignore` contains:
```
.env
.env.local
.env.*.local
```

---

## 🧪 Testing API Connections

### Test Twitter Connection

```python
# test_twitter_connection.py
from src.data_collection import DataCollector
from config import Config

config = Config()
collector = DataCollector(config)

# Test Twitter API
print("Testing Twitter connection...")
try:
    tweets = collector._get_twitter_data()
    print(f"✅ Success! Collected {len(tweets)} tweets")
    for tweet in tweets[:2]:
        print(f"  - {tweet['text'][:60]}...")
except Exception as e:
    print(f"❌ Error: {e}")
```

### Test Reddit Connection

```python
# test_reddit_connection.py
from src.data_collection import DataCollector
from config import Config

config = Config()
collector = DataCollector(config)

# Test Reddit API
print("Testing Reddit connection...")
try:
    posts = collector._get_reddit_data()
    print(f"✅ Success! Collected {len(posts)} posts")
    for post in posts[:2]:
        print(f"  - {post['text'][:60]}...")
except Exception as e:
    print(f"❌ Error: {e}")
```

### Run Tests

```bash
python test_twitter_connection.py
python test_reddit_connection.py
```

---

## 🔄 Data Collection Workflow

### Automatic Fallback Mechanism

The data collector implements graceful fallback:

```
Try Real APIs
    ↓
    ├─ Success? → Use real data
    │
    └─ Fail? → Try mock data
           ↓
           └─ Return mock samples
```

**This means:**
- ✅ Works without APIs configured
- ✅ Works with partial credentials
- ✅ Seamless fallback to mock data
- ✅ Perfect for development/testing

### API Rate Limits

#### Twitter
- 450 requests/15 minutes
- Adjust collection size in `config.py`

#### Reddit
- 60 requests/minute (default)
- Adjust collection size in `config.py`

---

## 📊 Customizing Data Collection

### In config.py

```python
# Adjust collection parameters
config.TWITTER_QUERY = "sentiment analysis"  # Search term
config.TWITTER_COUNT = 100                   # Number to collect
config.TWITTER_LANG = "en"                   # Language

config.REDDIT_SUBREDDIT = "technology"       # Which subreddit
config.REDDIT_TIME_FILTER = "week"           # Time range
config.REDDIT_COUNT = 50                     # Number to collect
```

### Custom Search Queries

```python
# Modify _get_twitter_data() in data_collection.py
query = 'python programming lang:en -is:retweet'
# Returns only English, non-retweets about Python

# Available Twitter operators:
# lang:en              - English language
# -is:retweet          - Exclude retweets
# has:links            - Has URLs
# verified             - Verified accounts only
# from:username        - From specific user
```

---

## 🚨 Troubleshooting

### Twitter Connection Issues

**Error: "AuthenticationError"**
```
Solution: Verify Bearer Token in .env
- Re-copy from Twitter Developer Portal
- Ensure no extra spaces/quotes
```

**Error: "Invalid Bearer Token"**
```
Solution: Token may have expired
- Generate new token in Developer Portal
- Update .env file
```

**Error: "You are being rate limited"**
```
Solution: Reduce collection frequency
config.TWITTER_COUNT = 50  # Reduce from 100
# Wait 15 minutes before next request
```

### Reddit Connection Issues

**Error: "401 Unauthorized"**
```
Solution: Check credentials
- Verify Client ID matches
- Verify Client Secret matches
- Check USER_AGENT format (must include username)
```

**Error: "403 Forbidden"**
```
Solution: Account restrictions
- Account must be 30+ days old
- Check if banned from subreddit
- Try different subreddit
```

**Error: "404 Not Found"**
```
Solution: Subreddit doesn't exist
- Verify subreddit name spelling
- Check if subreddit is public
- Try another subreddit
```

### General Issues

**"Module 'tweepy' not found"**
```bash
pip install tweepy
```

**"Module 'praw' not found"**
```bash
pip install praw
```

**"Environment variables not loading"**
```python
# In .env, ensure format is:
KEY=value  # No spaces around =
# No quotes needed
```

---

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Store credentials in `.env` file
- ✅ Add `.env` to `.gitignore`
- ✅ Regenerate tokens periodically
- ✅ Use environment variables for sensitive data
- ✅ Limit API app permissions to minimum needed
- ✅ Rotate credentials if compromised

### ❌ DON'T:
- ❌ Commit .env to git
- ❌ Share credentials in Slack/email
- ❌ Log sensitive information
- ❌ Hardcode credentials in code
- ❌ Use weak/reused passwords
- ❌ Grant unnecessary permissions

### Credential Rotation

```bash
# If credentials are exposed:
1. Go to developer portal
2. Regenerate tokens immediately
3. Update .env file
4. Verify no commits contain old credentials
5. Alert relevant platforms
```

---

## 📈 API Quotas and Limits

### Twitter API (Free Tier)
| Resource | Limit |
|----------|-------|
| Posts retrieved | 300 per request |
| Requests per 15 min | 450 |
| Requests per month | ~1.3M |
| Data retention | 7 days (recent posts) |

### Reddit API (Free)
| Resource | Limit |
|----------|-------|
| Requests per minute | 60 |
| No daily/monthly limit | ✅ |
| Concurrent requests | 1 |
| User agent required | Yes |

**Pro tip**: Space out requests to stay well under limits.

---

## 🎯 Advanced Configuration

### Custom Headers

```python
# In config.py
config.REQUEST_TIMEOUT = 30  # seconds
config.RETRY_ATTEMPTS = 3
config.RETRY_DELAY = 5  # seconds
```

### Filtering Options

```python
# Filter by sentiment even before classification
KEYWORDS_POSITIVE = ["love", "great", "excellent", "amazing"]
KEYWORDS_NEGATIVE = ["hate", "awful", "terrible", "worst"]
KEYWORDS_NEUTRAL = ["data", "information", "report"]
```

### Data Preprocessing

```python
# Skip certain samples
MIN_LENGTH = 10  # Ignore tweets < 10 chars
MAX_LENGTH = 280  # Ignore tweets > 280 chars
FILTER_URLS = True  # Remove posts with URLs
FILTER_MENTIONS = True  # Remove posts mentioning accounts
```

---

## 📚 References

- [Twitter API Documentation](https://developer.twitter.com/en/docs/api)
- [Reddit PRAW Documentation](https://praw.readthedocs.io/)
- [OAuth 2.0 Guide](https://oauth.net/2/)
- [API Best Practices](https://cloud.google.com/docs/authentication/production)

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] .env file created with credentials
- [ ] .env added to .gitignore
- [ ] Twitter API connection tested
- [ ] Reddit API connection tested
- [ ] Mock data works without APIs
- [ ] Real data collection works
- [ ] No credentials in git history
- [ ] Credentials not logged to console

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `python main.py 2>&1 | tee debug.log`
2. **Test individually**: Use test scripts above
3. **Verify credentials**: Double-check .env file
4. **Check API status**: Visit platform status pages
5. **Review documentation**: API docs for specific platform
6. **Enable debug mode**: Set `DEBUG=True` in .env

**Happy collecting! 🎉**
