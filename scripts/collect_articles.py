#!/usr/bin/env python3
"""
Weekly Digest Article Collector
Collects articles from various sources for SRE and Observability topics
"""

import feedparser
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import re


class ArticleCollector:
    """Collects articles from RSS feeds and various sources"""

    def __init__(self):
        self.articles = []
        self.sources = {
            'sreweekly': 'https://sreweekly.com/feed/',
            # Add more RSS feeds here
            'grafana': 'https://grafana.com/blog/index.xml',
            'honeycomb': 'https://www.honeycomb.io/feed',
        }

    def collect_from_rss(self, name: str, url: str, days_back: int = 7) -> List[Dict]:
        """Collect articles from an RSS feed"""
        try:
            feed = feedparser.parse(url)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            articles = []

            for entry in feed.entries[:20]:  # Limit to recent 20 entries
                # Parse the published date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6])

                # Check if article is recent
                if pub_date and pub_date >= cutoff_date:
                    article = {
                        'title': entry.get('title', 'No Title'),
                        'link': entry.get('link', ''),
                        'source': name,
                        'published': pub_date.strftime('%Y-%m-%d'),
                        'description': self._clean_description(entry.get('summary', '')),
                    }
                    articles.append(article)

            return articles
        except Exception as e:
            print(f"Error collecting from {name}: {str(e)}")
            return []

    def _clean_description(self, html_text: str) -> str:
        """Clean HTML from description"""
        # Remove HTML tags
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_text)
        # Limit to first 200 characters
        return text[:200] + '...' if len(text) > 200 else text

    def collect_from_geeknews(self, days_back: int = 7) -> List[Dict]:
        """
        Collect articles from GeekNews
        Note: GeekNews doesn't have a public API, so this is a placeholder
        You may need to implement web scraping or find an RSS feed
        """
        # Placeholder - implement actual GeekNews collection
        # You might need to use BeautifulSoup for web scraping
        print("GeekNews collection not implemented yet - requires web scraping")
        return []

    def collect_all(self, days_back: int = 7) -> List[Dict]:
        """Collect articles from all sources"""
        all_articles = []

        # Collect from RSS feeds
        for name, url in self.sources.items():
            print(f"Collecting from {name}...")
            articles = self.collect_from_rss(name, url, days_back)
            all_articles.extend(articles)
            print(f"  Found {len(articles)} articles")

        # Collect from GeekNews (if implemented)
        # geeknews_articles = self.collect_from_geeknews(days_back)
        # all_articles.extend(geeknews_articles)

        # Sort by published date
        all_articles.sort(key=lambda x: x['published'], reverse=True)

        return all_articles

    def filter_by_keywords(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filter articles by keywords in title or description"""
        filtered = []
        for article in articles:
            text = f"{article['title']} {article['description']}".lower()
            if any(keyword.lower() in text for keyword in keywords):
                filtered.append(article)
        return filtered

    def save_to_file(self, articles: List[Dict], filename: str):
        """Save collected articles to JSON file"""
        output_dir = Path(__file__).parent / 'output'
        output_dir.mkdir(exist_ok=True)

        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(articles)} articles to {filepath}")

    def generate_markdown_draft(self, articles: List[Dict], top_n: int = 5):
        """Generate a draft markdown post from top articles"""
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}-weekly-digest-{today.strftime('%Y%m%d')}.md"

        # Select top N articles (you should manually review and select)
        selected = articles[:top_n]

        markdown = f"""---
title: "Weekly Digest - {today.strftime('%B %d, %Y')}"
layout: post
date: {today.strftime('%Y-%m-%d')} 10:00:00 +0900
category: weekly
tags: [SRE, Observability, Weekly]
author: kwonjaelee
description: "Top {top_n} articles on SRE and Observability from this week"
---

Welcome to this week's edition of Weekly Digest! Here are the most interesting articles on SRE, Observability, and Infrastructure Engineering.

## 📚 This Week's Picks

"""

        for i, article in enumerate(selected, 1):
            markdown += f"""### {i}. [{article['title']}]({article['link']})
**Source:** {article['source']} | **Date:** {article['published']}

{article['description']}

**Key Points:**
- [Add key point 1]
- [Add key point 2]
- [Add key point 3]

---

"""

        markdown += """## 🔗 Resources

- [SRE Weekly](https://sreweekly.com/) - Your weekly dose of SRE news
- [GeekNews](https://news.hada.io/) - Korean tech news aggregator

---

*Have an article suggestion? Feel free to reach out via [email](mailto:kwonjae13@gmail.com) or leave a comment below!*
"""

        # Save to drafts
        output_dir = Path(__file__).parent / 'drafts'
        output_dir.mkdir(exist_ok=True)

        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"\nGenerated draft post: {filepath}")
        print(f"Please review and edit before publishing!")

        return filepath


def main():
    """Main function"""
    print("Weekly Digest Article Collector")
    print("=" * 50)

    collector = ArticleCollector()

    # Collect articles from the last 7 days
    articles = collector.collect_all(days_back=7)
    print(f"\nTotal articles collected: {len(articles)}")

    # Filter by relevant keywords
    keywords = [
        'SRE', 'observability', 'monitoring', 'alerting',
        'kubernetes', 'prometheus', 'grafana', 'opentelemetry',
        'incident', 'postmortem', 'reliability', 'performance',
        'tracing', 'metrics', 'logging', 'eBPF'
    ]

    filtered = collector.filter_by_keywords(articles, keywords)
    print(f"Articles matching keywords: {len(filtered)}")

    # Save collected articles
    today = datetime.now().strftime('%Y%m%d')
    collector.save_to_file(filtered, f'articles_{today}.json')

    # Generate markdown draft
    if filtered:
        collector.generate_markdown_draft(filtered, top_n=5)
    else:
        print("\nNo articles found. Try adjusting the date range or keywords.")


if __name__ == '__main__':
    main()
