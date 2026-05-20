import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "knowledge_base.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    Create all tables if they don't exist yet.
    This runs once when the app starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Table 1: sessions
    # Each time a user preps for sections, that's one session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_ids TEXT NOT NULL,
            created_at TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0
        )
    """)

    # Table 2: questions
    # Every MCQ generated and answered is stored here
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            section_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT NOT NULL,
            user_answer TEXT,
            is_correct INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def create_session(section_ids: list[int]) -> int:
    """
    Create a new prep session and return its ID.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (section_ids, created_at)
        VALUES (?, ?)
    """, (json.dumps(section_ids), datetime.now().isoformat()))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def save_question(session_id: int, section_id: int, question: dict) -> int:
    """
    Save a generated MCQ to the database.
    question dict must have: question_text, options, correct_answer, explanation
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO questions 
        (session_id, section_id, question_text, options, correct_answer, explanation, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        section_id,
        question["question_text"],
        json.dumps(question["options"]),
        question["correct_answer"],
        question["explanation"],
        datetime.now().isoformat()
    ))
    question_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return question_id


def save_answer(question_id: int, user_answer: str, is_correct: bool):
    """
    Record the user's answer for a question.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE questions
        SET user_answer = ?, is_correct = ?
        WHERE id = ?
    """, (user_answer, 1 if is_correct else 0, question_id))
    conn.commit()
    conn.close()


def update_session_score(session_id: int, score: int, total: int):
    """
    Update the final score for a session.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sessions
        SET score = ?, total_questions = ?
        WHERE id = ?
    """, (score, total, session_id))
    conn.commit()
    conn.close()


def get_weak_areas(section_ids: list[int]) -> list[dict]:
    """
    Find questions the user got wrong in previous sessions for these sections.
    This is the CORE of the adaptive system.
    Returns a list of previously wrong questions to inform new MCQ generation.
    """
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(section_ids))
    cursor.execute(f"""
        SELECT question_text, correct_answer, explanation, section_id,
               COUNT(*) as wrong_count
        FROM questions
        WHERE section_id IN ({placeholders})
        AND is_correct = 0
        AND user_answer IS NOT NULL
        GROUP BY question_text
        ORDER BY wrong_count DESC
        LIMIT 10
    """, section_ids)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_prior_sessions(section_ids: list[int]) -> list[dict]:
    """
    Check if the user has prepped these sections before.
    Returns list of prior sessions.
    """
    conn = get_connection()
    cursor = conn.cursor()
    results = []
    for section_id in section_ids:
        cursor.execute("""
            SELECT s.id, s.section_ids, s.created_at, s.score, s.total_questions
            FROM sessions s
            JOIN questions q ON q.session_id = s.id
            WHERE q.section_id = ?
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, (section_id,))
        rows = cursor.fetchall()
        results.extend([dict(row) for row in rows])
    conn.close()
    # deduplicate by session id
    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique


def get_kb_snapshot() -> list[dict]:
    """
    Export the 5 most recent sessions with their questions.
    This is what gets saved to kb_snapshot.json for the evaluators.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM sessions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    sessions = [dict(row) for row in cursor.fetchall()]

    for session in sessions:
        cursor.execute("""
            SELECT * FROM questions WHERE session_id = ?
        """, (session["id"],))
        questions = [dict(row) for row in cursor.fetchall()]
        for q in questions:
            q["options"] = json.loads(q["options"])
        session["questions"] = questions

    conn.close()
    return sessions


if __name__ == "__main__":
    init_db()