# 🤖 Agent Tools & MCP Servers Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Good First Issues](https://img.shields.io/github/issues/community/good-first-issue?label=good%20first%20issues&color=blue)](https://github.com/tarunjandra/agent-tools-mcp-hub/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
[![All Contributors](https://img.shields.io/badge/all_contributors-0-orange.svg?style=flat-square)](#-contributors)

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
| [`arxiv_search`](tools/arxiv_search/) | Search & Web | Python | ✅ | Search arXiv papers by topic and return titles, authors, abstracts, and PDFs |
| [`crypto_price_checker`](tools/crypto_price_checker/) | Finance | Python | ✅ | Live cryptocurrency prices, 24h market trends & market caps |
| [`slack_notifier`](tools/slack_notifier/) | Communication | Python | ✅ | Send structured alert blocks and updates to Slack channels |
| [`jwt_decoder`](tools/jwt_decoder/) | Utilities | Python | ✅ | Decode JWT tokens and inspect headers & payloads |
| [`langchain_wrapper_demo`](tools/langchain_wrapper_demo/) | AI Integration | Python | ✅ | StructuredTool wrapper integration for LangChain agents |
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
cd tools/github_issue_fetcher
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
