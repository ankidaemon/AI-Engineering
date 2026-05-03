"""
Visualization module
Creates dashboards, charts, and reports
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter

logger = logging.getLogger(__name__)


class Visualizer:
    """Generates visualizations and dashboards"""
    
    def __init__(self, config):
        self.config = config
        self.output_dir = config.OUTPUT_DIR / "visualizations"
        
        # Set plotting style
        plt.style.use(config.PLOT_STYLE)
        sns.set_palette("husl")
    
    def generate_visualizations(self, synthesis: Dict[str, Any], classified: List[Dict[str, Any]]):
        """Generate all visualizations"""
        logger.info("Generating visualizations...")
        
        # Create sentiment distribution pie chart
        self._create_sentiment_distribution_chart(synthesis)
        
        # Create trend analysis
        self._create_trend_chart(synthesis)
        
        # Create source comparison
        self._create_source_comparison_chart(synthesis)
        
        # Create topics chart
        self._create_topics_chart(synthesis)
        
        # Create confidence distribution
        self._create_confidence_distribution_chart(classified)
        
        # Create HTML dashboard
        self._create_html_dashboard(synthesis, classified)
        
        # Create CSV exports
        self._create_csv_exports(synthesis, classified)
        
        logger.info("✅ All visualizations generated")
    
    def _create_sentiment_distribution_chart(self, synthesis: Dict[str, Any]):
        """Create sentiment distribution pie chart"""
        summary = synthesis['summary']
        labels = list(summary['sentiment_counts'].keys())
        sizes = list(summary['sentiment_counts'].values())
        colors = ['#d62728', '#ff7f0e', '#2ca02c']
        
        fig, ax = plt.subplots(figsize=self.config.FIGURE_SIZE)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.set_title('Sentiment Distribution', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        filepath = self.output_dir / "sentiment_distribution.png"
        plt.savefig(filepath, dpi=self.config.PLOT_DPI)
        plt.close()
        logger.info(f"✅ Saved: sentiment_distribution.png")
    
    def _create_trend_chart(self, synthesis: Dict[str, Any]):
        """Create trend analysis chart"""
        by_date = synthesis['trends']['by_date']
        
        if not by_date:
            return
        
        dates = sorted(by_date.keys())
        positives = [by_date[d]['positive'] for d in dates]
        neutrals = [by_date[d]['neutral'] for d in dates]
        negatives = [by_date[d]['negative'] for d in dates]
        
        fig, ax = plt.subplots(figsize=self.config.FIGURE_SIZE)
        ax.plot(dates, positives, marker='o', label='Positive', color='green')
        ax.plot(dates, neutrals, marker='s', label='Neutral', color='orange')
        ax.plot(dates, negatives, marker='^', label='Negative', color='red')
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Count')
        ax.set_title('Sentiment Trends Over Time', fontsize=14, fontweight='bold')
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        filepath = self.output_dir / "sentiment_trends.png"
        plt.savefig(filepath, dpi=self.config.PLOT_DPI)
        plt.close()
        logger.info(f"✅ Saved: sentiment_trends.png")
    
    def _create_source_comparison_chart(self, synthesis: Dict[str, Any]):
        """Create source comparison chart"""
        distribution = synthesis['distribution']
        
        sources = list(distribution.keys())
        positives = [distribution[s]['counts'].get('positive', 0) for s in sources]
        neutrals = [distribution[s]['counts'].get('neutral', 0) for s in sources]
        negatives = [distribution[s]['counts'].get('negative', 0) for s in sources]
        
        fig, ax = plt.subplots(figsize=self.config.FIGURE_SIZE)
        x = range(len(sources))
        width = 0.25
        
        ax.bar([i - width for i in x], positives, width, label='Positive', color='green')
        ax.bar(x, neutrals, width, label='Neutral', color='orange')
        ax.bar([i + width for i in x], negatives, width, label='Negative', color='red')
        
        ax.set_xlabel('Source')
        ax.set_ylabel('Count')
        ax.set_title('Sentiment Distribution by Source', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(sources)
        ax.legend()
        plt.tight_layout()
        
        filepath = self.output_dir / "source_comparison.png"
        plt.savefig(filepath, dpi=self.config.PLOT_DPI)
        plt.close()
        logger.info(f"✅ Saved: source_comparison.png")
    
    def _create_topics_chart(self, synthesis: Dict[str, Any]):
        """Create topics/keywords chart"""
        topics = synthesis['topics']
        
        if not topics:
            return
        
        words = [t['word'] for t in topics]
        counts = [t['count'] for t in topics]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.barh(words, counts, color='steelblue')
        ax.set_xlabel('Frequency')
        ax.set_title('Top Topics/Keywords', fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        plt.tight_layout()
        
        filepath = self.output_dir / "top_topics.png"
        plt.savefig(filepath, dpi=self.config.PLOT_DPI)
        plt.close()
        logger.info(f"✅ Saved: top_topics.png")
    
    def _create_confidence_distribution_chart(self, classified: List[Dict[str, Any]]):
        """Create confidence distribution chart"""
        confidences = [item['sentiment']['confidence'] for item in classified]
        
        fig, ax = plt.subplots(figsize=self.config.FIGURE_SIZE)
        ax.hist(confidences, bins=20, color='steelblue', edgecolor='black')
        ax.set_xlabel('Confidence')
        ax.set_ylabel('Frequency')
        ax.set_title('Prediction Confidence Distribution', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        filepath = self.output_dir / "confidence_distribution.png"
        plt.savefig(filepath, dpi=self.config.PLOT_DPI)
        plt.close()
        logger.info(f"✅ Saved: confidence_distribution.png")
    
    def _create_html_dashboard(self, synthesis: Dict[str, Any], classified: List[Dict[str, Any]]):
        """Create interactive HTML dashboard with plotly charts"""
        summary = synthesis['summary']
        distribution = synthesis['distribution']
        topics = synthesis['topics']
        insights = synthesis['insights']

        # --- plotly: sentiment distribution pie chart (loads plotly.js from CDN) ---
        sentiment_colors = {'positive': '#11998e', 'neutral': '#fa709a', 'negative': '#eb3349'}
        labels = list(summary['sentiment_counts'].keys())
        values = list(summary['sentiment_counts'].values())

        pie_fig = go.Figure(data=[go.Pie(
            labels=[l.capitalize() for l in labels],
            values=values,
            marker_colors=[sentiment_colors.get(l, '#667eea') for l in labels],
            hole=0.35,
            textinfo='label+percent',
        )])
        pie_fig.update_layout(
            title='Sentiment Distribution',
            margin=dict(l=10, r=10, t=50, b=10),
            height=350,
        )
        pie_html = pie_fig.to_html(include_plotlyjs='cdn', full_html=False)

        # --- plotly: grouped bar chart by source (reuses CDN already loaded) ---
        sources = list(distribution.keys())
        bar_fig = go.Figure()
        for sentiment in ['positive', 'neutral', 'negative']:
            bar_fig.add_trace(go.Bar(
                name=sentiment.capitalize(),
                x=sources,
                y=[distribution[s]['counts'].get(sentiment, 0) for s in sources],
                marker_color=sentiment_colors.get(sentiment, '#667eea'),
            ))
        bar_fig.update_layout(
            title='Sentiment by Source',
            barmode='group',
            margin=dict(l=10, r=10, t=50, b=10),
            height=350,
        )
        bar_html = bar_fig.to_html(include_plotlyjs=False, full_html=False)

        # --- plotly: confidence histogram ---
        confidences = [item['sentiment']['confidence'] for item in classified]
        hist_fig = px.histogram(
            x=confidences, nbins=20,
            labels={'x': 'Confidence', 'y': 'Count'},
            title='Prediction Confidence Distribution',
            color_discrete_sequence=['#667eea'],
        )
        hist_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=300)
        hist_html = hist_fig.to_html(include_plotlyjs=False, full_html=False)

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentiment Synthesizer Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        h1 {{ color: #667eea; margin-bottom: 30px; text-align: center; }}
        .timestamp {{ text-align: center; color: #999; margin-bottom: 30px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{ font-size: 0.9em; opacity: 0.9; margin-bottom: 10px; }}
        .metric-card .value {{ font-size: 2em; font-weight: bold; }}
        .metric-card.positive {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .metric-card.neutral {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }}
        .metric-card.negative {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 40px;
        }}
        .chart-card {{
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 10px;
        }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{ color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f5f5f5; font-weight: 600; color: #667eea; }}
        tr:hover {{ background: #fafafa; }}
        .insights-list {{ list-style: none; margin-top: 15px; }}
        .insights-list li {{ padding: 10px 0; padding-left: 30px; position: relative; }}
        .insights-list li:before {{ content: "✓"; position: absolute; left: 0; color: #11998e; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Sentiment Synthesizer Dashboard</h1>
        <div class="timestamp">Generated: {summary['timestamp']}</div>

        <div class="metrics-grid">
            <div class="metric-card positive">
                <h3>Positive</h3>
                <div class="value">{summary['sentiment_counts'].get('positive', 0)}</div>
                <div>{summary['sentiment_percentages'].get('positive', 0)}%</div>
            </div>
            <div class="metric-card neutral">
                <h3>Neutral</h3>
                <div class="value">{summary['sentiment_counts'].get('neutral', 0)}</div>
                <div>{summary['sentiment_percentages'].get('neutral', 0)}%</div>
            </div>
            <div class="metric-card negative">
                <h3>Negative</h3>
                <div class="value">{summary['sentiment_counts'].get('negative', 0)}</div>
                <div>{summary['sentiment_percentages'].get('negative', 0)}%</div>
            </div>
            <div class="metric-card">
                <h3>Total Samples</h3>
                <div class="value">{summary['total_samples']}</div>
                <div>Avg Confidence: {summary['average_confidence']}</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Interactive Charts</h2>
            <div class="charts-grid">
                <div class="chart-card">{pie_html}</div>
                <div class="chart-card">{bar_html}</div>
            </div>
            <div class="chart-card">{hist_html}</div>
        </div>

        <div class="section">
            <h2>📊 Overall Analysis</h2>
            <p><strong>Overall Sentiment:</strong> <span style="font-weight: bold; color: #667eea;">{summary['overall_sentiment']}</span></p>
            <p><strong>Average Confidence:</strong> {summary['average_confidence']}</p>
        </div>

        <div class="section">
            <h2>📱 Distribution by Source</h2>
            <table>
                <thead><tr><th>Source</th><th>Positive</th><th>Neutral</th><th>Negative</th><th>Total</th></tr></thead>
                <tbody>
                    {''.join([f"<tr><td>{source}</td><td>{dist['counts'].get('positive', 0)}</td><td>{dist['counts'].get('neutral', 0)}</td><td>{dist['counts'].get('negative', 0)}</td><td>{dist['total']}</td></tr>" for source, dist in distribution.items()])}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🏷️ Top Topics</h2>
            <table>
                <thead><tr><th>Topic</th><th>Frequency</th></tr></thead>
                <tbody>
                    {''.join([f"<tr><td>{t['word']}</td><td>{t['count']}</td></tr>" for t in topics[:10]])}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>💡 Key Insights</h2>
            <ul class="insights-list">
                {''.join([f"<li>{insight}</li>" for insight in insights])}
            </ul>
        </div>

        <div class="footer">
            <p>Generated by Sentiment Synthesizer | Powered by Transformers</p>
        </div>
    </div>
</body>
</html>
        """

        filepath = self.output_dir / "dashboard.html"
        with open(filepath, 'w') as f:
            f.write(html_content)

        logger.info(f"✅ Saved: dashboard.html")
    
    def _create_csv_exports(self, synthesis: Dict[str, Any], classified: List[Dict[str, Any]]):
        """Create CSV exports"""
        # Sentiment distribution
        summary = synthesis['summary']
        df_dist = pd.DataFrame({
            'sentiment': list(summary['sentiment_counts'].keys()),
            'count': list(summary['sentiment_counts'].values()),
            'percentage': list(summary['sentiment_percentages'].values())
        })
        df_dist.to_csv(self.output_dir / "sentiment_distribution.csv", index=False)
        
        # Classified results
        df_classified = pd.DataFrame([
            {
                'id': item['id'],
                'source': item['source'],
                'text': item['text'][:100],
                'sentiment': item['sentiment']['label'],
                'confidence': item['sentiment']['confidence']
            }
            for item in classified
        ])
        df_classified.to_csv(self.output_dir / "classifications.csv", index=False)
        
        logger.info(f"✅ Saved: sentiment_distribution.csv, classifications.csv")
