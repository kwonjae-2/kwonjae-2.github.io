#!/usr/bin/env python3
"""
Weekly Digest Article Collector
Collects articles from various sources for SRE and Observability topics
"""

import feedparser
import json
import requests
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import re
from anthropic import Anthropic


class ArticleCollector:
    """Collects articles from RSS feeds and various sources"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        self.articles = []
        self.sources = {
            'sreweekly': 'https://sreweekly.com/feed/',
            'geeknews': 'https://news.hada.io/rss/news',
            'opentelemetry': 'https://opentelemetry.io/blog/index.xml',
            # Vendor blogs
            'grafana': 'https://grafana.com/blog/index.xml',
            'honeycomb': 'https://www.honeycomb.io/feed',
        }

        # Initialize Anthropic client if API key is provided
        self.anthropic_client = None
        if anthropic_api_key:
            self.anthropic_client = Anthropic(api_key=anthropic_api_key)
            print("✓ Claude AI integration enabled")

        # Load previously published article URLs to avoid duplicates
        self.published_urls = self._load_published_urls()

    def _load_published_urls(self) -> set:
        """Load URLs from previously published posts to avoid duplicates"""
        published_urls = set()
        posts_dir = Path(__file__).parent.parent / '_posts'

        if not posts_dir.exists():
            return published_urls

        # Read all weekly digest posts
        for post_file in posts_dir.glob('*-weekly-*.md'):
            try:
                with open(post_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract URLs using regex
                    urls = re.findall(r'https?://[^\s\)]+', content)
                    published_urls.update(urls)
            except Exception as e:
                print(f"Warning: Could not read {post_file}: {e}")

        if published_urls:
            print(f"✓ Loaded {len(published_urls)} URLs from previous posts to avoid duplicates")

        return published_urls

    def collect_from_rss(self, name: str, url: str, days_back: int = 7, max_entries: int = 50) -> List[Dict]:
        """Collect articles from an RSS feed, expanding to older articles if needed"""
        try:
            feed = feedparser.parse(url)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            articles = []
            recent_articles = []
            older_articles = []

            # Process more entries to have a larger pool
            for entry in feed.entries[:max_entries]:
                link = entry.get('link', '')

                # Skip if already published
                if link in self.published_urls:
                    continue

                # Parse the published date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6])

                if pub_date:
                    article = {
                        'title': entry.get('title', 'No Title'),
                        'link': link,
                        'source': name,
                        'published': pub_date.strftime('%Y-%m-%d'),
                        'description': self._clean_description(entry.get('summary', '')),
                        'pub_date_obj': pub_date,  # Keep for sorting
                    }

                    # Separate recent and older articles
                    if pub_date >= cutoff_date:
                        recent_articles.append(article)
                    else:
                        older_articles.append(article)

            # Combine: prefer recent articles, but include older ones if needed
            articles = recent_articles + older_articles

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

    def collect_all(self, days_back: int = 7) -> List[Dict]:
        """Collect articles from all sources"""
        all_articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Collect from RSS feeds
        for name, url in self.sources.items():
            print(f"Collecting from {name}...")
            articles = self.collect_from_rss(name, url, days_back, max_entries=50)

            # Count recent vs older articles
            recent = sum(1 for a in articles if a.get('pub_date_obj') and a['pub_date_obj'] >= cutoff_date)
            older = len(articles) - recent

            all_articles.extend(articles)
            if older > 0:
                print(f"  Found {len(articles)} articles ({recent} recent, {older} older)")
            else:
                print(f"  Found {len(articles)} recent articles")

        # Sort by published date (most recent first)
        all_articles.sort(key=lambda x: x.get('pub_date_obj', datetime.min), reverse=True)

        # Remove pub_date_obj before returning (used only for sorting)
        for article in all_articles:
            article.pop('pub_date_obj', None)

        return all_articles

    def filter_by_keywords(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """Filter articles by keywords in title or description"""
        filtered = []
        for article in articles:
            text = f"{article['title']} {article['description']}".lower()
            if any(keyword.lower() in text for keyword in keywords):
                filtered.append(article)
        return filtered

    def select_top_articles_with_ai(self, articles: List[Dict], top_n: int = 5) -> List[Dict]:
        """Use Claude AI to select the most valuable articles for SRE/Observability professionals"""
        if not self.anthropic_client:
            print("⚠️  Claude AI not configured. Falling back to simple selection.")
            return articles[:top_n]

        print(f"\n🤖 Using Claude AI to analyze {len(articles)} articles...")

        # Prepare articles list for Claude
        articles_text = "\n\n".join([
            f"Article {i+1}:\nTitle: {article['title']}\nSource: {article['source']}\nDate: {article['published']}\nDescription: {article['description']}\nURL: {article['link']}"
            for i, article in enumerate(articles[:30])  # Limit to 30 to avoid token limits
        ])

        prompt = f"""You are an expert in SRE (Site Reliability Engineering) and Observability.
