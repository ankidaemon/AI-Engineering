import fs from 'fs';
import path from 'path';

/**
 * Preprocessor - Handles text cleaning and tokenization
 * Implements BERT-style preprocessing
 */
export class Preprocessor {
  constructor() {
    this.outputDir = './data/processed';
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Main preprocessing pipeline
   */
  preprocess(rawData) {
    console.log('Starting preprocessing pipeline...');
    
    let processed = rawData
      .map(item => ({
        ...item,
        cleaned_text: this.cleanText(item.text),
        tokens: this.tokenize(item.text),
        word_count: this.tokenize(item.text).length
      }))
      .filter(item => item.word_count > 0); // Remove empty texts

    // Save processed data
    this.saveProcessedData(processed);
    
    return processed;
  }

  /**
   * Clean text by removing special characters, URLs, mentions, etc.
   */
  cleanText(text) {
    if (!text) return '';

    let cleaned = text
      // Remove URLs
      .replace(/https?:\/\/\S+/g, '')
      // Remove mentions (@user)
      .replace(/@\w+/g, '')
      // Remove hashtags but keep text (#hashtag -> hashtag)
      .replace(/#(\w+)/g, '$1')
      // Remove extra whitespace
      .replace(/\s+/g, ' ')
      // Remove special characters except punctuation
      .replace(/[^\w\s.!?-]/g, '')
      .trim();

    return cleaned.toLowerCase();
  }

  /**
   * Tokenize text into words
   * BERT-style: splits on whitespace and punctuation
   */
  tokenize(text) {
    const cleaned = this.cleanText(text);
    
    // Simple tokenization: split on whitespace and punctuation
    const tokens = cleaned
      .split(/\s+/)
      .filter(token => token.length > 0);

    // Apply BPE-like subword tokenization for common patterns
    return this.applySubwordTokenization(tokens);
  }

  /**
   * Simple subword tokenization (approximates BERT tokenization)
   */
  applySubwordTokenization(tokens) {
    const subwordTokens = [];
    const minCharCount = 4;

    tokens.forEach(token => {
      if (token.length > minCharCount) {
        // For long tokens, split into meaningful subwords
        subwordTokens.push(`##${token.slice(0, Math.ceil(token.length / 2))}`);
        subwordTokens.push(token.slice(Math.ceil(token.length / 2)));
      } else {
        subwordTokens.push(token);
      }
    });

    return subwordTokens;
  }

  /**
   * Apply padding to sequences
   */
  padSequence(tokens, maxLength = 128) {
    if (tokens.length > maxLength) {
      return tokens.slice(0, maxLength);
    }
    
    const padToken = '[PAD]';
    const padding = Array(maxLength - tokens.length).fill(padToken);
    return [...tokens, ...padding];
  }

  /**
   * Extract linguistic features
   */
  extractFeatures(text) {
    const tokens = this.tokenize(text);
    
    return {
      token_count: tokens.length,
      has_exclamation: text.includes('!'),
      has_question: text.includes('?'),
      has_caps: /[A-Z]/.test(text),
      caps_ratio: (text.match(/[A-Z]/g) || []).length / text.length,
      punctuation_count: (text.match(/[.!?]/g) || []).length
    };
  }

  /**
   * Save processed data to file
   */
  saveProcessedData(data) {
    const filename = `processed_data_${Date.now()}.json`;
    const filepath = path.join(this.outputDir, filename);
    
    fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
    console.log(`✅ Processed data saved to ${filepath}`);
  }
}
