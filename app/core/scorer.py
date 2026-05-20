def score_session(questions: list[dict], user_answers: dict) -> dict:
    """
    Score a prep session.
    
    questions: list of MCQ dicts with question_id, correct_answer etc.
    user_answers: dict mapping question_id -> user's answer e.g. {1: "A", 2: "C"}
    
    Returns a results dict with score, total, and per-question breakdown.
    """
    results = []
    correct_count = 0

    for q in questions:
        qid = q["id"]
        correct = q["correct_answer"]
        user_ans = user_answers.get(qid, None)
        is_correct = user_ans == correct

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": qid,
            "question_text": q["question_text"],
            "options": q["options"],
            "correct_answer": correct,
            "user_answer": user_ans,
            "is_correct": is_correct,
            "explanation": q["explanation"]
        })

    total = len(questions)
    score_percent = round((correct_count / total) * 100) if total > 0 else 0

    return {
        "score": correct_count,
        "total": total,
        "score_percent": score_percent,
        "results": results
    }


def display_results(scored: dict):
    """
    Print a human-readable results summary to the terminal.
    """
    print("\n" + "="*50)
    print("SESSION RESULTS")
    print("="*50)
    print(f"Score: {scored['score']}/{scored['total']} ({scored['score_percent']}%)\n")

    for i, r in enumerate(scored["results"], 1):
        status = "✓ CORRECT" if r["is_correct"] else "✗ WRONG"
        print(f"Q{i}: {r['question_text']}")
        print(f"Your answer: {r['user_answer']} | Correct: {r['correct_answer']} | {status}")
        if not r["is_correct"]:
            print(f"Explanation: {r['explanation']}")
        print()