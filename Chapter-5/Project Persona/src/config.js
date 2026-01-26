/**
 * Configuration Module
 * Centralized configuration for the Sentiment Synthesizer
 */

export const config = {
  // Application Settings
  app: {
    name: 'Sentiment Synthesizer',
    version: '1.0.0',
    description: 'NLP system for sentiment analysis from social media data',
    author: 'AI Engineering Team'
  },

  // Data Collection Settings
  dataCollection: {
    sources: ['twitter', 'reddit'],
    mockDataEnabled: true,
    timeout: 30000,
    retryAttempts: 3,
    retryDelay: 1000
  },

  // Text Preprocessing Settings
  preprocessing: {
    minTokenLength: 1,
    maxSequenceLength: 128,
    removeUrls: true,
    removeMentions: true,
    removeHashtags: false,
    lowercase: true,
    removeSpecialChars: true
  },

  // Embedding Settings
  embedding: {
    dimension: 768,
    model: 'bert-base-uncased',
    poolingStrategy: 'mean',
    normalization: true,
    saveEmbeddings: true
  },

  // Classification Settings
  classification: {
    labels: ['negative', 'neutral', 'positive'],
    confidenceThreshold: 0.6,
    heuristicWeight: 0.5,
    embeddingWeight: 0.5,
    finetuneEnabled: false,
    epochs: 3
  },

  // Synthesis Settings
  synthesis: {
    topicsCount: 10,
    minTopicFrequency: 2,
    generateInsights: true,
    includeTemporalAnalysis: true
  },

  // Visualization Settings
  visualization: {
    generateDashboard: true,
    generateCharts: true,
    exportCSV: true,
    consoleOutput: true,
    dashboard: {
      theme: 'modern',
      responsive: true,
      chartLibrary: 'plotly'
    }
  },

  // Output Settings
  output: {
    baseDir: './output',
    rawDataDir: './data/raw',
    processedDataDir: './data/processed',
    embeddingsDir: './data/embeddings',
    classificationsDir: './data/classifications',
    synthesisDir: './output/synthesis',
    visualizationsDir: './output/visualizations'
  },

  // Processing Settings
  processing: {
    batchSize: 32,
    parallelProcessing: false,
    maxWorkers: 4,
    enableCache: true,
    cacheTTL: 3600000 // 1 hour
  },

  // API Settings
  api: {
    twitter: {
      apiVersion: '2',
      endpoint: 'https://api.twitter.com/2',
      timeout: 10000
    },
    reddit: {
      endpoint: 'https://oauth.reddit.com',
      timeout: 10000
    }
  },

  // Sentiment Keywords for Heuristic Scoring
  sentimentKeywords: {
    positive: [
      'love', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
      'awesome', 'best', 'perfect', 'good', 'happy', 'beautiful', 'brilliant',
      'impressed', 'satisfied', 'delighted', 'fantastic', 'outstanding'
    ],
    negative: [
      'hate', 'bad', 'terrible', 'awful', 'horrible', 'worst', 'poor',
      'disappointed', 'angry', 'sad', 'disgusting', 'useless', 'waste',
      'frustrated', 'upset', 'displeased', 'regret', 'scam'
    ],
    neutral: [
      'ok', 'okay', 'alright', 'fine', 'average', 'normal', 'regular',
      'middle', 'moderate', 'decent'
    ]
  },

  // Logging Settings
  logging: {
    level: 'info', // 'debug', 'info', 'warn', 'error'
    format: 'json', // 'json', 'text'
    includeTimestamp: true,
    includeFile: true,
    saveLogs: true,
    logDir: './logs'
  }
};

/**
 * Get configuration value by path
 * @param {string} path - Dot-notation path (e.g., 'embedding.dimension')
 * @param {*} defaultValue - Default value if path not found
 * @returns {*} Configuration value
 */
export function getConfig(path, defaultValue = undefined) {
  const keys = path.split('.');
  let value = config;

  for (const key of keys) {
    value = value?.[key];
    if (value === undefined) {
      return defaultValue;
    }
  }

  return value;
}

/**
 * Set configuration value by path
 * @param {string} path - Dot-notation path
 * @param {*} value - Value to set
 */
export function setConfig(path, value) {
  const keys = path.split('.');
  const lastKey = keys.pop();
  let obj = config;

  for (const key of keys) {
    if (!obj[key]) {
      obj[key] = {};
    }
    obj = obj[key];
  }

  obj[lastKey] = value;
}

/**
 * Get entire configuration
 * @returns {object} Full configuration object
 */
export function getFullConfig() {
  return JSON.parse(JSON.stringify(config));
}

export default config;
