# NotifAI Enterprise

Multi-agent, RAG-powered WhatsApp-to-Calendar system built on Google Cloud.

## Problem

College and workplace group chats are flooded with notices: exam dates, meeting reminders, submission deadlines, event announcements. Important information gets buried under casual chatter, Hinglish messages, and voice notes. NotifAI solves this by listening to WhatsApp groups, extracting structured events with AI, and syncing them directly to Google Calendar.

## Architecture

```mermaid
graph TD
    subgraph "WhatsApp"
        WA[WhatsApp Web] --> BROKER[Node.js Broker]
        BROKER -->|HTTP POST| API
    end

    subgraph "NotifAI Enterprise (Cloud Run)"
        API[FastAPI :8080] --> ROUTER[Router / Coordinator]
        ROUTER --> RETRIEVER[Retriever Agent]
        RETRIEVER --> CHROMA[(ChromaDB)]
        ROUTER --> EXTRACTOR[Extractor Agent]
        EXTRACTOR -->|Gemini 3.5 Flash-Lite| PYD[Pydantic Schema]
        ROUTER --> VALIDATOR[Validator / Critic]
        VALIDATOR -->|max 2 retries| EXTRACTOR
        ROUTER --> SCHEDULER[Scheduler Agent]
        SCHEDULER -->|OAuth 2.0| GCAL[Google Calendar API]
        ROUTER --> TRACE[Observability Tracing]
    end

    subgraph "Observability"
        TRACE --> METRICS[/metrics endpoint]
        TRACE --> CLI[CLI Report]
    end

    subgraph "Evaluation"
        EVAL[Eval Harness] --> DATASET[52 Labeled Notices]
        DATASET --> METRICS
    end
```

### Multi-Agent Pipeline

```
Message → Router → Retriever (RAG) → Extractor (Gemini + Pydantic)
         → Validator (self-reflection, max 2 retries) → Scheduler (Calendar)
```

1. **Router**: Coordinates the workflow, delegates to sub-agents
2. **Retriever**: Searches ChromaDB for relevant context (metadata filters, top-k, relevance threshold)
3. **Extractor**: Uses Gemini 3.5 Flash-Lite with Pydantic schema for structured event extraction
4. **Validator**: Self-reflection critic — checks for hallucinations, duplicates, invalid dates, asks Extractor to retry (max 2 loops)
5. **Scheduler**: Creates Google Calendar events via OAuth 2.0

### RAG Pipeline

- **Embeddings**: Gemini `text-embedding-004` (768 dimensions)
- **Vector Store**: ChromaDB (Docker Compose), swappable behind `VectorStore` interface
- **Chunking**: Sentence-based for unstructured messages, structured chunks for events
- **Retrieval**: Top-k with cosine similarity, metadata filters (source_chat, date), relevance threshold (0.7)

## Quick Start

### Local Development (Docker Compose)

```bash
# 1. Clone and configure
git clone <repo> && cd NotifAI_Enterprise
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and Google Calendar OAuth credentials

# 2. Start services
docker compose up -d

# 3. Scan WhatsApp QR code
open http://localhost:3000

# 4. Check API health
curl http://localhost:8080/health
```

### Run Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=notifai
```

### Run Evaluation

```bash
# Mock mode (no API key needed, CI-safe)
python -m notifai.eval.runner --mock --category

# Real mode (requires GOOGLE_API_KEY)
python -m notifai.eval.runner --category

# JSON output
python -m notifai.eval.runner --json
```

### View Observability Report

```bash
python -m notifai.observability.report --traces
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Ingest a notice into the RAG pipeline |
| POST | `/query` | Run the multi-agent workflow on a message |
| GET | `/health` | Health check (RAG, Calendar, auth status) |
| GET | `/metrics` | Observability metrics + recent traces |
| GET | `/docs` | Interactive Swagger UI |

All endpoints (except `/health`) accept `X-API-Key` header for auth. Set `API_KEY` env var to enable.

## Evaluation Results

### Mock Eval (52 cases, 61 expected events)

| Metric | Value |
|--------|-------|
| Field Accuracy (title) | 90.38% |
| Field Accuracy (date) | 90.38% |
| Field Accuracy (time) | 90.38% |
| Precision | 100.00% |
| Recall | 100.00% |
| F1 Score | 100.00% |
| Hallucination Rate | 0.00% |

### Test Categories

