import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert quiz generator. 
You generate Multiple Choice Questions (MCQs) from study material.
You always respond with valid JSON only. No extra text, no markdown, no backticks.
"""


def generate_mcqs(
    section_content: str,
    section_id: int,
    n_questions: int = 5,
    weak_areas: list[dict] = None
) -> list[dict]:
    """
    Generate MCQs from a section of the SLATEFALL dossier.
    
    If weak_areas is provided (returning user), the prompt instructs
    the LLM to focus on those topics the user previously got wrong.
    """

    # Build the adaptive context if we have prior weak areas
    weak_context = ""
    if weak_areas:
        weak_topics = [w["question_text"] for w in weak_areas[:5]]
        weak_context = f"""
IMPORTANT - ADAPTIVE FOCUS:
This user has previously studied this material but got these topics wrong:
{json.dumps(weak_topics, indent=2)}

You MUST:
1. Generate questions that test these weak areas specifically
2. Avoid repeating the exact same questions
3. Approach the same topics from different angles
"""

    user_prompt = f"""
Generate exactly {n_questions} MCQs from the following study material.
Section ID: {section_id}

{weak_context}

STUDY MATERIAL:
{section_content[:4000]}

Respond with a JSON array of exactly {n_questions} objects.
Each object must have exactly these fields:
{{
    "question_text": "the question",
    "options": {{
        "A": "first option",
        "B": "second option", 
        "C": "third option",
        "D": "fourth option"
    }},
    "correct_answer": "A",
    "explanation": "brief explanation of why this answer is correct"
}}

Rules:
- correct_answer must be exactly one of: A, B, C, or D
- All 4 options must be plausible
- Questions must be based strictly on the provided material
- Respond with the JSON array only, nothing else
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    raw = response.choices[0].message.content.strip()

    # Clean up in case LLM adds markdown backticks anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    questions = json.loads(raw)
    return questions


if __name__ == "__main__":
    # Quick test with Section 1 content
    from pdf_parser import extract_sections
    import sys
    sys.path.append(".")

    from app.core.pdf_parser import extract_sections

    sections = extract_sections("SLATEFALL_DOSSIER.pdf")
    section = sections[1]

    print(f"Testing MCQ generation for: {section['title']}\n")
    questions = generate_mcqs(
        section_content=section["content"],
        section_id=1,
        n_questions=3
    )

    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q['question_text']}")
        for letter, option in q["options"].items():
            print(f"  {letter}: {option}")
        print(f"  Answer: {q['correct_answer']}")
        print(f"  Explanation: {q['explanation']}")
        print()