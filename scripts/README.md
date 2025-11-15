# Weekly Digest Automation Scripts

This directory contains scripts to automate the collection and preparation of Weekly Digest posts.

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Scripts

### collect_articles.py

Collects articles from various RSS feeds and sources related to SRE and Observability.

**Usage:**
```bash
python collect_articles.py
```

**What it does:**
- Collects articles from configured RSS feeds (SRE Weekly, Grafana, Honeycomb, etc.)
- Filters articles from the last 7 days
- Filters by relevant keywords (SRE, observability, monitoring, etc.)
- Saves collected articles to `output/articles_YYYYMMDD.json`
- Generates a draft markdown post in `drafts/`

**Output:**
- JSON file with all collected articles
- Draft markdown post with top 5 articles (needs manual review and editing)

## Adding New Sources

Edit `collect_articles.py` and add new RSS feeds to the `sources` dictionary:

```python
self.sources = {
    'sreweekly': 'https://sreweekly.com/feed/',
    'your_source': 'https://example.com/feed.xml',
}
```

## Manual Review Process

1. Run `collect_articles.py` to collect articles
2. Review the generated draft in `drafts/` folder
3. Select the most interesting 5 articles
4. Add key points and descriptions for each article
5. Move the edited file to `_posts/` folder
6. Commit and push to publish

## Automation with GitHub Actions

See `.github/workflows/weekly-digest.yml` for automated collection setup.