Your task is to analyze the following articles and select the TOP {top_n} most valuable articles for SRE and Observability professionals.

Consider these criteria:
1. **Practical Value**: Does it provide actionable insights or real-world solutions?
2. **Innovation**: Does it introduce new tools, techniques, or perspectives?
3. **Relevance**: Is it directly relevant to SRE/Observability practitioners?
4. **Impact**: Will it help improve system reliability, monitoring, or incident response?
5. **Technical Depth**: Does it go beyond surface-level content?

Articles to analyze:

{articles_text}

Please respond in JSON format with the following structure:
{{
  "selected_articles": [
    {{
      "article_number": 1,
      "reasoning": "Brief explanation of why this article is valuable (2-3 sentences)"
    }}
  ]
}}

Select exactly {top_n} articles and order them by importance (most important first)."""

        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Parse JSON response
            selection = json.loads(response_text)

            # Extract selected articles
            selected = []
            for item in selection['selected_articles']:
                article_idx = item['article_number'] - 1
                if 0 <= article_idx < len(articles):
                    article = articles[article_idx].copy()
                    article['ai_reasoning'] = item['reasoning']
                    selected.append(article)

            print(f"✓ Claude AI selected {len(selected)} articles")
            return selected

        except Exception as e:
            print(f"⚠️  Error using Claude AI: {str(e)}")
            print("   Falling back to simple selection...")
            return articles[:top_n]

    def generate_article_summary_with_ai(self, article: Dict) -> Dict[str, str]:
        """Use Claude AI to generate a summary and key points for an article"""
        if not self.anthropic_client:
            return {
                'summary': article['description'],
                'key_points': [
                    'Key insight from the article',
                    'Important technical detail',
                    'Practical application or takeaway'
                ]
            }

        prompt = f"""Analyze this article about SRE/Observability and provide:
1. A concise 2-3 sentence summary focusing on the main value proposition
2. Three specific, actionable key points

Article:
Title: {article['title']}
Source: {article['source']}
Description: {article['description']}

Respond in JSON format:
{{
  "summary": "2-3 sentence summary here",
  "key_points": [
    "Specific key point 1",
    "Specific key point 2",
    "Specific key point 3"
  ]
}}"""

        try:
            message = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text
            return json.loads(response_text)

        except Exception as e:
            print(f"⚠️  Error generating summary for '{article['title']}': {str(e)}")
            return {
                'summary': article['description'],
                'key_points': [
                    'Key insight from the article',
                    'Important technical detail',
                    'Practical application or takeaway'
                ]
            }

    def save_to_file(self, articles: List[Dict], filename: str):
        """Save collected articles to JSON file"""
        output_dir = Path(__file__).parent / 'output'
        output_dir.mkdir(exist_ok=True)

        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(articles)} articles to {filepath}")

    def generate_markdown_draft(self, articles: List[Dict], top_n: int = 5, use_ai: bool = True):
        """Generate a draft markdown post from top articles"""
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}-weekly-{today.strftime('%Y%m%d')}.md"

        # Use AI to select and analyze articles if available
        if use_ai and self.anthropic_client:
            print("\n🤖 Using Claude AI to select and analyze articles...")
            selected = self.select_top_articles_with_ai(articles, top_n)

            # Generate summaries for each selected article
            print("\n📝 Generating summaries for selected articles...")
            for article in selected:
                summary_data = self.generate_article_summary_with_ai(article)
                article['ai_summary'] = summary_data['summary']
                article['ai_key_points'] = summary_data['key_points']
        else:
            # Fallback to simple selection
            selected = articles[:top_n]

        markdown = f"""---
