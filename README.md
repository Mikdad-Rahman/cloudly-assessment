# Adaptive Document Preparation System

### Cloudly AI/ML Intern Assessment — Syeed Mikdad Rahman

---

## Project Overview

An AI-powered Adaptive Document Preparation System that ingests a multi-section PDF, generates MCQs using an LLM, scores user responses, and **adapts future question sets based on historical weak areas**.

The system distinguishes between first-time and returning prep runs. On returning runs, the history context (mistakes + question drift) influences what new questions are generated — this is the core adaptive intelligence.

RAG (Retrieval Augmented Generation) powers context retrieval — the entire dossier is chunked, embedded using `all-MiniLM-L6-v2`, and stored in ChromaDB. On each MCQ generation request, semantically relevant chunks are retrieved via vector similarity search.

---

## Stack Choices & Reasoning

| Component          | Choice                           | Reason                                                                           |
| ------------------ | -------------------------------- | -------------------------------------------------------------------------------- |
| Backend            | FastAPI                          | Async, auto-docs, clean Pydantic validation                                      |
| LLM                | Groq (llama-3.3-70b-versatile)   | Free tier, fast inference, strong instruction following                          |
| PDF Parsing        | PyMuPDF (fitz)                   | Reliable text extraction, handles complex layouts                                |
| RAG / Vector Store | ChromaDB + sentence-transformers | Local vector search, no API needed, persistent                                   |
| Database           | PostgreSQL + pgAdmin             | Production-grade, supports all required KB query patterns                        |
| Orchestration      | Raw API calls                    | Keeps flow transparent and easy to follow                                        |
| UI (Primary)       | HTML/JS + nginx                  | Lightweight, Docker-native, instant load                                         |
| UI (Legacy)        | Streamlit                        | Original prototype — replaced due to Docker startup timing issue on Windows/WSL2 |
| Containerization   | Docker + docker-compose          | Single command full stack setup                                                  |
| Logging            | colorlog                         | Colored structured terminal + file logs                                          |

---

## Architecture Overview

```
SLATEFALL_DOSSIER.pdf  (or any uploaded PDF)
        │
        ▼
  PDF Parser (PyMuPDF)
        │
        ├──► ChromaDB (255 chunks, vector indexed)
        │
        ▼
  Prep Engine
        │
        ├──► KB Check (PostgreSQL)
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
- Docker Desktop installed and running
- A free Groq API key from https://console.groq.com
- Git

---

## Quick Start — Docker (Recommended)

> ⏱ Estimated setup time: under 5 minutes

### Step 1 — Clone the repository

```bash
git clone https://github.com/Mikdad-Rahman/cloudly-assessment.git
cd cloudly-assessment
```

### Step 2 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

```
GROQ_API_KEY=your_groq_api_key_here
```

### Step 3 — Build and run

```bash
docker-compose up --build
```

Wait for all containers to start (first build takes ~3-5 minutes due to model downloads).

### Step 4 — Access the services

| Service      | URL                        | Credentials                 |
| ------------ | -------------------------- | --------------------------- |
| HTML/JS UI   | http://localhost:3001      | —                           |
| FastAPI Docs | http://localhost:8000/docs | —                           |
| pgAdmin      | http://localhost:5050      | admin@cloudly.io / admin123 |
| PostgreSQL   | localhost:5432             | cloudly / cloudly123        |

### Step 5 — Connect pgAdmin to PostgreSQL (optional, for DB inspection)

1. Open http://localhost:5050
2. Login: `admin@cloudly.io` / `admin123`
3. Right click **Servers → Register → Server**
4. **General tab** → Name: `cloudly`
5. **Connection tab:**
   - Host: `postgres`
   - Port: `5432`
   - Database: `cloudly`
   - Username: `cloudly`
   - Password: `cloudly123`

### Stop the stack

```bash
docker-compose down
```

---

## UI Options

### HTML/JS UI v2.0 (Docker — Recommended)

Lightweight, Docker-native UI served by nginx. Instant load, calls FastAPI directly via REST.

```
http://localhost:3001
```

Features:

- Upload any PDF and auto-index it
- Select sections and start a prep session
- Answer MCQs interactively
- View results with explanations
- Browse history grouped by PDF document
- KB Snapshot with expandable session details

### Streamlit UI (Legacy — Local Only)

`streamlit_app.py` is kept in the repository as evidence of the first UI implementation. During development, Streamlit was the original UI choice but a startup timing issue was discovered — ChromaDB initialization inside Docker on Windows/WSL2 caused the container to hang indefinitely on the blank loading screen. This led to the decision to build the HTML/JS UI as a proper Docker-native replacement.

If you want to view the original Streamlit UI, run it locally while Docker services are running:

\```bash

# Make sure postgres is running first

docker-compose up -d postgres

# Then run Streamlit locally

streamlit run streamlit_app.py
\```
Open http://localhost:8501

> ℹ️ The Streamlit UI is **not part of the Docker stack** and is not required to run the system. The HTML/JS UI at http://localhost:3001 is the primary interface.

---

## Manual Setup (Without Docker)

### 1. Clone the repository

```bash
git clone https://github.com/Mikdad-Rahman/cloudly-assessment.git
cd cloudly-assessment
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 5. Start PostgreSQL via Docker

