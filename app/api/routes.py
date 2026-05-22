from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.prep_engine import run_prep_session, generate_questions_only
from app.db.database import (
    get_prior_sessions,
    get_weak_areas,
    get_kb_snapshot,
    save_answer,
    update_session_score
)
from app.core.scorer import score_session
from app.core.logger import get_logger
import os

logger = get_logger("api")

router = APIRouter()


# --- Request Models ---

class PrepRequest(BaseModel):
    section_ids: list[int]
    simulate: bool = False


class AnswerRequest(BaseModel):
    session_id: int
    answers: dict[int, str]


class GenerateRequest(BaseModel):
    section_ids: list[int]


class SubmitRequest(BaseModel):
    session_id: int
    questions: list[dict]
    answers: dict[int, str]


# --- Endpoints ---

@router.get("/")
def root():
    return {"message": "Adaptive Document Prep System is running."}


@router.get("/pdf-info")
def get_pdf_info():
    """Get the current PDF filename and display name."""
    pdf_path = "SLATEFALL_DOSSIER.pdf"
    filename = os.path.basename(pdf_path)
    name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()
    return {"filename": filename, "name": name}


@router.get("/sections")
def list_sections():
    """List all available sections in the dossier."""
    from app.core.pdf_parser import extract_sections
    sections = extract_sections("SLATEFALL_DOSSIER.pdf")
    return {
        "sections": [
            {"id": k, "title": v["title"]}
            for k, v in sections.items()
        ]
    }


@router.post("/prep")
def start_prep(request: PrepRequest):
    logger.info(f"API prep request — sections: {request.section_ids}")

    if not request.section_ids:
        logger.warning("Prep request with no section IDs")
        raise HTTPException(status_code=400, detail="No section IDs provided.")

    valid = list(range(1, 11))
    for sid in request.section_ids:
        if sid not in valid:
            logger.warning(f"Invalid section ID requested: {sid}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section ID: {sid}. Must be between 1 and 10."
            )

    try:
        result = run_prep_session(
            section_ids=request.section_ids,
            simulate_answers=request.simulate
        )
        logger.info(f"Prep session completed — session ID: {result['session_id']}")
        return {
            "session_id": result["session_id"],
            "is_adaptive": result["is_adaptive"],
            "questions": result["questions"],
            "scored": result["scored"],
            "kb_snapshot": result["kb_snapshot"]
        }
    except Exception as e:
        logger.error(f"Prep session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def generate_questions(request: GenerateRequest):
    """Generate questions for the UI without collecting answers."""
    logger.info(f"Generate request — sections: {request.section_ids}")

    if not request.section_ids:
        raise HTTPException(status_code=400, detail="No section IDs provided.")

    valid = list(range(1, 11))
    for sid in request.section_ids:
        if sid not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section ID: {sid}. Must be between 1 and 10."
            )

    try:
        prior = get_prior_sessions(request.section_ids)
        is_returning = len(prior) > 0
        weak = get_weak_areas(request.section_ids) if is_returning else []

        result = generate_questions_only(section_ids=request.section_ids)
        logger.info(f"Generated {len(result['questions'])} questions — session {result['session_id']}")

        return {
            "session_id": result["session_id"],
            "is_adaptive": result["is_adaptive"],
            "weak_areas": weak[:5],
            "questions": result["questions"]
        }
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit")
def submit_answers(request: SubmitRequest):
    """Submit user answers for a session."""
    logger.info(f"Submit request — session {request.session_id}")

    if not request.questions or not request.answers:
        raise HTTPException(status_code=400, detail="Questions and answers required.")

    try:
        answers = {int(k): v for k, v in request.answers.items()}
        scored = score_session(request.questions, answers)

        for r in scored["results"]:
            save_answer(r["question_id"], r["user_answer"], r["is_correct"])

        update_session_score(request.session_id, scored["score"], scored["total"])
        kb_snapshot = get_kb_snapshot()

        logger.info(
            f"Session {request.session_id} scored — "
            f"{scored['score']}/{scored['total']} ({scored['score_percent']}%)"
        )

        return {
            "session_id": request.session_id,
            "scored": scored,
            "kb_snapshot": kb_snapshot
        }
    except Exception as e:
        logger.error(f"Submit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{section_id}")
def get_section_history(section_id: int):
    """Get prior prep sessions for a section."""
    sessions = get_prior_sessions([section_id])
    return {"section_id": section_id, "prior_sessions": sessions}


@router.get("/weak-areas")
def get_weak_areas_endpoint(section_ids: str):
    """Get weak areas for given section IDs."""
    try:
        ids = [int(x) for x in section_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section_ids format.")
    weak = get_weak_areas(ids)
    return {"weak_areas": weak}


@router.get("/kb-snapshot")
def kb_snapshot():
    """Get the current knowledge base snapshot (last 5 sessions)."""
    snapshot = get_kb_snapshot()
    return {"kb_snapshot": snapshot}