title: "Weekly - {today.strftime('%B %d, %Y')}"
layout: post
date: {today.strftime('%Y-%m-%d')} 10:00:00 +0900
category: weekly
tags: [SRE, Observability, Weekly]
author: kwonjaelee
description: "Top {len(selected)} articles on SRE and Observability from this week"
---

Welcome to this week's edition! Here are the most valuable articles on SRE, Observability, and Infrastructure Engineering.

## 📚 This Week's Picks

"""

        for i, article in enumerate(selected, 1):
            # Use AI-generated summary if available, otherwise use description
            summary = article.get('ai_summary', article['description'])
            key_points = article.get('ai_key_points', [
                'Key insight from the article',
                'Important technical detail',
                'Practical application or takeaway'
            ])

            markdown += f"""### {i}. [{article['title']}]({article['link']})
**Source:** {article['source']} | **Date:** {article['published']}

{summary}

**Key Points:**
"""
            for point in key_points:
                markdown += f"- {point}\n"

            markdown += "\n---\n\n"

        markdown += """## 🔗 Resources

- [SRE Weekly](https://sreweekly.com/) - Your weekly dose of SRE news
- [GeekNews](https://news.hada.io/) - Korean tech news aggregator
- [OpenTelemetry Blog](https://opentelemetry.io/blog/)

---

*Have an article suggestion? Feel free to reach out via [email](mailto:kwonjae13@gmail.com) or leave a comment below!*
"""

        # Save to _posts directory for automatic publishing
        posts_dir = Path(__file__).parent.parent / '_posts'
        posts_dir.mkdir(exist_ok=True)

        filepath = posts_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"\n✓ Generated post: {filepath}")
        if use_ai and self.anthropic_client:
            print("  ✓ AI-powered selection and analysis complete!")

        return filepath


def main():
    """Main function"""
    print("=" * 60)
    print("Weekly Digest Article Collector with Claude AI")
    print("=" * 60)

    # Get API key from environment variable
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("⚠️  Warning: ANTHROPIC_API_KEY not found in environment")
        print("   AI features will be disabled. Set ANTHROPIC_API_KEY to enable.")

    collector = ArticleCollector(anthropic_api_key=api_key)

    # Collect articles from the last 7 days (but include older if needed)
    print("\n📡 Collecting articles from RSS feeds...")
    print("   (Including older articles if recent ones are insufficient)")
    articles = collector.collect_all(days_back=7)
    print(f"\n✓ Total articles collected: {len(articles)}")

    if len(articles) == 0:
        print("\n⚠️  No articles found. Check your RSS feeds or date range.")
        return

    # Filter by relevant keywords
    keywords = [
        'SRE', 'observability', 'monitoring', 'alerting',
        'kubernetes', 'prometheus', 'grafana', 'opentelemetry',
        'incident', 'postmortem', 'reliability', 'performance',
        'tracing', 'metrics', 'logging', 'eBPF', 'distributed',
        'microservices', 'cloud native', 'telemetry'
    ]

    print("\n🔍 Filtering by SRE/Observability keywords...")
    filtered = collector.filter_by_keywords(articles, keywords)
    print(f"✓ Articles matching keywords: {len(filtered)}")

    if len(filtered) == 0:
        print("\n⚠️  No articles matched the keywords. Using all articles.")
        filtered = articles
    elif len(filtered) < 10:
        print(f"⚠️  Only {len(filtered)} articles found - may include older content")

    # Save collected articles
    today = datetime.now().strftime('%Y%m%d')
    collector.save_to_file(filtered, f'articles_{today}.json')

    # Generate markdown post with AI
    print("\n" + "=" * 60)
    if filtered:
        filepath = collector.generate_markdown_draft(filtered, top_n=5, use_ai=bool(api_key))
        print("=" * 60)
        print(f"\n✅ Weekly digest post created successfully!")
        print(f"📄 File: {filepath}")
        if api_key:
            print("🤖 Claude AI analyzed and selected the best articles")
        print("🔄 Duplicates from previous posts: EXCLUDED")
        print("\nNext: Commit and push to publish on Saturday")
    else:
        print("\n⚠️  No articles found. Try adjusting the date range or keywords.")


if __name__ == '__main__':
    main()