```bash
docker-compose up -d postgres
```

### 6. Place the SLATEFALL PDF

Place `SLATEFALL_DOSSIER.pdf` in the project root directory.

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

### Start REST API server

```bash
python main.py --serve
```

Open http://localhost:8000/docs for interactive API documentation.

---

## Evaluation Scenarios

### Scenario A — Cold-start prep (any two sections)

```bash
python main.py --sections 3 7 --simulate
```

This runs a fresh prep session over sections 3 and 7 with no prior history. Questions are generated purely from PDF content.

---

### Scenario B — Three consecutive adaptive iterations

Run these commands in order. Each builds on the history of the previous.

**Iteration 1 — Sections 5, 8 (cold start):**

```bash
python main.py --sections 5 8 --simulate --output-dir outputs/scenario_b_iter1
```

**Iteration 2 — Sections 6, 8, 9 (section 8 is a returning section):**

```bash
python main.py --sections 6 8 9 --simulate --output-dir outputs/scenario_b_iter2
```

**Iteration 3 — Section 8 only (maximum adaptive focus):**

```bash
python main.py --sections 8 --simulate --output-dir outputs/scenario_b_iter3
```

**Output files generated:**

```
outputs/
├── scenario_b_iter1/
│   ├── questions_iter1.json       # Questions generated + simulated answers
│   └── kb_snapshot_iter1.json     # KB state at end of iteration 1
├── scenario_b_iter2/
│   ├── questions_iter2.json
│   └── kb_snapshot_iter2.json
└── scenario_b_iter3/
    ├── questions_iter3.json
    └── kb_snapshot_iter3.json
```

**Why adaptive behavior is visible across iterations:**

- **Iter 1** — Sections 5 and 8 studied cold. No prior history. Fresh questions generated from PDF content via RAG.
- **Iter 2** — Section 8 is a returning section. Weak areas from Iter 1 are detected in the KB. RAG query is built from wrong-answer topics. LLM prompt is injected with weak area context. Questions refocus on previously missed topics.
- **Iter 3** — Section 8 studied again. Weak areas from both Iter 1 and Iter 2 compound. The system drills the consistently wrong topics harder from different angles, avoiding repetition of already-mastered questions.

---

## API Endpoints

| Method | Endpoint                    | Description                                         |
| ------ | --------------------------- | --------------------------------------------------- |
| GET    | /                           | Health check                                        |
| GET    | /pdf-info                   | Get current PDF filename and display name           |
| GET    | /sections                   | List all sections in the current PDF                |
| POST   | /upload-pdf                 | Upload a new PDF, re-parse and re-index ChromaDB    |
| POST   | /prep                       | Run a full prep session (CLI/simulate mode)         |
| POST   | /generate                   | Generate questions for UI (interactive, no answers) |
| POST   | /submit                     | Submit answers, score and save to DB                |
| GET    | /history/{section_id}       | Get prior sessions for a section with questions     |
| GET    | /all-sessions               | Get all sessions grouped by PDF name                |
| GET    | /weak-areas?section_ids=1,2 | Get weak areas for sections                         |
| GET    | /kb-snapshot                | Get last 5 sessions snapshot with questions         |

---

## Knowledge Base Schema

### sessions table

| Column          | Type      | Description                       |
| --------------- | --------- | --------------------------------- |
| id              | SERIAL PK | Unique session ID                 |
| section_ids     | TEXT      | JSON array of studied section IDs |
| created_at      | TEXT      | ISO timestamp                     |
| score           | INTEGER   | Correct answer count              |
| total_questions | INTEGER   | Total questions in session        |
| pdf_name        | TEXT      | Source PDF filename               |

### questions table

| Column         | Type       | Description                    |
| -------------- | ---------- | ------------------------------ |
| id             | SERIAL PK  | Unique question ID             |
| session_id     | INTEGER FK | Links to sessions.id           |
| section_id     | INTEGER    | Source section number          |
| question_text  | TEXT       | The MCQ question               |
| options        | TEXT       | JSON object of A/B/C/D options |
| correct_answer | TEXT       | Correct letter (A/B/C/D)       |
| explanation    | TEXT       | Why the answer is correct      |
| user_answer    | TEXT       | What the user answered         |
| is_correct     | INTEGER    | 0 or 1                         |
| created_at     | TEXT       | ISO timestamp                  |

### KB Query Patterns Supported

- **Prior sessions by section IDs** → `get_prior_sessions(section_ids)` — used for adaptive mode detection
- **Question-level results by session** → `SELECT * FROM questions WHERE session_id = ?`
- **Weak areas across sessions** → `get_weak_areas(section_ids)` — groups wrong answers by question, orders by wrong count
- **KB snapshot** → `get_kb_snapshot()` — top-5 most recent sessions with full question details

