# Policy System

A role-based AI assistant for querying internal policy documents. Users ask questions in natural language and receive grounded, cited answers drawn strictly from documents their role is authorized to access.

---

## What it does

Policy documents (PDFs, DOCX, Markdown) are ingested and stored as vector embeddings. When a user submits a query, the system:

1. Looks up which documents the user's role permits them to see
2. Retrieves the most relevant chunks from those documents only — unauthorized content is filtered at the vector store level, not in application code
3. Sends the retrieved chunks to a local LLM (Llama 3 via Ollama) along with the question
4. Returns a grounded answer in one of two formats:
   - **Executive Summary** — concise, no citation markers
   - **Detailed Response** — comprehensive, with `[Doc Title, Page X, Para Y]` citations

If a query touches a domain the user has no access to, the system returns a permission prompt instead of calling the LLM. No hallucination from out-of-scope sources.

**Key capabilities:**

| Feature | Description |
|---|---|
| Role-based access | Documents are tagged with roles at upload; retrieval is pre-filtered at the vector store |
| Multi-role union | Users with multiple roles see the union of all their accessible documents |
| Archive toggle | Archived documents are hidden by default; a UI toggle re-includes them |
| Response formats | Per-user default format with per-session override |
| Feedback & flagging | Thumbs up/down; auditor feedback carries higher weight; thumbs-down auto-flags the conversation and snapshots the full thread |
| Automated validation | Canned Q&A pairs scored against gold answers via cosine similarity |
| Fully local | No cloud services; LLM and embeddings run via Ollama |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
│              Next.js 15  ·  Tailwind  ·  shadcn/ui             │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS / JWT (httpOnly cookie)
┌───────────────────────────────▼─────────────────────────────────┐
│                        FastAPI  (port 8000)                      │
│  /auth  /admin  /query  /feedback          --workers 1 required │
└──────┬─────────────────────────────┬────────────────────────────┘
       │                             │
       ▼                             ▼
┌──────────────┐            ┌────────────────────┐
│  PostgreSQL  │            │  ChromaDB          │
│  (port 5432) │            │  (embedded,        │
│              │            │   ./data/chroma_db)│
│  users       │            │                    │
│  roles       │            │  chunk vectors     │
│  documents   │            │  + metadata:       │
│  messages    │            │    doc_id          │
│  feedback    │            │    page / para     │
│  canned_q's  │            │    role_{uuid}=T   │──► role pre-filter
│  valid_runs  │            │    is_archived      │
└──────────────┘            └─────────┬──────────┘
                                      │ similarity search
                            ┌─────────▼──────────┐
                            │  Ollama  (port 11434)│
                            │  nomic-embed-text    │ ◄─ embeddings
                            │  llama3 / mistral    │ ◄─ chat
                            └────────────────────┘
```

### Layer breakdown

```
core/           Protocols + dataclasses — zero infrastructure deps
  interfaces.py   RAGProvider, LLMProvider (typing.Protocol)
  models.py       Chunk, RetrievedChunk, LLMResponse, CrossDomainPermissionRequired

db/             SQLAlchemy async ORM + Alembic migrations
auth/           bcrypt password hashing, HS256 JWT, FastAPI dependency
admin/          User, document, and access management services
ingestion/      PDF / DOCX / text parsers → chunker → pipeline
rag/            ChromaDB provider (role pre-filter enforced here)
llm/            Ollama provider (embed + chat)
query/          Engine: access-filter → retrieve → generate → persist
feedback/       Rating service (auditor weighting) + conversation flagging
validation/     Canned Q&A runner + cosine similarity scorer
api/            FastAPI routers, Pydantic schemas, app factory
```

### Security model

Role filtering is a **pre-filter at the vector store level**, not a post-filter in Python. ChromaDB metadata stores one boolean key per allowed role (`role_{uuid}=True`). The `similarity_search` WHERE clause is constructed from the user's actual role UUIDs before the query runs — results that don't match never leave the database.

When zero chunks match after filtering, the engine returns a typed `CrossDomainPermissionRequired` signal and **does not call the LLM**.

---

## Setup

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org) |
| uv | latest | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| Docker | any | [docker.com](https://www.docker.com) |
| Ollama | latest | [ollama.com](https://ollama.com) |

---

### 1. Clone and install

```bash
git clone <repo-url>
cd policy_system

