import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
from app.core.logger import get_logger

load_dotenv()
logger = get_logger("database_pg")

# PostgreSQL connection string from environment
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "cloudly")
PG_USER = os.getenv("PG_USER", "cloudly")
PG_PASSWORD = os.getenv("PG_PASSWORD", "cloudly123")


def get_connection():
    """Get a PostgreSQL connection."""
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )
    return conn


def init_pg_db():
    """Create tables in PostgreSQL if they don't exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                section_ids TEXT NOT NULL,
                created_at TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                section_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT NOT NULL,
                user_answer TEXT,
                is_correct INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        logger.info("PostgreSQL database initialized successfully.")
        return True

    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")
        return False


def create_session_pg(section_ids: list[int]) -> int:
    """Create a new prep session in PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (section_ids, created_at)
        VALUES (%s, %s) RETURNING id
    """, (json.dumps(section_ids), datetime.now().isoformat()))
    session_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    logger.info(f"Created PostgreSQL session ID: {session_id}")
    return session_id


def save_question_pg(session_id: int, section_id: int, question: dict) -> int:
    """Save a question to PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions
        (session_id, section_id, question_text, options,
         correct_answer, explanation, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, (
        session_id,
        section_id,
        question["question_text"],
        json.dumps(question["options"]),
        question["correct_answer"],
        question["explanation"],
        datetime.now().isoformat()
    ))
    question_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return question_id


def save_answer_pg(question_id: int, user_answer: str, is_correct: bool):
    """Save a user answer to PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE questions
        SET user_answer = %s, is_correct = %s
        WHERE id = %s
    """, (user_answer, 1 if is_correct else 0, question_id))
    conn.commit()
    conn.close()


def update_session_score_pg(session_id: int, score: int, total: int):
    """Update session score in PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sessions
        SET score = %s, total_questions = %s
        WHERE id = %s
    """, (score, total, session_id))
    conn.commit()
    conn.close()


def get_weak_areas_pg(section_ids: list[int]) -> list[dict]:
    """Get weak areas from PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    placeholders = ",".join(["%s"] * len(section_ids))
    cursor.execute(f"""
        SELECT question_text, correct_answer, explanation, section_id,
               COUNT(*) as wrong_count
        FROM questions
        WHERE section_id IN ({placeholders})
        AND is_correct = 0
        AND user_answer IS NOT NULL
        GROUP BY question_text, correct_answer, explanation, section_id
        ORDER BY wrong_count DESC
        LIMIT 10
    """, section_ids)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_prior_sessions_pg(section_ids: list[int]) -> list[dict]:
    """Get prior sessions from PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    results = []
    for section_id in section_ids:
        cursor.execute("""
            SELECT s.id, s.section_ids, s.created_at, s.score, s.total_questions
            FROM sessions s
            JOIN questions q ON q.session_id = s.id
            WHERE q.section_id = %s
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, (section_id,))
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
    conn.close()
    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique


def get_kb_snapshot_pg() -> list[dict]:
    """Get KB snapshot from PostgreSQL."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT * FROM sessions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    sessions = [dict(row) for row in cursor.fetchall()]
    for session in sessions:
        cursor.execute("""
            SELECT * FROM questions WHERE session_id = %s
        """, (session["id"],))
        questions = [dict(row) for row in cursor.fetchall()]
        for q in questions:
            q["options"] = json.loads(q["options"])
        session["questions"] = questions
    conn.close()
    return sessions