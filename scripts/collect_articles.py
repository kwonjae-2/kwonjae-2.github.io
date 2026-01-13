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
from openai import OpenAI


class ArticleCollector:
    """Collects articles from RSS feeds and various sources"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.articles = []
        self.sources = {
            'sreweekly': 'https://sreweekly.com/feed/',
            'geeknews': 'https://news.hada.io/rss/news',
            'opentelemetry': 'https://opentelemetry.io/blog/index.xml',
            # Vendor blogs
            'grafana': 'https://grafana.com/blog/index.xml',
            'honeycomb': 'https://www.honeycomb.io/feed',
            # AI & Engineering
            'anthropic': 'https://raw.githubusercontent.com/conoro/anthropic-engineering-rss-feed/main/anthropic_engineering_rss.xml',
            'hackernews': 'https://news.ycombinator.com/rss',
            'lenny': 'https://www.lennysnewsletter.com/feed',
        }

        # Initialize OpenAI client if API key is provided
        self.openai_client = None
        if openai_api_key:
            try:
                print(f"🔑 Initializing OpenAI API with API key (length: {len(openai_api_key)})")
                self.openai_client = OpenAI(api_key=openai_api_key)
                print("✓ OpenAI integration enabled")
            except Exception as e:
                print(f"❌ Failed to initialize OpenAI: {str(e)}")
                print(f"   Error type: {type(e).__name__}")
        else:
            print("⚠️  No API key provided - AI features will be disabled")

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

    def _strip_markdown_json(self, text: str) -> str:
        """Strip markdown code block formatting from JSON responses"""
        text = text.strip()
        # Remove ```json and ``` markers
        if text.startswith('```json'):
            text = text[7:]  # Remove ```json
        elif text.startswith('```'):
            text = text[3:]  # Remove ```

        if text.endswith('```'):
            text = text[:-3]  # Remove trailing ```

        return text.strip()

    def select_top_articles_with_ai(self, articles: List[Dict], min_n: int = 3, max_n: int = 10) -> List[Dict]:
        """Use OpenAI to select the most valuable articles for SRE/Observability professionals (3-10 articles)"""
        if not self.openai_client:
            print("⚠️  OpenAI not configured. Falling back to simple selection.")
            return articles[:min_n]

        print(f"\n🤖 Using OpenAI to analyze {len(articles)} articles...")

        # Prepare articles list for Claude
        articles_text = "\n\n".join([
            f"Article {i+1}:\nTitle: {article['title']}\nSource: {article['source']}\nDate: {article['published']}\nDescription: {article['description']}\nURL: {article['link']}"
            for i, article in enumerate(articles[:30])  # Limit to 30 to avoid token limits
        ])

        prompt = f"""You are a tech lead helping developers grow their skills and stay updated with industry trends.
Your task is to analyze the following articles and select between {min_n} to {max_n} most valuable articles for software developers and engineers.

**Topics to Consider** (broad developer interests):
- SRE, Observability, Monitoring, Infrastructure
- AI/ML, LLM, Machine Learning applications
- Software Engineering practices, Architecture, Design patterns
- Team culture, Developer productivity, Engineering leadership
- Backend/Frontend development, Databases, Performance
- DevOps, CI/CD, Automation, Cloud platforms
- Security, Scalability, Distributed systems
- Developer tools, Programming languages, Frameworks

**Selection Criteria** (in order of priority):
1. **Developer Growth**: Helps developers learn, improve skills, or advance their career
2. **Practical Value**: Actionable insights, real-world solutions, hands-on techniques
3. **Relevance**: Applicable to modern software development practices
4. **Innovation**: New tools, techniques, best practices, or fresh perspectives
5. **Impact**: Improves productivity, code quality, system reliability, or team effectiveness

**Important**:
- Select articles that developers would find genuinely useful or interesting
- Include diverse topics - not just SRE/Observability, but AI, development practices, team culture, etc.
- Minimum {min_n} articles, maximum {max_n} articles
- Choose the exact number based on how many articles truly meet the quality bar
- Quality over quantity - don't include mediocre articles just to reach a number

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