---

## How Adaptive Intelligence Works

1. Every session, all questions and answers are persisted to PostgreSQL
2. On a returning session, `get_weak_areas()` queries questions answered incorrectly across prior sessions for those sections
3. Weak area topics are extracted and used as the RAG query — ChromaDB retrieves chunks most semantically relevant to the user's weak spots
4. Weak area topics are injected into the LLM prompt as explicit focus instructions
5. The LLM generates new questions targeting those weak spots from different angles — avoiding repetition while reinforcing weak areas

---

## How RAG Works

1. On first run, the entire dossier is chunked into 255 overlapping segments (500 chars each, 100 char overlap)
2. Each chunk is embedded using `all-MiniLM-L6-v2` sentence transformer (runs locally, no API needed)
3. Vectors are stored persistently in ChromaDB (`chroma_db/` folder)
4. On MCQ generation, a semantic query is built from:
   - Weak area question texts (adaptive sessions)
   - Generic "key facts and details" query (fresh sessions)
5. ChromaDB returns the top-6 most semantically similar chunks
6. These chunks form the context sent to the LLM — no truncation, no keyword matching, pure semantic relevance

---

## Project Structure

```
cloudly_assessment/
├── app/
│   ├── api/
│   │   └── routes.py           # FastAPI REST endpoints (10 endpoints)
│   ├── core/
│   │   ├── config.py           # Active PDF path management
│   │   ├── pdf_parser.py       # PDF ingestion and section extraction
│   │   ├── llm.py              # Groq LLM + RAG-powered MCQ generation
│   │   ├── rag.py              # ChromaDB indexing, retrieval, reindexing
│   │   ├── prep_engine.py      # Core prep flow orchestration
│   │   ├── scorer.py           # Answer scoring and result display
│   │   └── logger.py           # Structured colored logging
│   └── db/
│       ├── database.py         # DB router — delegates to PostgreSQL
│       └── database_pg.py      # PostgreSQL — sessions, questions, answers
├── ui/
│   └── index.html              # HTML/JS UI v2.0 (served by nginx)
├── outputs/
│   ├── scenario_b_iter1/       # questions_iter1.json + kb_snapshot_iter1.json
│   ├── scenario_b_iter2/       # questions_iter2.json + kb_snapshot_iter2.json
│   └── scenario_b_iter3/       # questions_iter3.json + kb_snapshot_iter3.json
├── .streamlit/
│   └── config.toml             # Streamlit server config
├── chroma_db/                  # ChromaDB vector store (auto-generated)
├── logs/                       # Structured log files (auto-generated)
├── streamlit_app.py            # Streamlit UI (runs locally)
├── main.py                     # CLI + FastAPI entry point
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Full stack orchestration
├── requirements.txt            # Full dependencies
├── requirements-docker.txt     # CPU-optimized dependencies for Docker
├── .env.example                # Environment variable template
└── SLATEFALL_DOSSIER.pdf       # Source document
```

---

## Optional Enhancements Implemented

| Enhancement      | Status | Details                                                                     |
| ---------------- | ------ | --------------------------------------------------------------------------- |
| Containerization | ✅     | Docker + docker-compose, full stack with one command                        |
| Minimal UI       | ✅     | HTML/JS UI v2.0 (Docker) + Streamlit (local)                                |
| Error Handling   | ✅     | LLM failures, invalid section IDs, PDF parse errors, DB connection timeouts |
| Logging          | ✅     | colorlog with timestamps, session IDs, structured log files                 |
| PDF Upload       | ✅     | Upload any PDF, auto re-parse and re-index ChromaDB                         |
| PDF Tracking     | ✅     | Sessions track which PDF they came from                                     |
| pgAdmin          | ✅     | Visual DB management at http://localhost:5050                               |

---

## Known Limitations & Assumptions

- **LLM non-determinism** — MCQ phrasing varies between runs due to temperature. Structural correctness (4 choices, one answer, one explanation) is consistent.
- **PDF section detection** — The parser looks for patterns like `Section N.`, `Chapter N:`, `Part N`, `Module N`, `Unit N`. PDFs with different formatting may need the pattern adjusted in `pdf_parser.py`.
- **ChromaDB reindexing** — Uploading a new PDF clears and rebuilds the vector index. This takes ~30-60 seconds depending on PDF size.
- **Streamlit in Docker** — Has a startup timing issue with ChromaDB initialization on Windows/WSL2. Use the HTML/JS UI at http://localhost:3001 instead.
- **Simulated answers** — Scenario B uses random answer simulation (`--simulate`). Adaptive behavior is demonstrated by the system detecting wrong answers and refocusing questions, not by the correctness of simulated inputs.
- **Internet required** — Groq API calls require an active internet connection.
