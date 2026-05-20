"""
Trend Scout — GitHub trending explorer with insights.

Run: uvicorn main:app --reload --port 8000
Docs: README.md
"""

__version__ = "3.0.0"

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import httpx, os, re, time
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    pass

def _read_env_file_token() -> str:
    path = BASE_DIR / ".env"
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip().strip("\r")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.strip() == "GITHUB_TOKEN":
            return val.strip().strip('"').strip("'").strip("\r")
    return ""

def load_github_token() -> str:
    # .env file wins over shell env (avoids bad GITHUB_TOKEN overrides → 401)
    token = _read_env_file_token()
    if not token:
        token = (os.getenv("GITHUB_TOKEN") or "").strip().strip("\r")
    return token

def get_github_token() -> str:
    return load_github_token()

app = FastAPI(title="Trend Scout API", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
CACHE: dict = {}
CACHE_TTL = 300

LANG_COLORS = {
    "Python":"#3572A5","JavaScript":"#f1e05a","TypeScript":"#2b7489",
    "Rust":"#dea584","Go":"#00ADD8","C++":"#f34b7d","C":"#555555",
    "Java":"#b07219","Kotlin":"#A97BFF","Swift":"#F05138",
    "Ruby":"#701516","PHP":"#4F5D95","C#":"#178600","Shell":"#89e051",
    "Zig":"#ec915c","Lua":"#000080","Scala":"#c22d40","Dart":"#00B4AB",
}

CATEGORY_RULES = [
    ("AI/ML",      r"llm|gpt|\bai\b|\bml\b|deep.?learn|neural|diffusion|transformer|inference|embedding|rag|agent|vision"),
    ("Security",   r"security|vuln|pentest|exploit|cve|scan|malware|crypto(?!currency)|auth|zero.?day|ctf"),
    ("Infra",      r"k8s|kubernetes|docker|terraform|helm|infra|cloud|devops|ci.?cd|ansible|observ|monitor|prometheus"),
    ("Data",       r"\bsql\b|etl|\bdata\b|pipeline|polars|duckdb|spark|warehouse|analytics|arrow|parquet|clickhouse"),
    ("Web",        r"react|vue|svelte|next\.?js|nuxt|frontend|\bcss\b|\bhtml\b|browser|\bui\b|component|tailwind|astro"),
]

def guess_category(repo: dict) -> str:
    txt = (" ".join(repo.get("topics", [])) + " " + (repo.get("description") or "")).lower()
    for cat, pattern in CATEGORY_RULES:
        if re.search(pattern, txt):
            return cat
    return "Dev Tools"

STOPWORDS = {
    "the","and","for","with","from","this","that","your","you","are","was","was","into",
    "using","use","based","tool","tools","library","project","simple","easy","fast","new",
    "open","source","github","api","app","web","data","code","free","lightweight","modern",
    "a","an","of","in","on","to","or","is","it","by","as","at","be","can","all","not",
    "do","de","la","le","les","des","du","une","un","et","pour","avec","sur","dans",
}

TREND_PLAYBOOK = {
    "AI/ML": [
        ("Agents & workflow orchestration", "Many repos combine LLMs, RAG, and tools — next step is production multi-agent stacks."),
        ("Local inference & edge AI", "Inference/embedding projects are rising — pressure for cheaper, private deployments."),
        ("Model eval & observability", "As model wrappers multiply, demand grows for benchmarks, tracing, and guardrails."),
    ],
    "Security": [
        ("Supply chain & SBOM", "Dependency and build-artifact security is becoming standard in CI."),
        ("AI security (prompt injection, tool abuse)", "New repos blend security with LLMs — a fast-growing subsegment."),
        ("Hardening automation for small teams", "Security-by-default tooling without a dedicated SecOps hire."),
    ],
    "Infra": [
        ("Platform engineering for SMBs", "K8s/Terraform in trends — simplified internal platforms for smaller companies."),
        ("Cost-aware observability", "Monitoring and FinOps converge as cloud bills grow."),
        ("GitOps + preview environments", "Per-PR environments as a must-have in modern stacks."),
    ],
    "Data": [
        ("Lakehouse & OLAP without Spark", "DuckDB/Polars/ClickHouse in descriptions — lighter analytics trend."),
        ("Real-time analytics pipelines", "Streaming + SQL in one stack for SaaS products."),
        ("Data quality as code", "Schema tests and data contracts in CI/CD."),
    ],
    "Web": [
        ("Full-stack in one runtime (SSR + API)", "Next/Astro/SvelteKit dominate — fewer moving parts."),
        ("Design-system components + AI", "UI libraries with hooks for generative interfaces."),
        ("Performance budgets in DX", "Tools combining Lighthouse, bundlers, and RUM in one workflow."),
    ],
    "Dev Tools": [
        ("CLI-first developer experience", "New dev tools start from the terminal and plugins."),
        ("Local dev environments as code", "Reproducible setups without heavy Docker Compose."),
        ("AI-assisted refactors in the IDE", "LSP + LLM integrations for specific languages, not generic chat."),
    ],
}

IDEA_TEMPLATES = {
    "AI/ML": [
        ("CLI to benchmark prompts on your own docs", "Lightweight eval tools beyond SaaS — signal: many RAG/agent repos."),
        ("Self-hosted gateway for multiple models with token budgets", "Teams want one API and cost caps."),
        ("Agent + human-approval template for ops tasks", "Agent trend without a ready-made safety pattern."),
    ],
    "Security": [
        ("CI plugin scanning secrets in PR forks", "High stars on security — gap in small OSS projects."),
        ("CVE dashboard for runtime-only dependencies", "Less noise than full SBOM for indie devs."),
        ("Prompt-injection playground for your chatbots", "Few free, local testing labs."),
    ],
    "Infra": [
        ("Terraform generator with cost policies", "Infra trend + FinOps pressure."),
        ("Health-check aggregator for homelab / small clusters", "Simpler than full Datadog for side projects."),
        ("Preview env template for GitHub Actions (single YAML)", "Many DevOps repos, few copy-paste starters."),
    ],
    "Data": [
        ("CSV/Parquet → DuckDB migrator with quality report", "Data repos often start with files, not warehouses."),
        ("Lightweight SQL scheduler (cron + DuckDB/Polars)", "ETL without Airflow for solo founders."),
        ("Lineage visualizer for 5–10 tables at a startup", "Pipeline clarity without an enterprise catalog."),
    ],
    "Web": [
        ("SSR + auth + edge cache starter in one deploy", "Strong web category — friction assembling pieces."),
        ("Component library with built-in dark mode & a11y", "Many UI repos, inconsistent accessibility standards."),
        ("Bundle size comparison tool across frameworks", "Devs pick stacks for performance."),
    ],
    "Dev Tools": [
        ("Shared team rule linter package", "Dev Tools dominate — no standard for small teams."),
        ("CHANGELOG generator from conventional commits + AI summary", "Fast releases in trending repos."),
        ("Watch mode for tests on touched modules only", "Local feedback loop speed is a recurring theme."),
    ],
}

def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9+.#-]{2,}", (text or "").lower()) if w not in STOPWORDS]

def build_insights(repos: list, period: str) -> dict:
    if not repos:
        return {
            "summary": "Not enough data — fetch trending results or change filters.",
            "futureTrends": [],
            "ideas": [],
            "signals": {"topCategories": [], "hotTopics": [], "topLanguages": [], "keywords": []},
        }

    cat_score: dict[str, float] = {}
    lang_score: dict[str, float] = {}
    topic_score: dict[str, float] = {}
    keyword_score: dict[str, float] = {}
    momentum = {"daily": 1.0, "weekly": 0.85, "monthly": 0.7}.get(period, 1.0)

    for r in repos:
        rank_w = (26 - r.get("rank", 26)) / 25
        star_w = min((r.get("stars") or 0) / 500, 3.0)
        weight = rank_w * (1 + star_w * 0.35) * momentum
        cat = r.get("category") or "Dev Tools"
        cat_score[cat] = cat_score.get(cat, 0) + weight
        lang = r.get("lang") or "—"
        if lang != "—":
            lang_score[lang] = lang_score.get(lang, 0) + weight
        for t in r.get("topics") or []:
            topic_score[t.lower()] = topic_score.get(t.lower(), 0) + weight
        blob = f"{r.get('desc','')} {' '.join(r.get('topics') or [])}"
        for w in _tokenize(blob):
            if len(w) < 4:
                continue
            keyword_score[w] = keyword_score.get(w, 0) + weight * 0.6

    top_cats = sorted(cat_score.items(), key=lambda x: -x[1])[:5]
    top_langs = sorted(lang_score.items(), key=lambda x: -x[1])[:5]
    hot_topics = sorted(topic_score.items(), key=lambda x: -x[1])[:12]
    hot_keywords = sorted(keyword_score.items(), key=lambda x: -x[1])[:15]

    dominant_cat = top_cats[0][0] if top_cats else "Dev Tools"
    total_w = sum(cat_score.values()) or 1
    share = top_cats[0][1] / total_w if top_cats else 0

    future: list[dict] = []
    for title, reason in TREND_PLAYBOOK.get(dominant_cat, TREND_PLAYBOOK["Dev Tools"]):
        conf = "high" if share >= 0.35 else ("medium" if share >= 0.22 else "moderate")
        future.append({
            "title": title,
            "reason": reason,
            "confidence": conf,
            "horizon": {"daily": "2–6 wks", "weekly": "1–2 mo", "monthly": "2–4 mo"}.get(period, "1–2 mo"),
            "category": dominant_cat,
        })
    for cat, score in top_cats[1:3]:
        if score / total_w < 0.12:
            continue
        extra = TREND_PLAYBOOK.get(cat, [])[:1]
        for title, reason in extra:
            future.append({
                "title": title,
                "reason": f"Secondary signal in results ({cat}, ~{int(score/total_w*100)}%). {reason}",
                "confidence": "medium",
                "horizon": {"daily": "3–8 wks", "weekly": "1–3 mo", "monthly": "3–5 mo"}.get(period, "1–3 mo"),
                "category": cat,
            })
    if hot_topics[:3]:
        topics_txt = ", ".join(t[0] for t in hot_topics[:3])
        future.insert(0, {
            "title": f"Convergence around: {topics_txt}",
            "reason": "Top topics in the current set — likely direction for upcoming repos in this window.",
            "confidence": "high" if hot_topics[0][1] >= hot_topics[-1][1] * 2 else "medium",
            "horizon": {"daily": "1–4 wks", "weekly": "2–6 wks", "monthly": "1–2 mo"}.get(period, "2–6 wks"),
            "category": dominant_cat,
        })

    ideas: list[dict] = []
    seen_titles: set[str] = set()
    for cat, _ in top_cats[:2]:
        for title, why in IDEA_TEMPLATES.get(cat, IDEA_TEMPLATES["Dev Tools"]):
            if title in seen_titles:
                continue
            seen_titles.add(title)
            signals = [f"category: {cat}"]
            if hot_topics:
                signals.append(f"topic: {hot_topics[0][0]}")
            if top_langs:
                signals.append(f"language: {top_langs[0][0]}")
            ideas.append({"title": title, "why": why, "type": cat, "signals": signals})
    high_issue = sorted(repos, key=lambda r: (r.get("openIssues") or 0) / max(r.get("stars") or 1, 1), reverse=True)
    if high_issue and (high_issue[0].get("openIssues") or 0) > 5:
        r0 = high_issue[0]
        ideas.append({
            "title": f"Better docs / onboarding for repos like \"{r0.get('name')}\"",
            "why": "High open-issues-to-stars ratio — adoption outpacing maintenance.",
            "type": "OSS maintenance",
            "signals": [f"{r0.get('owner')}/{r0.get('name')}", f"{r0.get('openIssues')} issues"],
        })
    if len(top_langs) >= 2 and top_langs[0][0] != top_langs[1][0]:
        ideas.append({
            "title": f"Bridge {top_langs[1][0]} → {top_langs[0][0]} for trending libraries",
            "why": f"Two strong languages ({top_langs[0][0]}, {top_langs[1][0]}) — niche for bindings, FFI, or ports.",
            "type": "ecosystem",
            "signals": [f"{top_langs[0][0]} vs {top_langs[1][0]}"],
        })
    if hot_keywords[:5]:
        kw = ", ".join(k[0] for k in hot_keywords[:5])
        ideas.append({
            "title": "Micro-SaaS or OSS around recurring keywords",
            "why": f"Descriptions emphasize: {kw} — narrow to one problem (CLI, dashboard, plugin).",
            "type": "niche",
            "signals": hot_keywords[:5],
        })

    period_label = {"daily": "last 24h", "weekly": "last 7 days", "monthly": "last 30 days"}.get(period, period)
    summary = (
        f"Based on {len(repos)} repos ({period_label}), **{dominant_cat}** leads "
        f"(~{int(share*100)}% signal). "
    )
    if top_langs:
        summary += f"Top language: **{top_langs[0][0]}**. "
    if hot_topics:
        summary += f"Hot topics: **{', '.join(t[0] for t in hot_topics[:4])}**."

    return {
        "summary": summary,
        "futureTrends": future[:8],
        "ideas": ideas[:10],
        "signals": {
            "topCategories": [{"name": k, "score": round(v, 2)} for k, v in top_cats],
            "hotTopics": [{"name": k, "score": round(v, 2)} for k, v in hot_topics],
            "topLanguages": [{"name": k, "score": round(v, 2)} for k, v in top_langs],
            "keywords": [{"name": k, "score": round(v, 2)} for k, v in hot_keywords[:10]],
        },
    }

def since_date(period: str) -> str:
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
    return (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

def github_headers(*, with_auth: bool = True) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "TrendScout/3.0",
    }
    if with_auth:
        token = get_github_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers

def parse_github_error(response: httpx.Response) -> str:
    try:
        msg = response.json().get("message", "")
    except Exception:
        msg = response.text[:200]
    if response.status_code == 401:
        return "Invalid GitHub token (401). Set GITHUB_TOKEN in .env."
    if response.status_code == 403:
        low = (msg or "").lower()
        if "rate limit" in low:
            return "GitHub rate limit — wait a moment or add a token in .env."
        if "bad credentials" in low:
            return "Token rejected (403) — create a new PAT at github.com/settings/tokens."
        return msg or "Access forbidden (403)."
    return msg or f"GitHub HTTP error {response.status_code}"

async def fetch_github(period: str, language: str = "") -> list:
    key = f"{period}|{language}"
    if key in CACHE and time.time() - CACHE[key]["ts"] < CACHE_TTL:
        return CACHE[key]["data"]
    q = f"created:>{since_date(period)} stars:>10"
    if language:
        q += f" language:{language}"
    params = {"q": q, "sort": "stars", "order": "desc", "per_page": 25}
    headers = github_headers()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://api.github.com/search/repositories", params=params, headers=headers)
        if r.status_code == 401 and headers.get("Authorization"):
            r = await client.get(
                "https://api.github.com/search/repositories",
                params=params,
                headers=github_headers(with_auth=False),
            )
    if r.status_code != 200:
        detail = parse_github_error(r)
        if r.status_code == 401:
            detail += " Check .env and restart uvicorn (run: unset GITHUB_TOKEN)."
        code = 429 if r.status_code == 403 and "limit" in detail.lower() else r.status_code
        raise HTTPException(code, detail)
    result = []
    for i, repo in enumerate(r.json().get("items", [])):
        lang = repo.get("language") or "—"
        stars = repo.get("stargazers_count", 0)
        topics = repo.get("topics", [])
        result.append({
            "rank": i + 1,
            "owner": repo["owner"]["login"],
            "name": repo["name"],
            "desc": repo.get("description") or "",
            "lang": lang,
            "langColor": LANG_COLORS.get(lang, "#888"),
            "stars": stars,
            "forks": repo.get("forks_count", 0),
            "todayStars": round(stars * 0.04),
            "openIssues": repo.get("open_issues_count", 0),
            "license": (repo.get("license") or {}).get("spdx_id", "—"),
            "topics": topics[:4],
            "category": guess_category(repo),
            "createdAt": repo.get("created_at", ""),
            "ghUrl": repo["html_url"],
            "avatar": repo["owner"]["avatar_url"],
        })
    CACHE[key] = {"data": result, "ts": time.time()}
    return result

@app.get("/api/trending")
async def trending(
    since: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    language: str = Query("", max_length=50),
):
    data = await fetch_github(since, language)
    insights = build_insights(data, since)
    return {
        "repos": data,
        "count": len(data),
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "insights": insights,
    }

@app.post("/api/insights")
async def insights_from_repos(payload: dict = Body(default={"repos": [], "since": "daily"})):
    repos = payload.get("repos") or []
    since = payload.get("since") or "daily"
    if since not in ("daily", "weekly", "monthly"):
        since = "daily"
    return build_insights(repos, since)

@app.get("/api/status")
async def status():
    token = get_github_token()
    shell_token = (os.getenv("GITHUB_TOKEN") or "").strip()
    file_token = _read_env_file_token()
    headers = github_headers()
    github = {"ok": False, "message": "", "authenticated": bool(token)}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get("https://api.github.com/rate_limit", headers=headers)
    if r.status_code == 200:
        github["ok"] = True
        rl = r.json().get("resources", {}).get("search", {})
    else:
        rl = {}
        github["message"] = parse_github_error(r)
    token_hint = ""
    if token:
        token_hint = f"{token[:7]}…{token[-4:]}" if len(token) > 12 else "(too short)"
    return {
        "rateLimit": rl,
        "tokenSet": bool(token),
        "tokenHint": token_hint,
        "tokenSource": ".env" if file_token else ("shell" if shell_token else "none"),
        "shellOverridesEnv": bool(shell_token and file_token and shell_token != file_token),
        "github": github,
        "cacheKeys": len(CACHE),
    }

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
