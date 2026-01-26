import fs from 'fs';
import path from 'path';

/**
 * Visualizer - Generates charts and dashboards
 * Creates data for visualization in CSV and JSON formats
 */
export class Visualizer {
  constructor() {
    this.outputDir = './output/visualizations';
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Generate all visualizations
   */
  async generateVisualizations(synthesis) {
    console.log('Generating visualizations...');
    
    this.generateSentimentDistributionChart(synthesis);
    this.generateTrendChart(synthesis);
    this.generateSourceComparisonChart(synthesis);
    this.generateTopicsChart(synthesis);
    this.generateDashboard(synthesis);

    console.log('✅ All visualizations generated');
  }

  /**
   * Generate sentiment distribution chart data
   */
  generateSentimentDistributionChart(synthesis) {
    const data = [
      {
        sentiment: 'positive',
        count: synthesis.summary.sentiment_counts.positive,
        percentage: synthesis.summary.sentiment_percentages.positive
      },
      {
        sentiment: 'neutral',
        count: synthesis.summary.sentiment_counts.neutral,
        percentage: synthesis.summary.sentiment_percentages.neutral
      },
      {
        sentiment: 'negative',
        count: synthesis.summary.sentiment_counts.negative,
        percentage: synthesis.summary.sentiment_percentages.negative
      }
    ];

    // Generate ASCII chart
    this.generateASCIIPieChart('Sentiment Distribution', data);
    
    // Save as CSV
    const csv = 'sentiment,count,percentage\n' + 
      data.map(d => `${d.sentiment},${d.count},${d.percentage}`).join('\n');
    
    this.saveVisualization('sentiment_distribution.csv', csv);
  }

  /**
   * Generate trend chart data
   */
  generateTrendChart(synthesis) {
    const temporal = synthesis.trends.temporal;
    const dates = Object.keys(temporal).sort();
    
    let csv = 'date,positive,neutral,negative,total\n';
    
    dates.forEach(date => {
      const entry = temporal[date];
      csv += `${date},${entry.positive},${entry.neutral},${entry.negative},${entry.total}\n`;
    });

    this.saveVisualization('sentiment_trends.csv', csv);
    
    // Console visualization
    console.log('\n📈 Sentiment Trend Over Time:');
    this.printTrendTable(temporal);
  }

  /**
   * Generate source comparison chart
   */
  generateSourceComparisonChart(synthesis) {
    const distribution = synthesis.distribution;
    
    let csv = 'source,positive,neutral,negative,total\n';
    
    Object.keys(distribution).forEach(source => {
      const data = distribution[source];
      csv += `${source},${data.counts.positive},${data.counts.neutral},${data.counts.negative},${data.total}\n`;
    });

    this.saveVisualization('source_comparison.csv', csv);
    
    // Console visualization
    console.log('\n📊 Sentiment by Source:');
    this.printSourceTable(distribution);
  }

  /**
   * Generate topics chart
   */
  generateTopicsChart(synthesis) {
    const topics = synthesis.topics;
    
    let csv = 'topic,frequency\n';
    topics.forEach(t => {
      csv += `${t.word},${t.count}\n`;
    });

    this.saveVisualization('top_topics.csv', csv);
    
    // Console visualization
    console.log('\n🏷️  Top Topics:');
    this.printTopicsBar(topics);
  }

  /**
   * Generate comprehensive dashboard
   */
  generateDashboard(synthesis) {
    const dashboardHTML = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentiment Synthesizer Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2.5em;
        }
        .timestamp {
            text-align: center;
            color: #999;
            margin-bottom: 30px;
            font-size: 0.9em;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .metric-card h3 {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .metric-card .value {
            font-size: 2em;
            font-weight: bold;
        }
        .metric-card.positive {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .metric-card.neutral {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }
        .metric-card.negative {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f5f5f5;
            font-weight: 600;
            color: #667eea;
        }
        tr:hover {
            background: #fafafa;
        }
        .insights-list {
            list-style: none;
            margin-top: 15px;
        }
        .insights-list li {
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
            line-height: 1.6;
        }
        .insights-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #11998e;
            font-weight: bold;
            font-size: 1.2em;
        }
        .bar {
            display: inline-block;
            height: 20px;
            background: #667eea;
            border-radius: 3px;
            margin-right: 10px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #999;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Sentiment Synthesizer Dashboard</h1>
        <div class="timestamp">Generated: ${synthesis.timestamp}</div>
        
        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card positive">
                <h3>Positive</h3>
                <div class="value">${synthesis.summary.sentiment_counts.positive}</div>
                <div>${synthesis.summary.sentiment_percentages.positive}%</div>
            </div>
            <div class="metric-card neutral">
                <h3>Neutral</h3>
                <div class="value">${synthesis.summary.sentiment_counts.neutral}</div>
                <div>${synthesis.summary.sentiment_percentages.neutral}%</div>
            </div>
            <div class="metric-card negative">
                <h3>Negative</h3>
                <div class="value">${synthesis.summary.sentiment_counts.negative}</div>
                <div>${synthesis.summary.sentiment_percentages.negative}%</div>
            </div>
            <div class="metric-card">
                <h3>Total Samples</h3>
                <div class="value">${synthesis.summary.total_samples}</div>
                <div>Average Confidence: ${synthesis.summary.average_confidence}</div>
            </div>
        </div>

        <!-- Overall Sentiment -->
        <div class="section">
            <h2>📊 Overall Analysis</h2>
            <p><strong>Overall Sentiment:</strong> <span style="color: #667eea; font-weight: bold; font-size: 1.2em;">${synthesis.summary.overall_sentiment}</span></p>
            <p style="margin-top: 10px;"><strong>Total Samples Analyzed:</strong> ${synthesis.summary.total_samples}</p>
            <p><strong>Average Prediction Confidence:</strong> ${(parseFloat(synthesis.summary.average_confidence) * 100).toFixed(1)}%</p>
        </div>

        <!-- Distribution by Source -->
        <div class="section">
            <h2>📱 Sentiment Distribution by Source</h2>
            <table>
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Positive</th>
                        <th>Neutral</th>
                        <th>Negative</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(synthesis.distribution).map(([source, data]) => `
                    <tr>
                        <td><strong>${source}</strong></td>
                        <td>${data.counts.positive} (${data.percentages.positive}%)</td>
                        <td>${data.counts.neutral} (${data.percentages.neutral}%)</td>
                        <td>${data.counts.negative} (${data.percentages.negative}%)</td>
                        <td>${data.total}</td>
                    </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <!-- Top Topics -->
        <div class="section">
            <h2>🏷️ Top Topics/Keywords</h2>
            <table>
                <thead>
                    <tr>
                        <th>Topic</th>
                        <th>Frequency</th>
                        <th>Visualization</th>
                    </tr>
                </thead>
                <tbody>
                    ${synthesis.topics.slice(0, 10).map(topic => `
                    <tr>
                        <td>${topic.word}</td>
                        <td>${topic.count}</td>
                        <td><div class="bar" style="width: ${topic.count * 20}px;"></div></td>
                    </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <!-- Key Insights -->
        <div class="section">
            <h2>💡 Key Insights</h2>
            <ul class="insights-list">
                ${synthesis.insights.map(insight => `<li>${insight}</li>`).join('')}
            </ul>
        </div>

        <!-- Trends -->
        <div class="section">
            <h2>📈 Confidence Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Minimum Confidence</td>
                        <td>${synthesis.trends.confidence_trends.min}</td>
                    </tr>
                    <tr>
                        <td>Maximum Confidence</td>
                        <td>${synthesis.trends.confidence_trends.max}</td>
                    </tr>
                    <tr>
                        <td>Average Confidence</td>
                        <td>${synthesis.trends.confidence_trends.mean}</td>
                    </tr>
                    <tr>
                        <td>Median Confidence</td>
                        <td>${synthesis.trends.confidence_trends.median}</td>
                    </tr>
                    <tr>
                        <td>Standard Deviation</td>
                        <td>${synthesis.trends.confidence_trends.std_dev}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Sentiment Synthesizer | Powered by Transformer Models</p>
        </div>
    </div>
</body>
</html>
    `;

    this.saveVisualization('dashboard.html', dashboardHTML);
  }

  /**
   * Generate ASCII pie chart
   */
  generateASCIIPieChart(title, data) {
    console.log(`\n${'='.repeat(40)}`);
    console.log(`   ${title}`);
    console.log(`${'='.repeat(40)}`);
    
    data.forEach(item => {
      const percentage = parseFloat(item.percentage);
      const barLength = Math.round(percentage / 5);
      const bar = '█'.repeat(barLength);
      console.log(`${item.sentiment.padEnd(10)} │ ${bar} ${item.percentage}% (${item.count})`);
    });
    
    console.log(`${'='.repeat(40)}`);
  }

  /**
   * Print trend table
   */
  printTrendTable(temporal) {
    const dates = Object.keys(temporal).sort();
    console.log('Date       │ Positive │ Neutral │ Negative │ Total');
    console.log('-'.repeat(55));
    
    dates.forEach(date => {
      const entry = temporal[date];
      const line = `${date} │ ${String(entry.positive).padStart(8)} │ ${String(entry.neutral).padStart(7)} │ ${String(entry.negative).padStart(8)} │ ${entry.total}`;
      console.log(line);
    });
  }

  /**
   * Print source table
   */
  printSourceTable(distribution) {
    Object.entries(distribution).forEach(([source, data]) => {
      console.log(`\n${source.toUpperCase()}`);
      console.log(`  Positive: ${data.counts.positive} (${data.percentages.positive}%)`);
      console.log(`  Neutral:  ${data.counts.neutral} (${data.percentages.neutral}%)`);
      console.log(`  Negative: ${data.counts.negative} (${data.percentages.negative}%)`);
      console.log(`  Total:    ${data.total}`);
    });
  }

  /**
   * Print topics as bar chart
   */
  printTopicsBar(topics) {
    const maxCount = Math.max(...topics.map(t => t.count));
    
    topics.slice(0, 10).forEach(topic => {
      const barLength = Math.round((topic.count / maxCount) * 30);
      const bar = '▂'.repeat(barLength);
      console.log(`  ${topic.word.padEnd(15)} ${bar} ${topic.count}`);
    });
  }

  /**
   * Save visualization to file
   */
  saveVisualization(filename, content) {
    const filepath = path.join(this.outputDir, filename);
    fs.writeFileSync(filepath, content);
    console.log(`✅ Saved: ${filename}`);
  }
}
