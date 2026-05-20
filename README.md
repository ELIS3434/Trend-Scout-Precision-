# 🛰️ Trend Scout

> **Live pulse of GitHub** — a dark, Trendshift-style dashboard with trend forecasts and project ideas powered by the GitHub Search API.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 📈 **Trending repos** | Fresh repositories ranked by stars (daily / weekly / monthly) |
| 🏷️ **Auto-categories** | AI/ML, Security, Infra, Data, Web, Dev Tools — from topics & descriptions |
| 🔮 **Trend forecasts** | Where the ecosystem is likely heading based on current results |
| 💡 **Project ideas** | Actionable niches with signals (language, category, topics) |
| 🔍 **Filters & search** | Period, language, category, full-text search |
| 📤 **CSV export** | One-click export from the browser |

> ⚠️ **Note:** This is **not** official GitHub Trending — it uses the [Search API](https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-repositories). “Stars today” is **estimated** (~4% of total stars).

---

## 🖼️ Preview

```
┌─────────────────────────────────────────────────────────────┐
│  Trend Scout · KPIs · Forecasts · Project ideas             │
│  ─────────────────────────────────────────────────────────  │
│  Sidebar: period · language · category                      │
│  Table: rank · repo · lang · category · stars · topics      │
└─────────────────────────────────────────────────────────────┘
```

Run locally → **http://127.0.0.1:8000**

---

## 🚀 Quick start

### Requirements

- Python **3.10+**
- (Recommended) [GitHub Personal Access Token](https://github.com/settings/tokens) — higher Search API rate limits

### Install

```bash
git clone https://github.com/YOUR_USER/trendscout.git
cd trendscout

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # add your token
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000**

### 🔑 GitHub token (recommended)

1. Go to **Settings → Developer settings → Personal access tokens**
2. Create a classic token with `public_repo` scope (enough for search)
3. Add to `.env`:

```env
GITHUB_TOKEN=ghp_your_token_here
```

4. **Never commit** `.env` — it is listed in `.gitignore`

If you see **401 Unauthorized**:

```bash
unset GITHUB_TOKEN    # a bad shell token overrides .env
uvicorn main:app --reload --port 8000
```

Diagnostics: **http://127.0.0.1:8000/api/status**

---

## 📡 API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trending` | `GET` | Repos + insights (`since=daily\|weekly\|monthly`, `language=`) |
| `/api/insights` | `POST` | Analyze a custom repo list (`{ "repos": [], "since": "daily" }`) |
| `/api/status` | `GET` | Rate limit, token health, config source |
| `/` | `GET` | Dashboard (static) |

### Example

```bash
curl "http://127.0.0.1:8000/api/trending?since=weekly&language=Python"
```

---

## 🏗️ Project structure

```
trendscout/
├── main.py              # FastAPI · GitHub client · insights engine
├── static/
│   └── index.html       # Dashboard (vanilla JS, dark UI)
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## 🧠 How insights work

1. Fetch repos via GitHub Search (`created:>{date} stars:>10`)
2. Weight signals: rank, stars, topics, keywords from descriptions
3. Dominant category → trend playbook + idea templates
4. Output: `summary`, `futureTrends`, `ideas`, `signals`

No external LLM — fast, offline-friendly, predictable.

---

## 🛠️ Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) + [httpx](https://www.python-httpx.org/)
- **Frontend:** HTML / CSS / JS (no build step)
- **Config:** [python-dotenv](https://github.com/theskumar/python-dotenv)

---

## 🤝 Contributing

PRs welcome. For larger changes, open an issue first.

1. Fork → branch → commit
2. Run `uvicorn main:app --reload` and check UI + `/api/status`
3. Open a pull request

---

## ☕ Support

If Trend Scout saves you time spotting what’s hot on GitHub, you can buy me a coffee:

**[ko-fi.com/elis60522](https://ko-fi.com/elis60522)** · ZenGO

---

## 📄 License

[MIT](LICENSE) — use freely; respect GitHub API rate limits.

---

<p align="center">
  <sub>Built with ☕ and curiosity about what’s rising on GitHub today.</sub><br>
  <sub><a href="https://ko-fi.com/elis60522">Support on Ko-fi</a></sub>
</p>
