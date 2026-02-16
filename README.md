# Kwonjae Lee

Personal site featuring curated tech articles for developers.

## 🌐 Live Site

[kwonjae-2.github.io](https://kwonjae-2.github.io)

## 📚 Weekly

Automated weekly digest of curated tech articles covering:
- AI/ML & LLM applications
- Software engineering & architecture
- SRE & Observability
- DevOps & infrastructure
- Team culture & developer productivity

Articles are automatically collected, AI-curated, and published every Saturday at 10 AM KST.

## ✨ Features

- **Clean Design**: Minimalist and professional layout
- **Responsive**: Works on all devices
- **Fast Loading**: Optimized for speed
- **SEO Optimized**: Search engine friendly
- **Social Links**: Connect through LinkedIn, GitHub, and Email
- **Insight Hub**: Lightbulb icon links directly to current Scribbles issues
- **Adaptive Theme**: Automatically follows the visitor's light/dark preference
- **Rich Weekly Summary**: Article highlights, bilingual description (KO/EN), and client-side pagination
- **Article Highlights**: Each weekly post displays article titles as compact tags for quick scanning

## 🤖 Automation

- **Collection**: Python script fetches articles from multiple RSS feeds
- **Curation**: OpenAI GPT-5.2 selects 3-10 high-quality articles based on developer value
- **Publishing**: GitHub Actions workflow runs every Friday at 9 PM KST
- **Bilingual**: Each article includes both Korean and English summaries

## 🛠️ Tech Stack

- **Site**: Jekyll + GitHub Pages
- **Automation**: Python + GitHub Actions
- **AI**: OpenAI GPT-5.2
- **Sources**: SRE Weekly, GeekNews, OpenTelemetry, Grafana, Honeycomb, Anthropic Engineering, Hacker News, Lenny's Newsletter

## ⚙️ Configuration

Site configuration can be customized in `_config.yml`. The site now uses `dark-theme: auto` so the UI adapts to the visitor's OS preference, and the `insights_url` property drives the new lightbulb icon that links to current Scribbles issues.

## 🚀 Deployment

This site is automatically deployed to GitHub Pages whenever changes land on `gh-pages`.

## 📧 Contact

- [LinkedIn](https://linkedin.com/in/kwonjae-lee-213ba3157)
- [GitHub](https://github.com/kwonjae-2)
- [Email](mailto:kwonjae13@gmail.com)

---

Theme based on [Indigo](https://github.com/sergiokopplin/indigo) by Sérgio Kopplin
