from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.prep_engine import run_prep_session
from app.db.database import (
    get_prior_sessions,
    get_weak_areas,
    get_kb_snapshot
)

router = APIRouter()


# --- Request Models ---

class PrepRequest(BaseModel):
    section_ids: list[int]
    simulate: bool = False


class AnswerRequest(BaseModel):
    session_id: int
    answers: dict[int, str]  # question_id -> answer letter


# --- Endpoints ---

@router.get("/")
def root():
    return {"message": "Adaptive Document Prep System is running."}


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
    """
    Start a prep session for the given section IDs.
    If simulate=True, answers are auto-generated.
    """
    if not request.section_ids:
        raise HTTPException(status_code=400, detail="No section IDs provided.")

    valid = list(range(1, 11))
    for sid in request.section_ids:
        if sid not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section ID: {sid}. Must be between 1 and 10."
            )

    result = run_prep_session(
        section_ids=request.section_ids,
        simulate_answers=request.simulate
    )

    return {
        "session_id": result["session_id"],
        "is_adaptive": result["is_adaptive"],
        "questions": result["questions"],
        "scored": result["scored"],
        "kb_snapshot": result["kb_snapshot"]
    }


@router.get("/history/{section_id}")
def get_section_history(section_id: int):
    """Get prior prep sessions for a section."""
    sessions = get_prior_sessions([section_id])
    return {"section_id": section_id, "prior_sessions": sessions}


@router.get("/weak-areas")
def get_weak_areas_endpoint(section_ids: str):
    """
    Get weak areas for given section IDs.
    Pass section_ids as comma separated e.g. /weak-areas?section_ids=1,2,3
    """
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