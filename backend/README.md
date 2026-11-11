# goodnews backend

FastAPI + Pydantic v2 + LangGraph + Neo4j + Scrapy/trafilatura backend for the
goodnews MVP. Python is pinned to **3.11.6** for this project.

The root `.env` is loaded automatically by `app/core/config.py`; never commit
it. See the repository-root `.env.example` for every supported variable.

## Layout

| Path | Responsibility |
|------|----------------|
| `app/api/v1/` | thin HTTP routes only |
| `app/services/` | use cases, search/cache/evidence orchestration |
| `app/graph/` | Pydantic LangGraph state, prompts, nodes, conditional edges, guardrails |
| `app/llm/` | the only OpenAI SDK gateway (`LLMClient`) |
| `app/knowledge_graph/` | async Neo4j driver, Cypher repository, deterministic verification, seed data |
| `app/crawler/` | Scrapy spider, scrapy-playwright fallback, trafilatura extraction |
| `app/platforms/` | Xiaohongshu / Douyin / Bilibili adapters + browser login state |
| `app/models/` | Pydantic API / LLM / state / social contracts |
| `app/db/` | SQLAlchemy 2 async engine, history and social snapshot repositories |

## Install and run (Windows)

```bat
cd /d D:\goodnews\backend
D:\Python3.11\python.exe -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
..\scripts\start-neo4j.bat
.venv\Scripts\python.exe -m scripts.seed_graph
.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8010
```

Or from the repository root: `scripts\start-backend.bat`.

## Verification

```bat
:: health + graph stats
curl.exe http://127.0.0.1:8010/api/v1/health
curl.exe http://127.0.0.1:8010/api/v1/graph/stats

:: real DeepSeek JSON-mode check
.venv\Scripts\python.exe -m scripts.check_llm

:: real five-node fact-check
curl.exe -X POST http://127.0.0.1:8010/api/v1/factcheck ^
  -H "Content-Type: application/json" ^
  -d "{\"input_type\":\"text\",\"content\":\"埃菲尔铁塔位于柏林。\",\"max_evidence_rounds\":0}"

:: tests and lint
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check app scripts tests

:: crawler standalone (static)
.venv\Scripts\python.exe -m app.crawler.runner --url https://www.python.org/about/ --output crawler-output.json

:: JS-rendered fallback (uses Windows Edge by default)
.venv\Scripts\python.exe -m app.crawler.runner --url https://quotes.toscrape.com/js/ --output crawler-output.json --playwright --browser-channel msedge

:: social platforms: Bilibili
curl.exe -X POST http://127.0.0.1:8010/api/v1/social/fetch ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://www.bilibili.com/video/BV1gHWg6GEqj\",\"max_comments\":20,\"include_replies\":true}"

:: social platforms: Xiaohongshu login helper (first run only)
..\scripts\social-login.bat xiaohongshu
```

## MVP temporary decisions / refactor points

- One synchronous LangGraph run per HTTP request. Later: queue + SSE progress.
- Scrapy runs in a short-lived child process because Twisted's reactor cannot
  restart in-process. Later: a dedicated crawler service.
- `factcheck_records.result` stores the response as JSONB for an exact history
  snapshot. Later: normalized claims/evidence tables for analytics.
- `article_embeddings` and the `vector` extension exist but are **not used**.
- Search uses public RSS (no paid API key). Later: provider adapter for a
  commercial search API.
- No authentication by explicit MVP scope.
- Neo4j graph has 41 manually seeded entities / 30 relations. Empty or
  unmapped graphs always return `insufficient`; the LLM cannot invent a
  graph-backed verdict.
- Social adapters only read public pages through platform-native browser
  requests; they do not bypass login, paywalls or captchas. Xiaohongshu needs
  a local Playwright storage state; Douyin and Bilibili work anonymously in
  the tested scenarios, with Bilibili's anonymous comment endpoint limited to
  a small set of hot top-level comments.
- `social_fetch_records` stores normalized content/comment DTOs as JSONB. No
  raw signed URLs or platform cookies are persisted.
