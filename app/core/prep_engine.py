import json
from app.core.pdf_parser import extract_sections
from app.core.llm import generate_mcqs
from app.core.scorer import score_session, display_results
from app.db.database import (
    create_session,
    save_question,
    save_answer,
    update_session_score,
    get_weak_areas,
    get_prior_sessions,
    get_kb_snapshot
)

PDF_PATH = "SLATEFALL_DOSSIER.pdf"
N_QUESTIONS_PER_SECTION = 5


def run_prep_session(
    section_ids: list[int],
    simulate_answers: bool = False,
    simulate_wrong_ratio: float = 0.4
) -> dict:
    """
    Run a full prep session for the given section IDs.

    simulate_answers: if True, auto-generates answers (for Scenario B output)
    simulate_wrong_ratio: how many answers to get wrong in simulation

    Returns the full session result including kb_snapshot.
    """

    print("\n" + "="*50)
    print(f"PREP SESSION — Sections: {section_ids}")
    print("="*50)

    # STEP 1 — Check for prior history
    prior_sessions = get_prior_sessions(section_ids)
    is_returning = len(prior_sessions) > 0

    if is_returning:
        print(f"Returning user detected — {len(prior_sessions)} prior session(s) found.")
        print("Adaptive mode: ON — focusing on weak areas.\n")
    else:
        print("First time studying these sections.")
        print("Adaptive mode: OFF — generating fresh questions.\n")

    # STEP 2 — Load PDF sections
    all_sections = extract_sections(PDF_PATH)

    # STEP 3 — Get weak areas for adaptive prompting
    weak_areas = get_weak_areas(section_ids) if is_returning else []

    # STEP 4 — Create session in DB
    session_id = create_session(section_ids)
    print(f"Session ID: {session_id}\n")

    # STEP 5 — Generate MCQs for each section
    all_questions = []

    for section_id in section_ids:
        if section_id not in all_sections:
            print(f"Section {section_id} not found in PDF, skipping.")
            continue

        section = all_sections[section_id]
        print(f"Generating questions for Section {section_id}: {section['title']}...")

        # Filter weak areas to this section only
        section_weak = [w for w in weak_areas if w["section_id"] == section_id]

        questions = generate_mcqs(
            section_content=section["content"],
            section_id=section_id,
            n_questions=N_QUESTIONS_PER_SECTION,
            weak_areas=section_weak if section_weak else None
        )

        # Save each question to DB
        for q in questions:
            qid = save_question(session_id, section_id, q)
            q["id"] = qid
            q["section_id"] = section_id
            all_questions.append(q)

    print(f"\nGenerated {len(all_questions)} questions total.\n")

    # STEP 6 — Collect answers
    user_answers = {}

    if simulate_answers:
        # Auto-simulate answers for Scenario B
        import random
        print("Simulating user answers...\n")
        for i, q in enumerate(all_questions):
            options = list(q["options"].keys())
            if random.random() > simulate_wrong_ratio:
                # correct answer
                user_answers[q["id"]] = q["correct_answer"]
            else:
                # wrong answer — pick a different option
                wrong_options = [o for o in options if o != q["correct_answer"]]
                user_answers[q["id"]] = random.choice(wrong_options)
    else:
        # Real interactive mode — ask user in terminal
        print("Answer each question (A/B/C/D):\n")
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

    # STEP 7 — Score the session
    scored = score_session(all_questions, user_answers)

    # STEP 8 — Save answers to DB
    for r in scored["results"]:
        save_answer(r["question_id"], r["user_answer"], r["is_correct"])

    # STEP 9 — Update session score
    update_session_score(session_id, scored["score"], scored["total"])

    # STEP 10 — Display results
    display_results(scored)

    # STEP 11 — Get KB snapshot
    kb_snapshot = get_kb_snapshot()

    print(f"Session complete. Score: {scored['score']}/{scored['total']}")
    print(f"KB snapshot captured ({len(kb_snapshot)} session(s)).\n")

    return {
        "session_id": session_id,
        "questions": all_questions,
        "scored": scored,
        "kb_snapshot": kb_snapshot,
        "is_adaptive": is_returning
    }