# goodnews MVP architecture

## Fact-check flow

```mermaid
flowchart LR
  START([START]) --> A[fetch_article]
  A --> B[extract_claims]
  B --> C[retrieve_evidence]
  C --> D[graph_verify]
  D -->|coverage < 75% and rounds left| C
  D -->|sufficient or rounds exhausted| E[adjudicate]
  E --> END([END])
```

## Layer boundaries

```text
Vue view / components
  -> composable / Pinia
  -> src/api (single axios client)
  -> FastAPI route (no LLM / no Cypher)
  -> service (business orchestration)
  -> LangGraph node
     -> llm_client (only OpenAI SDK gateway)
     -> search / crawler
     -> graph verifier -> Neo4j repository (only Cypher)
  -> PostgreSQL history snapshot
```

## Guardrails

1. Graph verification is deterministic after candidate mapping: only exact,
   manually seeded Neo4j relations can produce `supported` / `contradicted`.
2. Empty or unmapped graph -> `insufficient`; prompts are explicitly told not
   to claim graph support.
3. Code-level guardrails (not only prompts):
   - graph contradiction cannot produce overall `true`;
   - no evidence + insufficient graph -> `insufficient_evidence`;
   - unresolved claims cannot produce overall `true`;
   - confidence is capped when the graph has no usable relation.
4. Per-claim verdicts must exist; missing ones are filled as insufficient.

## Social content + comment ingestion

```text
URL / share text
  -> platform detection (XHS / Douyin / Bilibili)
  -> Bilibili public API
     OR Playwright page + captured native XHR JSON (Douyin / XHS)
  -> normalized SocialContent + SocialComment[]
  -> PostgreSQL social_fetch_records (JSONB snapshot)
```

- Xiaohongshu may require a local login storage state; the API returns
  `platform_auth_required` instead of faking anonymous access.
- Douyin uses the page's own signed requests; no signature algorithm is copied.
- Bilibili uses public web APIs and supports nested first-level replies.
- Content metrics (views, likes, comments, shares, collects, coins, danmaku)
  are platform-specific and nullable.

## Social account sessions

```text
Login button -> visible Edge -> wait for platform login cookie
  -> save Playwright storage state + metadata
  -> adapters automatically use it on fetch
  -> status checks cookie expiry / platform auth errors
  -> logout deletes state; keepalive visits platform periodically
```

The storage state contains cookies and is git-ignored. Platform-side logout or
forced invalidation can still require a fresh QR login; auto-refresh is
best-effort, not a guarantee.

## Explicit MVP boundaries

- No login/JWT, no Celery, no multi-agent, no vector semantic dedupe.
- Redis is only a search cache.
- `article_embeddings` is created for the future but never queried.
- Search uses public RSS; a paid provider is a later adapter.
- Synchronous API; LLM streaming support exists in `llm_client` but no SSE
  endpoint yet.
