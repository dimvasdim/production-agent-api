# Production LangGraph API

A production-style chat API built with **FastAPI** and **LangGraph**. It wraps an LLM agent with the layers a real service needs: input/output security, response caching, rate limiting, model fallback, structured logging, metrics and LangSmith tracing. It runs locally or in Docker.

It supports two LLM providers, selected with a single environment variable:

| Provider | Default primary model | Default fallback model |
|---|---|---|
| **Ollama** (local, default) | `qwen3.5:4b` | `qwen2.5:7b` |
| **Google Gemini** | `gemini-3.6-flash` | `gemini-3.5-flash-lite` |

Tested with both providers.

## How a request flows

```
POST /chat
   │
   ├─ 1. Security check ──── prompt-injection patterns → 400 if blocked
   │                          PII (email, phone, SSN, card) masked before the LLM
   ├─ 2. Cache lookup ────── hit → return immediately (model_used = "cache")
   ├─ 3. LangGraph agent ─── primary model
   │                            └─ on error → fallback model
   │                                 └─ on error → graceful apology message
   ├─ 4. Output validation ─ mask leaked PII, block harmful content / secrets
   ├─ 5. Cache store
   └─ 6. Log (JSON) + record metrics → response
```

Requests are rate-limited per client IP (default `20/minute`), and every step is traced to LangSmith when tracing is enabled.

## Project structure

```
app/
├── main.py         FastAPI app, endpoints, lifespan, rate limiter
├── agent.py        LangGraph state machine: primary → fallback → error handler
├── llm.py          Model factory: builds a Gemini or Ollama chat model
├── config.py       Settings loaded from .env via pydantic-settings
├── security.py     Injection detection, input cleaning, PII masking, output validation
├── cache.py        In-memory response cache with TTL
├── monitoring.py   JSON logger, metrics collector, request timer
└── models.py       Pydantic request/response schemas
tests/
├── test_cache.py
└── test_security.py
```

## Getting started

### Prerequisites

- Python 3.14+ and [uv](https://docs.astral.sh/uv/)
- **For Ollama:** [Ollama](https://ollama.com/) installed, with the models pulled:
  ```bash
  ollama pull qwen3.5:4b
  ollama pull qwen2.5:7b
  ```
- **For Gemini:** a [Google AI Studio](https://aistudio.google.com/) API key
- *(Optional)* a [LangSmith](https://smith.langchain.com/) API key for tracing

### Configure

```bash
cp .env.example .env
```

Then edit `.env`. To use Gemini, set `LLM_PROVIDER=google` and add your `GOOGLE_API_KEY`.

### Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The API is now at http://localhost:8000, with interactive docs at http://localhost:8000/docs.

### Run with Docker

```bash
docker compose up --build
```

When you use Ollama, the container reaches the Ollama instance on your host machine through `host.docker.internal:11434`, which is configured in `docker-compose.yml`. If the container can't connect, set `OLLAMA_HOST=0.0.0.0` on the host and restart Ollama.

## Configuration

All settings live in `app/config.py`. Each one can be overridden by an environment variable or a `.env` entry with the same name in uppercase. The precedence is OS environment > `.env` > code default.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` or `google` |
| `PRIMARY_MODEL` | *per provider* | Overrides the default primary model |
| `FALLBACK_MODEL` | *per provider* | Overrides the default fallback model |
| `GOOGLE_API_KEY` | — | Required when `LLM_PROVIDER=google` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Where Ollama is running |
| `LANGCHAIN_TRACING_V2` | `true` | Enables LangSmith tracing |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `production-api` | LangSmith project name |
| `APP_ENV` | `development` | `production` in Docker |
| `LOG_LEVEL` | `INFO` | Logging level |
| `RATE_LIMIT` | `20/minute` | Per-IP limit on `/chat` |
| `CACHE_TTL_SECONDS` | `300` | How long cached responses live |
| `MAX_RETRIES` | `3` | Retry budget for the agent / Gemini client |

To print the active configuration, run:

```bash
uv run python -m app.config
```

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a message to the agent |
| `GET` | `/health` | Health check (used by Docker) |
| `GET` | `/metrics` | Request count, error rate, latency, cache hit rate, token estimates |
| `GET` | `/cache/stats` | Cache hits, misses and entry count |

### Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is LangGraph in one sentence?", "thread_id": "demo"}'
```

```json
{
  "response": "LangGraph is a library for building stateful, multi-step LLM applications as graphs.",
  "thread_id": "demo",
  "model_used": "primary",
  "cached": false,
  "processing_time_ms": 1234.56,
  "security_notes": [],
  "timestamp": "2026-10-22T10:00:00+00:00"
}
```

Sending the same message again returns `"cached": true`. A message like `"Ignore all previous instructions..."` is rejected with a `400`.

## Testing

```bash
uv run pytest
```

Several modules also have a standalone demo you can run directly, e.g. `uv run python -m app.security`, `app.cache`, `app.agent` or `app.monitoring`.

## Production notes

This project is a learning exercise. Some components are simplified on purpose:

- **Cache and metrics are in-memory.** They reset on restart and aren't shared between instances. In a real deployment, use Redis and Prometheus.
- **Security filters are regex-based.** They catch common patterns but are not a complete defense against prompt injection.
- **Token counts are estimates** (words × 1.3), not real tokenizer counts.
- **Conversation memory isn't persisted.** `thread_id` is logged but each request is handled independently.

## Credits

Built by following [Production RAG with LangChain & Vector Databases – Full Course](https://www.youtube.com/watch?v=mHxLXzYjQRE) by freeCodeCamp, then extended with Ollama/Gemini provider switching and Docker networking for a host-side Ollama.