| Category | Cases | Description |
|----------|-------|-------------|
| simple_english | 10 | Basic English event notices |
| hinglish | 10 | Hindi-English mixed notices |
| ambiguous_dates | 8 | Relative dates ("next Friday", "in 2 days") |
| multi_event | 6 | Multiple events in one message |
| cancellation | 5 | Cancellations and reschedules |
| chatter | 5 | Non-event messages (should extract nothing) |
| deadlines | 4 | Submission deadlines |
| mixed | 4 | Complex multi-event notices |

## Cost & Latency

### Gemini API Pricing (Nov 2026)

| Model | Input ($/1M) | Output ($/1M) | Use Case |
|-------|-------------|---------------|----------|
| gemini-3.5-flash-lite | $0.30 | $2.50 | Default extraction |
| gemini-3.8-flash | $0.75 | $3.75 | Higher accuracy |
| gemini-2.5-flash-lite | $0.10 | $0.40 | Budget option |
| text-embedding-004 | $0.02 | — | RAG embeddings |

### Cloud Run Free Tier

| Resource | Free Tier | Beyond Free Tier |
|----------|-----------|-----------------|
| CPU | 180,000 vCPU-s/month | $0.000024/vCPU-s |
| Memory | 360,000 GiB-s/month | $0.0000025/GiB-s |
| Requests | 2M/month | $0.40/million |

### Estimated Monthly Cost (Development)

| Component | Cost |
|-----------|------|
| Cloud Run | $0.00 (free tier) |
| Artifact Registry | ~$0.05 (0.5GB image) |
| Secret Manager | ~$0.06 (1 secret) |
| Gemini API | ~$0.50-5.00 (usage-based) |
| **Total** | **~$0.60-5.20/month** |

Optional Cloud SQL (pgvector): +$7-10/month (db-f1-micro)

## Deployment

### Cloud Run (Recommended)

```bash
# Set your project and API key
export GOOGLE_API_KEY="your-key"
export PROJECT_ID="your-project"

# Deploy
./deploy.sh $PROJECT_ID us-central1
```

### Terraform (Alternative)

```bash
cd deploy/terraform
terraform init
terraform apply -var="project_id=$PROJECT_ID" -var="google_api_key=$GOOGLE_API_KEY"
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| AI Framework | Google ADK 2.14.1 |
| LLM | Gemini 3.5 Flash-Lite (google-genai 3.6.0) |
| Embeddings | text-embedding-004 |
| Vector DB | ChromaDB (swappable interface) |
| API | FastAPI + slowapi rate limiting |
| Calendar | Google Calendar API v3 + OAuth 2.0 |
| Observability | Custom tracing + CLI report |
| Eval | 52-case labeled dataset + metrics harness |
| Deployment | Docker + Cloud Run + Terraform |
| CI | GitHub Actions (Python 3.11/3.12) |
| Quality | ruff + mypy + pytest (67 tests) |

## Limitations

- WhatsApp Web.js uses Puppeteer/Chromium which can be fragile (session expiry, rate limits)
- ChromaDB in Docker Compose is for development; production should use Cloud SQL pgvector or Vertex AI Vector Search
- Validator uses rule-based checks by default; LLM-based validation is available but adds cost
- Evaluation uses a static labeled dataset; real-world performance depends on notice complexity
- Gemini free tier has rate limits (1,500 RPD for 3.5 Flash-Lite)
- Cloud Run cold starts may add 1-2s latency for infrequent requests

## Project Structure

```
notifai/
├── agents/          # Multi-agent workflow (router, extractor, validator, scheduler, retriever)
├── api/             # FastAPI service (auth, endpoints, rate limiting)
├── config/          # Settings (pydantic-settings) + pricing config
├── core/            # Pydantic schemas (CollegeEvent, SessionState, Chunk)
├── eval/            # Evaluation harness (dataset, metrics, runner)
├── observability/   # Per-request tracing + CLI report
├── rag/             # RAG pipeline (embeddings, vector store, chunking)
└── tools/           # Typed tools (calendar, RAG retrieval)

tests/               # 67 tests (unit + integration)
deploy/terraform/    # Terraform IaC
Dockerfile.cloudrun  # Cloud Run optimized (non-root, health check)
deploy.sh            # One-command Cloud Run deployment
docker-compose.yml   # Local dev (Chroma + engine + broker)
```