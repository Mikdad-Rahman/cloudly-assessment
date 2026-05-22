# Adaptive Document Prep System
### Cloudly AI/ML Intern Assessment — Syeed Mikdad Rahman

---

## Project Overview

An AI-powered backend system that ingests a multi-section PDF document
(SLATEFALL Dossier), generates Multiple Choice Questions (MCQs) using
an LLM, scores user responses, and **adapts future question sets based
on the user's historical weak areas**.

The core differentiator is the adaptive intelligence: on returning prep
sessions, the system queries the Knowledge Base for previously wrong
answers and feeds that context into the LLM prompt — causing it to focus
new questions on topics the user consistently struggles with.

RAG (Retrieval Augmented Generation) powers the context retrieval —
the entire dossier is chunked, embedded using `all-MiniLM-L6-v2`, and
stored in ChromaDB. On each MCQ generation request, semantically
relevant chunks are retrieved via vector similarity search rather than
naive text truncation.

---

## Stack Choices & Reasoning

| Component | Choice | Reason |
|-----------|--------|--------|
| Backend | FastAPI | Async, auto-docs, clean Pydantic validation |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, fast inference, strong instruction following |
| PDF Parsing | PyMuPDF (fitz) | Reliable text extraction, handles complex layouts |
| RAG / Vector Store | ChromaDB + sentence-transformers | Local vector search, no API needed |
| Primary Database | SQLite | Zero setup, file-based, works without Docker |
| Extended Database | PostgreSQL + pgAdmin | Production-grade DB with visual management UI |
| Orchestration | Raw API calls | Keeps the flow transparent and easy to follow |
| UI | Streamlit | Rapid interactive frontend, pure Python |
| Containerization | Docker + docker-compose | Single command full stack setup |
| Logging | colorlog | Colored structured terminal + file logs |

---

## Architecture Overview

```
SLATEFALL_DOSSIER.pdf
        │
        ▼
  PDF Parser (PyMuPDF)
        │
        ├──► ChromaDB (255 chunks, vector indexed)
        │
        ▼
  Prep Engine
        │
        ├──► KB Check (SQLite / PostgreSQL)
        │         │
        │         └──► Weak Areas (if returning user)
        │
        ├──► RAG Retrieval (ChromaDB semantic search)
        │
        ├──► LLM (Groq) → MCQ Generation
        │
        ├──► Scorer → Results + Explanations
        │
        └──► KB Persist (sessions + questions + answers)
```

---

## Prerequisites

- Python 3.11+
- A free Groq API key from https://console.groq.com
- Docker Desktop (for containerized setup)

---

## Quick Start — Docker (Recommended)

The easiest way to run the full stack with a single command.

**Step 1 — Clone and configure**
```bash
git clone https://github.com/Mikdad-Rahman/cloudly-assessment.git
cd cloudly-assessment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

**Step 2 — Build and run**
```bash
docker-compose up --build
```

**Step 3 — Access the services**

| Service | URL | Credentials |
|---------|-----|-------------|
| FastAPI Docs | http://localhost:8000/docs | — |
| Streamlit UI | http://localhost:8501 | — |
| pgAdmin | http://localhost:5050 | admin@cloudly.io / admin123 |
| PostgreSQL | localhost:5432 | cloudly / cloudly123 |

**Step 4 — Connect pgAdmin to PostgreSQL**
1. Open http://localhost:5050
2. Login: admin@cloudly.io / admin123
3. Right click Servers → Register → Server
4. Name: cloudly
5. Connection tab:
   - Host: postgres
   - Port: 5432
   - Database: cloudly
   - Username: cloudly
   - Password: cloudly123

**Stop the stack**
```bash
docker-compose down
```

---

## Manual Setup (Without Docker)

**1. Clone the repository**
```bash
git clone https://github.com/Mikdad-Rahman/cloudly-assessment.git
cd cloudly-assessment
```

**2. Create and activate virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment**
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

**5. Place the SLATEFALL PDF**

Place `SLATEFALL_DOSSIER.pdf` in the root directory.

---

## Running the System

### Interactive CLI session
```bash
python main.py --sections 1 2
```

### Simulated answers (for evaluation)
```bash
python main.py --sections 1 2 --simulate
```

### Save outputs to folder
```bash
python main.py --sections 1 2 --simulate --output-dir outputs/my_session
```

### REST API server
```bash
python main.py --serve
```
Open http://localhost:8000/docs for interactive API documentation.

### Streamlit UI
```bash
streamlit run streamlit_app.py
```
Open http://localhost:8501

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| GET | /sections | List all 10 dossier sections |
| POST | /prep | Run a prep session |
| GET | /history/{section_id} | Get prior sessions for a section |
| GET | /weak-areas?section_ids=1,2 | Get weak areas for sections |
| GET | /kb-snapshot | Get last 5 sessions snapshot |

---

## Scenario B — Evaluation Outputs

Run these three commands in order (fresh database recommended):

**Iteration 1 — Sections 5, 8:**
```bash
python main.py --sections 5 8 --simulate --output-dir outputs/scenario_b_iter1
```

**Iteration 2 — Sections 6, 8, 9:**
```bash
python main.py --sections 6 8 9 --simulate --output-dir outputs/scenario_b_iter2
```

**Iteration 3 — Section 8 only:**
```bash
python main.py --sections 8 --simulate --output-dir outputs/scenario_b_iter3
```

Output files:
```
outputs/
├── scenario_b_iter1/
│   ├── questions_iter1.json
│   └── kb_snapshot_iter1.json
├── scenario_b_iter2/
│   ├── questions_iter2.json
│   └── kb_snapshot_iter2.json
└── scenario_b_iter3/
    ├── questions_iter3.json
    └── kb_snapshot_iter3.json
