import json
import socket
from datetime import datetime
from app.core.logger import get_logger

logger = get_logger("database")


def _is_postgres_available() -> bool:
    """Check if PostgreSQL is reachable with a 2 second timeout."""
    try:
        import os
        host = os.getenv("PG_HOST", "localhost")
        port = int(os.getenv("PG_PORT", "5432"))
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return True
    except Exception:
        return False


def init_db():
    """Initialize PostgreSQL database."""
    if not _is_postgres_available():
        logger.warning("PostgreSQL not reachable — skipping DB init. Start Docker to use the app.")
        return

    from app.db.database_pg import init_pg_db
    from app.core.pdf_parser import extract_sections
    from app.core.rag import index_sections

    init_pg_db()

    try:
        sections = extract_sections("SLATEFALL_DOSSIER.pdf")
        index_sections(sections)
    except Exception as e:
        logger.warning(f"RAG indexing skipped: {e}")


def create_session(section_ids: list[int]) -> int:
    from app.db.database_pg import create_session_pg
    return create_session_pg(section_ids)


def save_question(session_id: int, section_id: int, question: dict) -> int:
    from app.db.database_pg import save_question_pg
    return save_question_pg(session_id, section_id, question)


def save_answer(question_id: int, user_answer: str, is_correct: bool):
    from app.db.database_pg import save_answer_pg
    save_answer_pg(question_id, user_answer, is_correct)


def update_session_score(session_id: int, score: int, total: int):
    from app.db.database_pg import update_session_score_pg
    update_session_score_pg(session_id, score, total)


def get_weak_areas(section_ids: list[int]) -> list[dict]:
    from app.db.database_pg import get_weak_areas_pg
    return get_weak_areas_pg(section_ids)


def get_prior_sessions(section_ids: list[int]) -> list[dict]:
    from app.db.database_pg import get_prior_sessions_pg
    return get_prior_sessions_pg(section_ids)


def get_kb_snapshot() -> list[dict]:
    from app.db.database_pg import get_kb_snapshot_pg
    return get_kb_snapshot_pg()


if __name__ == "__main__":
    init_db()