Order articles by importance (most important first)."""

        try:
            print("   📡 Sending request to OpenAI API...")
            response = self.openai_client.chat.completions.create(
                model="gpt-5.2",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            usage = response.usage
            print(f"   ✓ Received response from OpenAI API (usage: {usage.prompt_tokens} in, {usage.completion_tokens} out)")

            response_text = response.choices[0].message.content
            print(f"   📝 Response length: {len(response_text)} characters")

            # Strip markdown formatting and parse JSON response
            clean_json = self._strip_markdown_json(response_text)
            selection = json.loads(clean_json)

            # Extract selected articles
            selected = []
            for item in selection['selected_articles']:
                article_idx = item['article_number'] - 1
                if 0 <= article_idx < len(articles):
                    article = articles[article_idx].copy()
                    article['ai_reasoning'] = item['reasoning']
                    selected.append(article)
                    print(f"   ✓ Selected article {article_idx + 1}: {article['title'][:60]}...")

            print(f"✓ OpenAI selected {len(selected)} articles")
            return selected

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse OpenAI response as JSON: {str(e)}")
            print(f"   Response text: {response_text[:200]}...")
            print("   Falling back to simple selection...")
            return articles[:min_n]
        except Exception as e:
            print(f"❌ Error using OpenAI: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            print("   Falling back to simple selection...")
            return articles[:min_n]

    def generate_article_summary_with_ai(self, article: Dict) -> Dict[str, str]:
        """Use OpenAI to generate bilingual (Korean/English) summary and key points"""
        if not self.openai_client:
            return {
                'summary_ko': article['description'],
                'summary_en': article['description'],
                'key_points_ko': [
                    '아티클의 주요 인사이트',
                    '중요한 기술적 세부사항',
                    '실무 적용 방안'
                ],
                'key_points_en': [
                    'Key insight from the article',
                    'Important technical detail',
                    'Practical application or takeaway'
                ]
            }

        prompt = f"""Analyze this article for software developers and provide bilingual summaries (Korean and English):

Article:
Title: {article['title']}
Source: {article['source']}
Description: {article['description']}

This article could be about: SRE, Observability, AI/ML, software engineering, team culture, developer productivity, or any tech topic relevant to developers.

Provide:
1. A concise 2-3 sentence summary in KOREAN focusing on what developers will learn or gain
2. The same summary in ENGLISH
3. Three specific, actionable key points in KOREAN that developers can apply
4. The same three key points in ENGLISH

Respond in JSON format:
{{
  "summary_ko": "한글로 작성된 2-3문장 요약",
  "summary_en": "English 2-3 sentence summary",
  "key_points_ko": [
    "첫 번째 핵심 포인트",
    "두 번째 핵심 포인트",
    "세 번째 핵심 포인트"
  ],
  "key_points_en": [
    "First key point",
    "Second key point",
    "Third key point"
  ]
}}"""

        try:
            print(f"   📝 Generating bilingual summary for: {article['title'][:50]}...")
            response = self.openai_client.chat.completions.create(
                model="gpt-5.2",
                max_tokens=800,  # Increased for bilingual content
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            response_text = response.choices[0].message.content
            # Strip markdown formatting and parse JSON
            clean_json = self._strip_markdown_json(response_text)
            result = json.loads(clean_json)
            usage = response.usage
            print(f"   ✓ Summary generated ({usage.completion_tokens} tokens)")
            return result

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse summary JSON for '{article['title'][:40]}': {str(e)}")
            print(f"   Response: {response_text[:150]}...")
            return {
                'summary_ko': article['description'],
                'summary_en': article['description'],
                'key_points_ko': [
                    '아티클의 주요 인사이트',
                    '중요한 기술적 세부사항',
                    '실무 적용 방안'
                ],
                'key_points_en': [
                    'Key insight from the article',
                    'Important technical detail',
                    'Practical application or takeaway'
                ]
            }
        except Exception as e:
            print(f"❌ Error generating summary for '{article['title'][:40]}': {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            return {
                'summary_ko': article['description'],
                'summary_en': article['description'],
                'key_points_ko': [
                    '아티클의 주요 인사이트',
                    '중요한 기술적 세부사항',
                    '실무 적용 방안'
                ],
                'key_points_en': [
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

    def generate_markdown_draft(self, articles: List[Dict], min_n: int = 3, max_n: int = 10, use_ai: bool = True):
        """Generate a draft markdown post from top articles (3-10 articles)"""
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}-weekly-{today.strftime('%Y%m%d')}.md"

        # Use AI to select and analyze articles if available
        if use_ai and self.openai_client:
            print("\n🤖 Using OpenAI to select and analyze articles...")
            selected = self.select_top_articles_with_ai(articles, min_n, max_n)

            # Generate bilingual summaries for each selected article
            print("\n📝 Generating bilingual summaries for selected articles...")
            for article in selected:
                summary_data = self.generate_article_summary_with_ai(article)
                article['ai_summary_ko'] = summary_data.get('summary_ko', article['description'])
                article['ai_summary_en'] = summary_data.get('summary_en', article['description'])
                article['ai_key_points_ko'] = summary_data.get('key_points_ko', ['주요 인사이트', '기술적 세부사항', '실무 적용'])
                article['ai_key_points_en'] = summary_data.get('key_points_en', ['Key insight', 'Technical detail', 'Practical application'])
        else:
            # Fallback to simple selection
            selected = articles[:min_n]

        markdown = f"""---
