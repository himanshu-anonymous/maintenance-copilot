# Readiness Assistant — Progress & Verification Log

## Product Summary
"The right maintenance knowledge, for the right equipment, at the moment a fault occurs, with evidence behind every recommendation."
Target category: Centrifugal pump + induction motor (P-101, M-104, etc.)
Synthetic demo data notice: "Demo with synthetic data. Not for real safety decisions."

---

## Phase 0: Scaffold & Gemini Verification

### 1. Gemini / Gemma API Verification Record
Real API verification executed against Google Generative Language API endpoint `https://generativelanguage.googleapis.com/v1beta/`:

- **Primary Model**: `models/gemma-4-26b-a4b-it` (Verified active and responsive)
- **Fallback Model**: `models/gemma-4-31b-it` (Verified active for `generateContent`)
- **Thinking Configuration (`thinkingConfig`)**:
  - Tested: `thinkingConfig: {"thinkingBudget": 0}` and `{"thinkingBudget": 100}`
  - Result: Returned HTTP 400 (`Thinking budget is not supported for this model.`).
  - **Verified Behavior**: Do not send `thinkingConfig` to Gemma 4 models. Gemma 4 emits internal reasoning parts marked with `'thought': True`. The API client filters out chunks with `thought: True` so only grounded user-facing diagnosis text reaches the technician.
- **JSON Output**:
  - Config: `generationConfig: {"responseMimeType": "application/json"}`
  - Verified working without errors.
- **Streaming Format**:
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/{model}:streamGenerateContent?key={key}&alt=sse`
  - Protocol: Server-Sent Events (SSE) emitting `data: { ... }` chunks containing candidate parts.
  - Verified working with `gemma-4-26b-a4b-it`.

### 2. Services Architecture (Docker Compose)
- **backend**: Python 3.11-slim, FastAPI, uvicorn, async httpx HTTP/2 client, SQLAlchemy SQLite, redis-py asyncio, pydantic v2. (Port 8000)
- **redis**: `redis:7-alpine`, maxmemory 128mb, LRU eviction, password protected. (Internal port 6379, host port 6381)
- **dashboard**: Multi-stage Docker build, Vite + React + Tailwind + Creative Tim UI components + @xyflow/react, served via Nginx on port 80 (host port 3000).
- **neo4j** (profile: `graph`): `neo4j:5-community`, heap max 512m, optional mirror writer.

### Phase 0 ACCEPT Checks
- [x] `docker compose up -d` healthy across all core services (`readiness-backend`, `readiness-redis`, `readiness-dashboard`)
- [x] `GET /api/health` reports status 200 with `sqlite: healthy`, `redis: healthy`, `gemini: healthy`
- [x] Pytest suite passes (`test_health_endpoint`, `test_root_notice`)

---

## Phase 1: Synthetic Knowledge Pack
*In progress...*
