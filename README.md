# 🤖 Agent Tools & MCP Servers Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Good First Issues](https://img.shields.io/github/issues/community/good-first-issue?label=good%20first%20issues&color=blue)](https://github.com/tarunjandra/agent-tools-mcp-hub/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
[![All Contributors](https://img.shields.io/badge/all_contributors-28-orange.svg?style=flat-square)](#-contributors)

A curated, plug-and-play collection of **AI Agent Tools**, **Model Context Protocol (MCP)** servers, and integration connectors for modern AI agents (LangChain, CrewAI, AutoGen, OpenAI Swarm).

---

## 🌟 Why This Repo?

Building AI agents requires connecting them to real-world APIs, tools, and databases. This repository provides:
- 🧩 **Zero-conflict Modular Tools**: Every tool lives in its own standalone directory (`tools/<tool-name>/`).
- ⚡ **Multi-Language Support**: Implementations in Python, TypeScript/Node.js, or Go.
- 🔌 **Universal Compatibility**: Compatible with Model Context Protocol (MCP), OpenAI Function Calling, and LangChain Tools.
- 🤝 **Beginner-Friendly Open Source**: Ideal for first-time and seasoned contributors alike.

---

## 📂 Tools & Connectors Catalog

| Tool Name | Category | Language | MCP Compatible | Description |
| :--- | :--- | :--- | :---: | :--- |
| [`duckduckgo_search`](tools/duckduckgo_search/) | Search & Web | Python | ✅ | Instant internet search tool using DuckDuckGo HTML/API |
| [`wikipedia_search`](tools/wikipedia_search/) | Search & Web | Python | ✅ | Fetch clean article extracts and summaries from Wikipedia |
| [`arxiv_search`](tools/arxiv_search/) | Search & Web | Python | ✅ | Query arXiv API for research papers, authors & abstracts |
| [`rss_feed_reader`](tools/rss_feed_reader/) | Search & Web | Python | ✅ | Parse RSS/Atom feeds and return the latest article titles, links, and summaries |
| [`crypto_price_checker`](tools/crypto_price_checker/) | Finance | Python | ✅ | Live cryptocurrency prices, 24h market trends & market caps |
| [`currency_converter`](tools/currency_converter/) | Finance | Python | ✅ | Real-time foreign exchange rate conversion |
| [`open_meteo_weather`](tools/open_meteo_weather/) | Weather | Python | ✅ | Zero-auth current weather & 7-day forecast queries |
| [`sqlite_query_runner`](tools/sqlite_query_runner/) | Database | Python | ✅ | Safely execute read-only SQL queries on local SQLite databases |
| [`slack_notifier`](tools/slack_notifier/) | Communication | Python | ✅ | Send structured alert blocks and updates to Slack channels |
| [`jwt_decoder`](tools/jwt_decoder/) | Utilities | Python | ✅ | Decode JWT tokens and inspect headers & payloads |
| [`langchain_wrapper_demo`](tools/langchain_wrapper_demo/) | AI Integration | Python | ✅ | StructuredTool wrapper integration for LangChain agents |
| [`hackernews_profile`](tools/hackernews_profile/) | Search & Web | Python | ✅ | Fetch user profile data and karma score from HackerNews |
| [`crypto_price_tracker`](tools/crypto_price_tracker/) | Finance | Python | ✅ | A tool to fetch the current price of cryptocurrencies using the CoinGecko API. |
| [`telegram_notifier`](tools/telegram_notifier/) | Communication | Python | ✅ | Sends text messages, alerts, and Markdown/HTML notifications to Telegram chats or channels via Telegram Bot API. |
| [`yahoo_finance`](tools/yahoo_finance/) | Finance | Python | ✅ | A tool to fetch current stock quotes and basic company info using Yahoo Finance. |
| [`qr_code_generator`](tools/qr_code_generator/) | Utilities | Python | ✅ | Generates QR code images from URLs or text strings and returns them as base64-encoded PNG data. |
| [`hackernews_profile_ts`](tools/hackernews_profile_ts/) | Search & Web | TypeScript | ✅ | Fetches HackerNews user profiles with karma, creation date, and submission count. |
| [`github_repo_info`](tools/github_repo_info/) | Developer Tools | Python | ✅ | Fetches public metadata for any GitHub repository — stars, forks, primary language, open issues, license, topics and description. |
| [`github_repo_stats_ts`](tools/github_repo_stats_ts/) | Developer Tools | TypeScript | ✅ | Fetches public GitHub repository statistics and recent release history via the GitHub REST API. |
| [`github_issue_pr_manager`](tools/github_issue_pr_manager/) | Developer Tools | Python | ✅ | Lists GitHub issues/PRs and creates issues/comments for repositories via GitHub REST API. |
| [`github_pr_diff`](tools/github_pr_diff/) | Developer Tools | TypeScript | ✅ | Fetch diff files and patch details for any GitHub pull request to enable automated AI code reviews. |
| [`github_pr_diff_ts`](tools/github_pr_diff_ts/) | Developer Tools | TypeScript | ✅ | Fetches pull request metadata, per-file patches, and raw unified diffs from the GitHub REST API to enable automated AI code reviews. |
| [`github_pr_code_review_diff_ts`](tools/github_pr_code_review_diff_ts/) | Developer Tools | TypeScript | ✅ | Fetches changed files and patch details for an open GitHub pull request for automated code review workflows. |
| [`jira_ticket_status_fetcher`](tools/jira_ticket_status_fetcher/) | Developer Tools | Python | ✅ | Fetch the status, summary, and description of a Jira ticket using the Jira Cloud REST API. |
| [`trello_card_creator`](tools/trello_card_creator/) | Developer Tools | Python | ✅ | Create task cards in specified Trello lists using the Trello REST API. |
| [`docker_container_status`](tools/docker_container_status/) | Developer Tools | Python | ✅ | Queries the local Docker daemon and reports container status, health, and live resource statistics. |
| [`spotify_player`](tools/spotify_player/) | Media | Python | ✅ | Fetch the currently playing track and the user's private/public playlists from Spotify. |
| [`pdf_text_extractor`](tools/pdf_text_extractor/) | Utilities | Python | ✅ | Extract plain text from local PDF files using pypdf. |
| [`public_holiday_lookup`](tools/public_holiday_lookup/) | Utilities | Python | ✅ | Retrieves public holiday dates for an ISO country code and calendar year using the free Nager.Date API. |
| [`brave_search`](tools/brave_search/) | Search & Web | Python | ✅ | Queries the Brave Search REST API for privacy-first web results with titles, URLs, snippets and freshness filters. |
| [`discord_webhook_announcer_ts`](tools/discord_webhook_announcer_ts/) | Communication | TypeScript | ✅ | Sends Discord notifications and rich embed announcements through a Discord webhook URL. |
| [`gemini_embeddings`](tools/gemini_embeddings/) | AI Integration | Python | ✅ | Generate text embeddings for semantic search using the Google Generative AI Python SDK (Gemini API) or Vertex AI. |
| [`google_custom_search`](tools/google_custom_search/) | Search & Web | Python | ✅ | Searches the web via Google's Custom Search JSON API and returns the top matching links with titles and snippets. |
| [`supabase_table_query`](tools/supabase_table_query/) | Database | TypeScript | ✅ | Query and insert rows in a Supabase Postgres table using @supabase/supabase-js. |
| [`postgres_query_runner`](tools/postgres_query_runner/) | Database | Python | ✅ | Execute parameterized, read-only SQL queries against a PostgreSQL database using psycopg2. |
| [`redis_key_value_store`](tools/redis_key_value_store/) | Database | Python | ✅ | Get and set cached values in a Redis instance with optional TTL expiration. |
| [`chromadb_vector_query`](tools/chromadb_vector_query/) | Database | Python | ✅ | Runs semantic similarity searches against a local persistent ChromaDB vector database. |
| [`telegram_bot_sender`](tools/telegram_bot_sender/) | Communication | Python | ✅ | Send agent alerts and text messages to Telegram chats using the Telegram Bot API. |
| [`twilio_sms_alert`](tools/twilio_sms_alert/) | Communication | Python | ✅ | Sends critical SMS alert notifications via the Twilio Programmable Messaging API for agent workflows. |
| [`twitter_x_post_creator_ts`](tools/twitter_x_post_creator_ts/) | Communication | TypeScript | ✅ | Create automated text posts using the X API v2. |
| [`sendgrid_email_dispatcher`](tools/sendgrid_email_dispatcher/) | Communication | Python | ✅ | Send plain-text or HTML emails to recipients using the SendGrid API. |
| [`crewai_wrapper_demo`](tools/crewai_wrapper_demo/) | Frameworks | Python | ✅ | Adapts any tool in this hub into a CrewAI tool automatically with dynamic Pydantic schemas. |
| *[Add your tool here!](CONTRIBUTING.md)* | *Any* | *Any* | *Any* | *Submit a pull request in 15 minutes!* |

---

## 🚀 Quick Start: Using a Tool

### Python Example
```python
import sys
sys.path.append("tools/duckduckgo_search")
from tool import search_duckduckgo

results = search_duckduckgo(query="Model Context Protocol Specification", max_results=3)
print(results)
```

### TypeScript / MCP Example
```bash
cd tools/hackernews_profile_ts
npm install
npm run build
npm start
```

---

## 🤝 How to Contribute (Easy 15-Minute Guide)

We welcome all contributions! Whether you want to add an API wrapper, a new database connector, or fix documentation:

1. **Fork** this repository.
2. Pick an open issue labeled [`good first issue`](https://github.com/tarunjandra/agent-tools-mcp-hub/issues?q=label%3A%22good+first+issue%22) or propose your own.
3. Duplicate [`tools/_template/`](tools/_template/) into `tools/your_tool_name/`.
4. Implement your tool logic + add a quick `README.md`.
5. Run tests / linting: `python scripts/validate_tools.py`
6. Submit a **Pull Request**!

👉 Read our complete [**Contribution Guide (CONTRIBUTING.md)**](CONTRIBUTING.md) for step-by-step instructions.

---

## 👥 Contributors

Thanks to these wonderful people for contributing to the Agent Tools Hub!

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tarunjandra"><img src="https://avatars.githubusercontent.com/tarunjandra" width="80px;" alt="Tarun Jalandhara"/><br /><sub><b>Tarun Jalandhara</b></sub></a><br />💻 📖 🚇</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/stefannut"><img src="https://avatars.githubusercontent.com/stefannut" width="80px;" alt="Stefan Nut"/><br /><sub><b>Stefan Nut</b></sub></a><br />💻 🔌</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/govardhanreddyg2005-byte"><img src="https://avatars.githubusercontent.com/govardhanreddyg2005-byte" width="80px;" alt="Govardhan Reddy"/><br /><sub><b>Govardhan Reddy</b></sub></a><br />📖 🔌</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/gitvishal96"><img src="https://avatars.githubusercontent.com/gitvishal96" width="80px;" alt="Vishal"/><br /><sub><b>Vishal</b></sub></a><br />💻 🔍</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/baseqube-git"><img src="https://avatars.githubusercontent.com/baseqube-git" width="80px;" alt="BaseQube"/><br /><sub><b>BaseQube</b></sub></a><br />💻 🌦️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/imagenize"><img src="https://avatars.githubusercontent.com/imagenize" width="80px;" alt="Imagenize"/><br /><sub><b>Imagenize</b></sub></a><br />💻 📡</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/liangzhengtao"><img src="https://avatars.githubusercontent.com/liangzhengtao" width="80px;" alt="Liang Zhengtao"/><br /><sub><b>Liang Zhengtao</b></sub></a><br />💻 📰</td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jalaj"><img src="https://avatars.githubusercontent.com/jalaj" width="80px;" alt="jalaj"/><br /><sub><b>jalaj</b></sub></a><br />💻 📈</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/A13790618"><img src="https://avatars.githubusercontent.com/A13790618" width="80px;" alt="A13790618"/><br /><sub><b>A13790618</b></sub></a><br />💻 💬</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ace-ai-controller"><img src="https://avatars.githubusercontent.com/ace-ai-controller" width="80px;" alt="ace-ai-controller"/><br /><sub><b>ace-ai-controller</b></sub></a><br />💻 🛠️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Lucas-doyle"><img src="https://avatars.githubusercontent.com/Lucas-doyle" width="80px;" alt="Lucas-doyle"/><br /><sub><b>Lucas-doyle</b></sub></a><br />💻 📰</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/securetechs"><img src="https://avatars.githubusercontent.com/securetechs" width="80px;" alt="securetechs"/><br /><sub><b>securetechs</b></sub></a><br />💻 🐙</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Mukunt07"><img src="https://avatars.githubusercontent.com/Mukunt07" width="80px;" alt="Mukunt07"/><br /><sub><b>Mukunt07</b></sub></a><br />💻 🎵</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ayesha8087"><img src="https://avatars.githubusercontent.com/ayesha8087" width="80px;" alt="ayesha8087"/><br /><sub><b>ayesha8087</b></sub></a><br />💻 📄</td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/anirudhatalmale6-alt"><img src="https://avatars.githubusercontent.com/anirudhatalmale6-alt" width="80px;" alt="Anirudha Talmale"/><br /><sub><b>Anirudha Talmale</b></sub></a><br />💻 🔍</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/usamnang-cmyk"><img src="https://avatars.githubusercontent.com/usamnang-cmyk" width="80px;" alt="Samnang Uy"/><br /><sub><b>Samnang Uy</b></sub></a><br />💻 📡</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/golden-dragon-dev"><img src="https://avatars.githubusercontent.com/golden-dragon-dev" width="80px;" alt="golden-dragon-dev"/><br /><sub><b>golden-dragon-dev</b></sub></a><br />💻 🧠</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/JacobTurner0321"><img src="https://avatars.githubusercontent.com/JacobTurner0321" width="80px;" alt="Trung Nguyen"/><br /><sub><b>Trung Nguyen</b></sub></a><br />💻 🔍</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/jayarbrul03"><img src="https://avatars.githubusercontent.com/jayarbrul03" width="80px;" alt="jayarbrul03"/><br /><sub><b>jayarbrul03</b></sub></a><br />💻 🗄️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ImpactEngineer87"><img src="https://avatars.githubusercontent.com/ImpactEngineer87" width="80px;" alt="ImpactEngineer87"/><br /><sub><b>ImpactEngineer87</b></sub></a><br />💻 💬</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mikerdev92"><img src="https://avatars.githubusercontent.com/mikerdev92" width="80px;" alt="Mike R"/><br /><sub><b>Mike R</b></sub></a><br />💻 🔧</td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/phjpdev"><img src="https://avatars.githubusercontent.com/phjpdev" width="80px;" alt="Jean Patrick"/><br /><sub><b>Jean Patrick</b></sub></a><br />💻 🛠️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/hernandezcruzhecto"><img src="https://avatars.githubusercontent.com/hernandezcruzhecto" width="80px;" alt="hernandezcruzhecto"/><br /><sub><b>hernandezcruzhecto</b></sub></a><br />💻 🗓️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ricardo4453"><img src="https://avatars.githubusercontent.com/ricardo4453" width="80px;" alt="ricardo4453"/><br /><sub><b>ricardo4453</b></sub></a><br />💻 💬</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tomwork0427"><img src="https://avatars.githubusercontent.com/tomwork0427" width="80px;" alt="tomwork0427"/><br /><sub><b>tomwork0427</b></sub></a><br />💻 🔍</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/goldenstar9393"><img src="https://avatars.githubusercontent.com/goldenstar9393" width="80px;" alt="goldenstar9393"/><br /><sub><b>goldenstar9393</b></sub></a><br />💻 🛡️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dobrivoje0101"><img src="https://avatars.githubusercontent.com/dobrivoje0101" width="80px;" alt="Dobrivoje"/><br /><sub><b>Dobrivoje</b></sub></a><br />💻 🗄️</td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ammarhere02"><img src="https://avatars.githubusercontent.com/ammarhere02" width="80px;" alt="Ammar Khan"/><br /><sub><b>Ammar Khan</b></sub></a><br />💻 📊</td>
    </tr>
  </tbody>
</table>
<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind are welcome!

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