# Install all dependencies (including dev extras)
uv sync --dev
```

---

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if you need to change anything — the defaults work out of the box with Docker:

```dotenv
DATABASE_URL=postgresql+asyncpg://policy_user:policy_pass@localhost:5432/policy_db
JWT_SECRET=change-me-to-a-long-random-secret   # change this
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3
CHROMA_PERSIST_DIR=./data/chroma_db
```

---

### 3. Start PostgreSQL

```bash
docker compose up -d
```

This starts Postgres 16 on port 5432 and pgAdmin on port 5050 (`admin@local.dev` / `admin`).

---

### 4. Run database migrations

```bash
uv run alembic upgrade head
```

Creates all tables: `users`, `roles`, `user_roles`, `documents`, `document_access`, `conversations`, `messages`, `feedback`, `canned_questions`, `validation_runs`.

---

### 5. Seed the database

Bootstrap one user per role type so you can log in immediately:

```bash
uv run python scripts/seed_db.py
```

This creates four accounts (all with password `Admin1234!`):

| Email | Role type | Description |
|---|---|---|
| `admin@example.com` | `SYSTEM_ADMIN` | Full admin access |
| `global.auditor@example.com` | `GLOBAL_AUDITOR` | Sees all documents, feedback weight 2.0 |
| `domain.auditor@example.com` | `DOMAIN_AUDITOR` | Engineering domain, feedback weight 1.5 |
| `user@example.com` | `FUNCTIONAL` | Standard user, Engineering domain |

The script is idempotent — safe to re-run if accounts already exist.

---

### 6. Start Ollama and pull models

```bash
# In a separate terminal
ollama serve

# Pull required models (one-time, ~5 GB total)
ollama pull llama3
ollama pull nomic-embed-text
```

---

### 7. Start the API

```bash
# Single worker is required — ChromaDB embedded mode is not safe with multiple workers
uv run uvicorn policy_system.api.main:app --workers 1 --reload
```

API is live at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

---

### 8. Run tests

```bash
uv run pytest tests/ -v
```

Tests use an in-memory SQLite database and do not require Postgres or Ollama to be running.

---

## Notebooks

The `notebooks/` directory contains one Jupyter notebook per build phase. Open them in order to validate each layer interactively.

```bash
# Register the kernel once after uv sync (writes the correct Python path outside .venv)
uv run python -m ipykernel install --user --name policy-system --display-name "Policy System"

# Launch JupyterLab and select the "Policy System" kernel in each notebook
uv run jupyter lab
```

| Notebook | Purpose | Owner |
|---|---|---|
| `01_db_and_auth.ipynb` | DB connection, seed data, password + JWT tests | Built |
| `02_document_ingestion_admin.ipynb` | Admin services, role access, archive toggle | Built |
| `03_document_parsing.ipynb` | PDF/DOCX/text parsing, chunker inspection | User (RAG exploration) |
| `04_rag_pipeline.ipynb` | Ollama embed, end-to-end ingest, role isolation test | User (RAG exploration) |
| `05_query_engine.ipynb` | Full query flow, citations, cross-domain fallback | Built |
| `06_feedback_and_flagging.ipynb` | Feedback weights, thumbs-down flagging | Built |
| `07_validation_harness.ipynb` | Gold Q&A scoring, pass/fail table, prompt tuning | Built |

---

## API Quick Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | Public | Get JWT token |
| `GET` | `/auth/me` | User | Current user profile |
| `POST` | `/admin/users` | Admin | Create user |
| `POST` | `/admin/users/{id}/roles` | Admin | Assign role to user |
| `POST` | `/admin/documents` | Admin | Register document + role access |
| `PATCH` | `/admin/documents/{id}/archive` | Admin | Archive / unarchive document |
| `POST` | `/query/` | User | Submit policy query |
| `POST` | `/feedback/` | User | Submit thumbs up/down |
| `GET` | `/health` | Public | Health check |

Full schema available at `/docs` (Swagger UI) or `/openapi.json`.

---

## Project Constraints

- **Single worker only**: `--workers 1` is required. ChromaDB in embedded mode is not safe for multi-process deployments. To support multiple workers, migrate the vector store to `pgvector` (same Postgres instance — only `rag/chromadb_provider.py` needs to change).
- **Local only**: Designed for local deployment. No cloud infrastructure required.
- **Ollama required**: The LLM and embedding model run locally via Ollama. Swapping to a hosted API requires only changing `llm/ollama_provider.py` and the `LLM_PROVIDER` config value.
