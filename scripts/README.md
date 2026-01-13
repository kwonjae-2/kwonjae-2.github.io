# Weekly Automation Scripts

This directory contains scripts to automate the collection and preparation of Weekly posts using **Claude AI**.

## Features

✨ **AI-Powered Curation**: Claude AI analyzes articles and selects the most valuable content
📊 **Multi-Source Collection**: Aggregates from SRE Weekly, GeekNews, OpenTelemetry, and more
🤖 **Fully Automated**: Generates complete blog posts ready to publish
📝 **Smart Summaries**: AI-generated summaries and key points for each article

## Setup

### 1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 2. Set up Anthropic API Key

**For local testing:**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
ANTHROPIC_API_KEY=your_api_key_here
```

Get your API key from: https://console.anthropic.com/

**For GitHub Actions:**
1. Go to your repository Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Name: `ANTHROPIC_API_KEY`
4. Value: Your Anthropic API key from https://console.anthropic.com/

## Scripts

### collect_articles.py

Collects articles from RSS feeds and uses Claude AI to select and analyze the best content.

**Usage:**
```bash
# With AI (requires ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=your_key_here
python collect_articles.py

# Without AI (falls back to simple selection)
python collect_articles.py
```

**What it does:**

1. **Collects** articles from RSS feeds:
   - SRE Weekly
   - GeekNews (news.hada.io)
   - OpenTelemetry Blog
   - Grafana Blog
   - Honeycomb Blog
   - Anthropic Engineering Blog
   - Hacker News (Y Combinator)
   - Lenny's Newsletter (Product, Growth, AI)

2. **Filters** by SRE/Observability keywords

3. **AI Analysis** (if API key is available):
   - Claude AI evaluates each article for:
     - Practical value
     - Innovation
     - Relevance to SRE professionals
     - Technical depth
     - Real-world impact
   - Selects top 5 most valuable articles
   - Generates concise summaries
   - Extracts key points

4. **Generates** a complete blog post in `_posts/` directory

**Output:**
- `_posts/YYYY-MM-DD-weekly-YYYYMMDD.md` - Ready-to-publish blog post
- `scripts/output/articles_YYYYMMDD.json` - All collected articles (backup)

## How AI Selection Works

Claude AI uses these criteria to select articles:

1. **Practical Value**: Actionable insights and real-world solutions
2. **Innovation**: New tools, techniques, or perspectives
3. **Relevance**: Direct relevance to SRE/Observability practitioners
4. **Impact**: Helps improve reliability, monitoring, or incident response
5. **Technical Depth**: Goes beyond surface-level content

## Adding New RSS Sources

Edit `collect_articles.py` and add new feeds to the `sources` dictionary:

```python
self.sources = {
    'sreweekly': 'https://sreweekly.com/feed/',
    'anthropic': 'https://raw.githubusercontent.com/conoro/anthropic-engineering-rss-feed/main/anthropic_engineering_rss.xml',
    'your_source': 'https://example.com/feed.xml',
}
```

## Automation with GitHub Actions

### Fully Automated Weekly Process

**Every Friday at 9 PM KST:**
1. GitHub Actions runs `collect_articles.py`
2. Claude AI analyzes and selects top 5 articles
3. AI generates summaries and key points
4. Complete blog post is committed to `_posts/`
5. GitHub Pages automatically publishes on Saturday

**No manual intervention required!** 🎉

### Manual Trigger

You can also trigger the workflow manually:
1. Go to Actions tab in GitHub
2. Select "Weekly Digest - Collect and Publish"
3. Click "Run workflow"

## Workflow Schedule

- **Friday 9 PM KST**: Auto-collect and generate post
- **Saturday**: GitHub Pages automatically publishes
- Post appears on https://kwonjae-2.github.io/weekly/

## Troubleshooting

**Issue**: No articles collected
**Solution**: Check RSS feed URLs, verify they're accessible

**Issue**: AI not working
**Solution**: Verify `ANTHROPIC_API_KEY` is set in GitHub Secrets

**Issue**: Articles not filtered well
**Solution**: Adjust keywords in `collect_articles.py` line 347

## Architecture

```
RSS Feeds → Collect → Filter by Keywords → Claude AI Analysis
                                              ↓
                                         Select Top 5
                                              ↓
                                    Generate Summaries
                                              ↓
                                      Create Blog Post
                                              ↓
                                    Commit to _posts/
                                              ↓
                                   GitHub Pages Publish
```
