# Adaptive Document Prep System
### Cloudly AI/ML Intern Assessment — Syeed Mikdad Rahman

## Project Overview

An AI-powered backend system that ingests a multi-section PDF document
(SLATEFALL Dossier), generates Multiple Choice Questions (MCQs) using
an LLM, scores user responses, and **adapts future question sets based
on the user's historical weak areas**.

The core differentiator is the adaptive intelligence: on returning prep
sessions, the system queries the Knowledge Base for previously wrong
answers and feeds that context into the LLM prompt — causing it to focus
new questions on topics the user consistently struggles with.

---

## Stack Choices & Reasoning

| Component | Choice | Reason |
|-----------|--------|--------|
| Backend | FastAPI | Async, auto-docs, clean Pydantic validation |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, fast inference, strong instruction following |
| PDF Parsing | PyMuPDF (fitz) | Reliable text extraction, handles complex layouts |
| Database | SQLite | Zero setup, file-based, perfect for local assessment |
| Orchestration | Raw API calls | Keeps the flow transparent and easy to follow |

---

## Prerequisites

- Python 3.11+
- A free Groq API key from https://console.groq.com

---

## Setup Instructions

**1. Clone the repository**
```bash
git clone <your-repo-url>
cd cloudly_assessment
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

**4. Add your Groq API key**

Create a `.env` file in the root directory: (Paste your key in the file just like the ".env_example")

**5. Add the SLATEFALL PDF**

Place `SLATEFALL_DOSSIER.pdf` in the root directory.

---

## Running with Docker (Recommended)

The easiest way to run the full stack.

**Prerequisites:** Docker Desktop installed and running.

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

This starts two services:
- FastAPI backend → http://localhost:8000/docs
- Streamlit UI → http://localhost:8501

**Step 3 — Run Scenario B (in a separate terminal)**
```bash
docker-compose exec api python main.py --sections 5 8 --simulate --output-dir outputs/scenario_b_iter1
docker-compose exec api python main.py --sections 6 8 9 --simulate --output-dir outputs/scenario_b_iter2
docker-compose exec api python main.py --sections 8 --simulate --output-dir outputs/scenario_b_iter3
```

**Stop the stack**
```bash
docker-compose down
```

---

## Running the System

### As a CLI (interactive prep session)
```bash
python main.py --sections 1 2
```

### With simulated answers
```bash
python main.py --sections 1 2 --simulate
```

### With output files saved
```bash
python main.py --sections 1 2 --simulate --output-dir outputs/my_session
```

### As a REST API server
```bash
python main.py --serve
```
Then open http://localhost:8000/docs for interactive API documentation.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Health check |
| GET | /sections | List all 10 sections |
| POST | /prep | Run a prep session |
| GET | /history/{section_id} | Get prior sessions for a section |
| GET | /weak-areas?section_ids=1,2 | Get weak areas for sections |
| GET | /kb-snapshot | Get last 5 sessions snapshot |

---

## Scenario B — Evaluation Outputs

Run these three commands in order:

**Iteration 1 — Sections 5, 8:**
```bash
python main.py --sections 5 8 --simulate --output-dir outputs/scenario_b_iter1
```

**Iteration 2 — Sections 6, 8, 9:**
```bash
python main.py --sections 6 8 9 --simulate --output-dir outputs/scenario_b_iter2
```

**Iteration 3 — Section 8:**
```bash
python main.py --sections 8 --simulate --output-dir outputs/scenario_b_iter3
```

Output files are saved to:
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

---

## Knowledge Base Schema

**sessions table**
- `id` — unique session ID
- `section_ids` — JSON array of studied sections
- `created_at` — timestamp
- `score` — correct answers count
- `total_questions` — total questions in session

**questions table**
- `id` — unique question ID
- `session_id` — links to session
- `section_id` — which section this came from
- `question_text`, `options`, `correct_answer`, `explanation`
- `user_answer` — what the user answered
- `is_correct` — 0 or 1

---

## How Adaptive Intelligence Works

1. On every session, all questions and answers are persisted to SQLite
2. On a returning session, `get_weak_areas()` queries questions answered
   incorrectly across prior sessions for those sections
3. The weak area topics are injected into the LLM prompt as explicit
   focus instructions
4. The LLM generates new questions targeting those weak spots from
   different angles — avoiding repetition while reinforcing weak areas

---

## Known Limitations

- LLM output is non-deterministic — question phrasing varies between runs
- Section content is truncated to 4,000 characters for LLM context limits
- Simulated answers use a random seed — results vary between simulation runs
- The system requires an active internet connection for Groq API calls

---

## Project Structure
cloudly_assessment/
├── app/
│   ├── api/
│   │   └── routes.py         # FastAPI endpoints
│   ├── core/
│   │   ├── pdf_parser.py     # PDF ingestion and section extraction
│   │   ├── llm.py            # Groq LLM integration and MCQ generation
│   │   ├── prep_engine.py    # Core prep flow orchestration
│   │   └── scorer.py         # Answer scoring and result display
│   └── db/
│       └── database.py       # SQLite KB — schema, queries, snapshots
├── outputs/
│   ├── scenario_b_iter1/
│   ├── scenario_b_iter2/
│   └── scenario_b_iter3/
├── main.py                   # CLI + FastAPI entry point
├── requirements.txt
├── .env                      # API keys (not committed)
└── SLATEFALL_DOSSIER.pdf