```

**Why adaptive behavior is visible across iterations:**
- Iter 1 studies sections 5 and 8 cold — fresh questions generated
- Iter 2 returns to section 8 — weak areas from Iter 1 detected, questions refocused
- Iter 3 studies section 8 again — weak areas from both prior sessions compound,
  questions drill the consistently wrong topics harder

---

## Knowledge Base Schema

**sessions table**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Unique session ID |
| section_ids | TEXT | JSON array of studied sections |
| created_at | TEXT | ISO timestamp |
| score | INTEGER | Correct answer count |
| total_questions | INTEGER | Total questions in session |

**questions table**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Unique question ID |
| session_id | INTEGER FK | Links to session |
| section_id | INTEGER | Source section |
| question_text | TEXT | The MCQ question |
| options | TEXT | JSON object of A/B/C/D options |
| correct_answer | TEXT | Correct letter |
| explanation | TEXT | Why the answer is correct |
| user_answer | TEXT | What the user answered |
| is_correct | INTEGER | 0 or 1 |

---

## How Adaptive Intelligence Works

1. Every session, all questions and answers are persisted to the KB
2. On a returning session, `get_weak_areas()` queries questions the
   user answered incorrectly across prior sessions for those sections
3. Weak area topics are extracted and used as the RAG query — so
   ChromaDB retrieves chunks most relevant to the user's weak spots
4. Weak area topics are also injected into the LLM prompt as explicit
   focus instructions
5. The LLM generates new questions targeting those weak spots from
   different angles — avoiding repetition while reinforcing weak areas

---

## How RAG Works

1. On first run, the entire SLATEFALL dossier is chunked into
   255 overlapping segments (500 chars each, 100 char overlap)
2. Each chunk is embedded using `all-MiniLM-L6-v2` sentence transformer
3. Vectors are stored persistently in ChromaDB (`chroma_db/` folder)
4. On MCQ generation, a semantic query is built from:
   - Weak area question texts (adaptive sessions)
   - Generic "key facts and details" query (fresh sessions)
5. ChromaDB returns the top-6 most semantically similar chunks
6. These chunks form the context sent to the LLM — no truncation,
   no keyword matching, pure semantic relevance

---

## Project Structure

```
cloudly_assessment/
├── app/
│   ├── api/
│   │   └── routes.py           # FastAPI REST endpoints
│   ├── core/
│   │   ├── pdf_parser.py       # PDF ingestion and section extraction
│   │   ├── llm.py              # Groq LLM + RAG-powered MCQ generation
│   │   ├── rag.py              # ChromaDB indexing and retrieval
│   │   ├── prep_engine.py      # Core prep flow orchestration
│   │   ├── scorer.py           # Answer scoring and result display
│   │   └── logger.py           # Structured colored logging
│   └── db/
│       ├── database.py         # SQLite KB — schema, queries, snapshots
│       └── database_pg.py      # PostgreSQL KB — production database
├── outputs/
│   ├── scenario_b_iter1/       # questions_iter1.json + kb_snapshot_iter1.json
│   ├── scenario_b_iter2/       # questions_iter2.json + kb_snapshot_iter2.json
│   └── scenario_b_iter3/       # questions_iter3.json + kb_snapshot_iter3.json
├── chroma_db/                  # ChromaDB vector store (auto-generated)
├── logs/                       # Structured log files (auto-generated)
├── streamlit_app.py            # Interactive Streamlit UI
├── main.py                     # CLI + FastAPI entry point
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Full stack orchestration
├── requirements.txt
├── .env.example                # Environment variable template
└── SLATEFALL_DOSSIER.pdf       # Source document
```

---

## Known Limitations

- LLM output is non-deterministic — question phrasing varies between runs
- ChromaDB vectors are pre-built on first run — re-indexing requires
  deleting the `chroma_db/` folder
- The system requires an active internet connection for Groq API calls
- PostgreSQL is optional — system falls back to SQLite automatically
  if PostgreSQL is not available
- Simulated answers use random selection — results vary between runs