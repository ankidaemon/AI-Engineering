import dotenv from 'dotenv';
import { DataCollector } from './dataCollection/dataCollector.js';
import { Preprocessor } from './preprocessing/preprocessor.js';
import { EmbeddingGenerator } from './embedding/embeddingGenerator.js';
import { SentimentClassifier } from './classification/sentimentClassifier.js';
import { SentimentSynthesizer } from './synthesis/sentimentSynthesizer.js';
import { Visualizer } from './visualization/visualizer.js';

dotenv.config();

/**
 * Main entry point for the Sentiment Synthesizer pipeline
 */
async function main() {
  try {
    console.log('🚀 Starting Sentiment Synthesizer Pipeline...\n');

    // Step 1: Data Collection
    console.log('📊 Step 1: Data Collection');
    const dataCollector = new DataCollector();
    const rawData = await dataCollector.collectData();
    console.log(`✅ Collected ${rawData.length} samples\n`);

    // Step 2: Preprocessing
    console.log('🧹 Step 2: Preprocessing');
    const preprocessor = new Preprocessor();
    const cleanedData = preprocessor.preprocess(rawData);
    console.log(`✅ Cleaned and tokenized ${cleanedData.length} samples\n`);

    // Step 3: Embedding Generation
    console.log('🧠 Step 3: Embedding Generation');
    const embeddingGenerator = new EmbeddingGenerator();
    const embeddings = await embeddingGenerator.generateEmbeddings(cleanedData);
    console.log(`✅ Generated embeddings with dimension ${embeddings[0]?.embedding?.length || 768}\n`);

    // Step 4: Sentiment Classification
    console.log('🎯 Step 4: Sentiment Classification');
    const classifier = new SentimentClassifier();
    const classified = classifier.classifySentiment(embeddings);
    console.log(`✅ Classified sentiments: ${classified.length} samples\n`);

    // Step 5: Sentiment Synthesis
    console.log('📈 Step 5: Sentiment Synthesis');
    const synthesizer = new SentimentSynthesizer();
    const synthesis = synthesizer.synthesizeSentiment(classified);
    console.log('✅ Sentiment synthesis completed\n');

    // Step 6: Visualization
    console.log('📊 Step 6: Visualization');
    const visualizer = new Visualizer();
    await visualizer.generateVisualizations(synthesis);
    console.log('✅ Visualizations generated\n');

    console.log('🎉 Pipeline completed successfully!');
    console.log('Results saved to output/ directory');

  } catch (error) {
    console.error('❌ Error in pipeline:', error.message);
    process.exit(1);
  }
}

// Run the pipeline
main();
