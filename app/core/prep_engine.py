import os
import json
from app.core.pdf_parser import extract_sections
from app.core.llm import generate_mcqs
from app.core.scorer import score_session, display_results
from app.core.config import get_pdf_path
from app.db.database import (
    create_session,
    save_question,
    save_answer,
    update_session_score,
    get_weak_areas,
    get_prior_sessions,
    get_kb_snapshot
)
from app.core.logger import get_logger
logger = get_logger("prep_engine")

N_QUESTIONS_PER_SECTION = 5


def run_prep_session(
    section_ids: list[int],
    simulate_answers: bool = False,
    simulate_wrong_ratio: float = 0.4
) -> dict:

    pdf_path = get_pdf_path()
    pdf_name = os.path.basename(pdf_path)
    logger.info(f"Starting prep session — sections: {section_ids} — PDF: {pdf_name}")

    prior_sessions = get_prior_sessions(section_ids)
    is_returning = len(prior_sessions) > 0

    if is_returning:
        logger.info(f"Returning user — {len(prior_sessions)} prior session(s) found. Adaptive mode ON.")
    else:
        logger.info("First time studying these sections. Adaptive mode OFF.")

    all_sections = extract_sections(pdf_path)
    weak_areas = get_weak_areas(section_ids) if is_returning else []
    session_id = create_session(section_ids, pdf_name)
    logger.info(f"Created session ID: {session_id}")

    all_questions = []

    for section_id in section_ids:
        if section_id not in all_sections:
            logger.warning(f"Section {section_id} not found in PDF — skipping")
            continue

        section = all_sections[section_id]
        logger.info(f"Generating questions for Section {section_id}: {section['title']}")

        section_weak = [w for w in weak_areas if w["section_id"] == section_id]

        try:
            questions = generate_mcqs(
                section_content=section["content"],
                section_id=section_id,
                n_questions=N_QUESTIONS_PER_SECTION,
                weak_areas=section_weak if section_weak else None
            )
        except Exception as e:
            logger.error(f"Failed to generate questions for section {section_id}: {e}")
            continue

        for q in questions:
            qid = save_question(session_id, section_id, q)
            q["id"] = qid
            q["section_id"] = section_id
            all_questions.append(q)

    logger.info(f"Generated {len(all_questions)} questions total for session {session_id}")

    user_answers = {}

    if simulate_answers:
        import random
        logger.info("Simulating user answers")
        for q in all_questions:
            options = list(q["options"].keys())
            if random.random() > simulate_wrong_ratio:
                user_answers[q["id"]] = q["correct_answer"]
            else:
                wrong_options = [o for o in options if o != q["correct_answer"]]
                user_answers[q["id"]] = random.choice(wrong_options)
    else:
        print("\nAnswer each question (A/B/C/D):\n")
        for i, q in enumerate(all_questions, 1):
            print(f"Q{i} [Section {q['section_id']}]: {q['question_text']}")
            for letter, option in q["options"].items():
                print(f"  {letter}: {option}")
            while True:
                ans = input("Your answer: ").strip().upper()
                if ans in ["A", "B", "C", "D"]:
                    user_answers[q["id"]] = ans
                    break
                print("Please enter A, B, C, or D")
            print()

    scored = score_session(all_questions, user_answers)

    for r in scored["results"]:
        save_answer(r["question_id"], r["user_answer"], r["is_correct"])

    update_session_score(session_id, scored["score"], scored["total"])
    display_results(scored)

    kb_snapshot = get_kb_snapshot()

    logger.info(
        f"Session {session_id} complete — "
        f"Score: {scored['score']}/{scored['total']} "
        f"({scored['score_percent']}%)"
    )

    return {
        "session_id": session_id,
        "questions": all_questions,
        "scored": scored,
        "kb_snapshot": kb_snapshot,
        "is_adaptive": is_returning
    }


def generate_questions_only(section_ids: list[int]) -> dict:
    """Only generate questions without collecting answers. Used by the UI."""
    pdf_path = get_pdf_path()
    pdf_name = os.path.basename(pdf_path)

    all_sections = extract_sections(pdf_path)
    prior_sessions = get_prior_sessions(section_ids)
    is_returning = len(prior_sessions) > 0
    weak_areas = get_weak_areas(section_ids) if is_returning else []
    session_id = create_session(section_ids, pdf_name)

    all_questions = []
    for section_id in section_ids:
        if section_id not in all_sections:
            continue
        section = all_sections[section_id]
        section_weak = [w for w in weak_areas if w["section_id"] == section_id]
        questions = generate_mcqs(
            section_content=section["content"],
            section_id=section_id,
            n_questions=N_QUESTIONS_PER_SECTION,
            weak_areas=section_weak if section_weak else None
        )
        for q in questions:
            qid = save_question(session_id, section_id, q)
            q["id"] = qid
            q["section_id"] = section_id
            all_questions.append(q)

    return {
        "session_id": session_id,
        "questions": all_questions,
        "is_adaptive": is_returning
    }