title: "Weekly - {today.strftime('%B %d, %Y')}"
layout: post
date: {today.strftime('%Y-%m-%d')} 10:00:00 +0900
category: weekly
tags: [Development, Tech, Weekly]
author: kwonjaelee
description: "이번 주 개발자를 위한 {len(selected)}개의 아티클 | {len(selected)} curated articles for developers"
article_count: {len(selected)}
---

### 📚 이번 주 추천 아티클

"""

        # Korean version
        for i, article in enumerate(selected, 1):
            summary_ko = article.get('ai_summary_ko', article['description'])
            key_points_ko = article.get('ai_key_points_ko', [
                '아티클의 주요 인사이트',
                '중요한 기술적 세부사항',
                '실무 적용 방안'
            ])

            markdown += f"""#### {i}. [{article['title']}]({article['link']})
**출처:** {article['source']} | **날짜:** {article['published']}

{summary_ko}

**핵심 포인트:**
"""
            for point in key_points_ko:
                markdown += f"- {point}\n"

            markdown += "\n"

        markdown += """---

### 📚 This Week's Picks

"""

        # English version
        for i, article in enumerate(selected, 1):
            summary_en = article.get('ai_summary_en', article['description'])
            key_points_en = article.get('ai_key_points_en', [
                'Key insight from the article',
                'Important technical detail',
                'Practical application or takeaway'
            ])

            markdown += f"""#### {i}. [{article['title']}]({article['link']})
**Source:** {article['source']} | **Date:** {article['published']}

{summary_en}

**Key Points:**
"""
            for point in key_points_en:
                markdown += f"- {point}\n"

            markdown += "\n"

        markdown += """---

## 🔗 Sources

Articles curated from various tech blogs and communities including SRE Weekly, GeekNews, OpenTelemetry, Grafana, and more.

---

*아티클 제안이 있으시면 [이메일](mailto:kwonjae13@gmail.com)로 연락주시거나 댓글을 남겨주세요!*

*Have an article suggestion? Feel free to reach out via [email](mailto:kwonjae13@gmail.com) or leave a comment below!*
"""

        # Save to _posts directory for automatic publishing
        posts_dir = Path(__file__).parent.parent / '_posts'
        posts_dir.mkdir(exist_ok=True)

        filepath = posts_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"\n✓ Generated post: {filepath}")
        if use_ai and self.openai_client:
            print("  ✓ AI-powered selection and analysis complete!")

        return filepath


def main():
    """Main function"""
    print("=" * 60)
    print("Weekly Article Collector with OpenAI")
    print("=" * 60)

    # Get API key from environment variable
    api_key = os.environ.get('OPENAI_API_KEY')
    print(f"\n🔍 Environment check:")
    print(f"   OPENAI_API_KEY present: {bool(api_key)}")
    if api_key:
        print(f"   API key length: {len(api_key)}")
        print(f"   API key prefix: {api_key[:10]}...")
    else:
        print("⚠️  Warning: OPENAI_API_KEY not found in environment")
        print("   AI features will be disabled. Set OPENAI_API_KEY to enable.")

    collector = ArticleCollector(openai_api_key=api_key)

    # Collect articles from the last 7 days (but include older if needed)
    print("\n📡 Collecting articles from RSS feeds...")
    print("   (Including older articles if recent ones are insufficient)")
    articles = collector.collect_all(days_back=7)
    print(f"\n✓ Total articles collected: {len(articles)}")

    if len(articles) == 0:
        print("\n⚠️  No articles found. Check your RSS feeds or date range.")
        return

    # No keyword filtering - let AI select the most relevant articles
    print("\n✓ Using all collected articles (AI will select relevant ones)")
    filtered = articles

    # Save collected articles
    today = datetime.now().strftime('%Y%m%d')
    collector.save_to_file(filtered, f'articles_{today}.json')

    # Generate markdown post with AI (3-10 articles)
    print("\n" + "=" * 60)
    if filtered:
        filepath = collector.generate_markdown_draft(filtered, min_n=3, max_n=10, use_ai=bool(api_key))
        print("=" * 60)
        print(f"\n✅ Weekly digest post created successfully!")
        print(f"📄 File: {filepath}")
        if api_key:
            print("🤖 OpenAI analyzed and selected the best articles")
        print("🔄 Duplicates from previous posts: EXCLUDED")
        print("\nNext: Commit and push to publish on Saturday")
    else:
        print("\n⚠️  No articles found. Try adjusting the date range or keywords.")


if __name__ == '__main__':
    main()
