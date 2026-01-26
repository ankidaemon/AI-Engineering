/**
 * Test Script for Sentiment Synthesizer
 * Tests core functionality without external API dependencies
 */

import { DataCollector } from './dataCollection/dataCollector.js';
import { Preprocessor } from './preprocessing/preprocessor.js';
import { EmbeddingGenerator } from './embedding/embeddingGenerator.js';
import { SentimentClassifier } from './classification/sentimentClassifier.js';
import { SentimentSynthesizer } from './synthesis/sentimentSynthesizer.js';
import { Visualizer } from './visualization/visualizer.js';
import { Logger } from './utils/logger.js';

const logger = new Logger('Tests');

/**
 * Run all tests
 */
async function runTests() {
  console.log('\n🧪 Running Sentiment Synthesizer Tests...\n');
  
  let passed = 0;
  let failed = 0;

  try {
    // Test 1: Data Collection
    console.log('Test 1: Data Collection');
    const dataCollector = new DataCollector();
    const rawData = await dataCollector.collectData();
    
    if (Array.isArray(rawData) && rawData.length > 0) {
      console.log('✅ PASSED: Data collection returns array with samples\n');
      passed++;
    } else {
      console.log('❌ FAILED: Data collection failed\n');
      failed++;
    }

    // Test 2: Preprocessing
    console.log('Test 2: Preprocessing');
    const preprocessor = new Preprocessor();
    const cleaned = preprocessor.preprocess(rawData);
    
    const hasTokens = cleaned.every(item => Array.isArray(item.tokens));
    const hasCleaned = cleaned.every(item => typeof item.cleaned_text === 'string');
    
    if (hasTokens && hasCleaned && cleaned.length > 0) {
      console.log('✅ PASSED: Preprocessing produces tokenized output\n');
      passed++;
    } else {
      console.log('❌ FAILED: Preprocessing validation failed\n');
      failed++;
    }

    // Test 3: Embedding Generation
    console.log('Test 3: Embedding Generation');
    const embeddingGenerator = new EmbeddingGenerator();
    const embeddings = await embeddingGenerator.generateEmbeddings(cleaned);
    
    const hasEmbeddings = embeddings.every(item => 
      Array.isArray(item.embedding) && item.embedding.length === 768
    );
    
    if (hasEmbeddings && embeddings.length > 0) {
      console.log('✅ PASSED: Embeddings generated with correct dimension (768)\n');
      passed++;
    } else {
      console.log('❌ FAILED: Embedding generation failed\n');
      failed++;
    }

    // Test 4: Sentiment Classification
    console.log('Test 4: Sentiment Classification');
    const classifier = new SentimentClassifier();
    const classified = classifier.classifySentiment(embeddings);
    
    const validLabels = ['positive', 'neutral', 'negative'];
    const hasValidLabels = classified.every(item => 
      validLabels.includes(item.sentiment.label) &&
      typeof item.sentiment.confidence === 'number' &&
      item.sentiment.confidence >= 0 && item.sentiment.confidence <= 1
    );
    
    if (hasValidLabels && classified.length > 0) {
      console.log('✅ PASSED: Classification produces valid labels and scores\n');
      passed++;
    } else {
      console.log('❌ FAILED: Classification validation failed\n');
      failed++;
    }

    // Test 5: Sentiment Synthesis
    console.log('Test 5: Sentiment Synthesis');
    const synthesizer = new SentimentSynthesizer();
    const synthesis = synthesizer.synthesizeSentiment(classified);
    
    const hasSummary = synthesis.summary && synthesis.summary.total_samples > 0;
    const hasDistribution = synthesis.distribution && Object.keys(synthesis.distribution).length > 0;
    const hasInsights = Array.isArray(synthesis.insights) && synthesis.insights.length > 0;
    
    if (hasSummary && hasDistribution && hasInsights) {
      console.log('✅ PASSED: Synthesis produces valid summary and insights\n');
      passed++;
    } else {
      console.log('❌ FAILED: Synthesis validation failed\n');
      failed++;
    }

    // Test 6: Visualization
    console.log('Test 6: Visualization');
    const visualizer = new Visualizer();
    await visualizer.generateVisualizations(synthesis);
    
    console.log('✅ PASSED: Visualizations generated successfully\n');
    passed++;

    // Test 7: Utility Functions
    console.log('Test 7: Utility Functions');
    
    // Test cosine similarity
    const vec1 = [1, 0, 0];
    const vec2 = [1, 0, 0];
    const similarity = embeddingGenerator.cosineSimilarity(vec1, vec2);
    
    if (Math.abs(similarity - 1.0) < 0.01) {
      console.log('✅ PASSED: Cosine similarity calculation correct\n');
      passed++;
    } else {
      console.log('❌ FAILED: Cosine similarity validation failed\n');
      failed++;
    }

    // Test 8: Distribution Calculation
    console.log('Test 8: Distribution Analysis');
    const distribution = classifier.getSentimentDistribution(classified);
    
    const totalMatches = distribution.positive + distribution.neutral + distribution.negative === distribution.total;
    
    if (totalMatches && distribution.total === classified.length) {
      console.log('✅ PASSED: Distribution calculation is accurate\n');
      passed++;
    } else {
      console.log('❌ FAILED: Distribution calculation failed\n');
      failed++;
    }

  } catch (error) {
    console.error('❌ Test execution error:', error.message);
    failed++;
  }

  // Print test summary
  console.log('\n' + '='.repeat(50));
  console.log('TEST SUMMARY');
  console.log('='.repeat(50));
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`Total: ${passed + failed}`);
  console.log('='.repeat(50) + '\n');

  return failed === 0;
}

// Run tests
const success = await runTests();
process.exit(success ? 0 : 1);
