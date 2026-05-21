import os
import json
from groq import Groq
from dotenv import load_dotenv
from app.core.logger import get_logger
logger = get_logger("llm")

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert quiz generator. 
You generate Multiple Choice Questions (MCQs) from study material.
You always respond with valid JSON only. No extra text, no markdown, no backticks.
"""

def chunk_section(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """
    Split section text into overlapping chunks.
    
    chunk_size: characters per chunk
    overlap: characters shared between consecutive chunks
    so context isn't lost at boundaries
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # overlap keeps context
        
    return chunks


def get_relevant_chunks(
    text: str,
    weak_areas: list[dict] = None,
    max_chars: int = 4000
) -> str:
    """
    Smartly select the most relevant chunks from a section.
    
    If we have weak areas, prioritize chunks containing
    keywords from those weak topics.
    If no weak areas, just take the first max_chars.
    """
    chunks = chunk_section(text)
    
    # If no weak areas or text is short enough, return as much as fits
    if not weak_areas or len(text) <= max_chars:
        return text[:max_chars]
    
    # Extract keywords from weak area questions
    keywords = []
    for w in weak_areas:
        # Pull meaningful words (longer than 4 chars) from wrong questions
        words = [
            word.lower() 
            for word in w["question_text"].split() 
            if len(word) > 4
        ]
        keywords.extend(words)
    
    # Score each chunk by how many keywords it contains
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for kw in keywords if kw in chunk_lower)
        scored_chunks.append((score, chunk))
    
    # Sort by score — highest relevance first
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Build final content up to max_chars
    selected = ""
    for score, chunk in scored_chunks:
        if len(selected) + len(chunk) <= max_chars:
            selected += chunk + "\n\n"
        else:
            break
    
    return selected.strip() if selected else text[:max_chars]

def generate_mcqs(
    section_content: str,
    section_id: int,
    n_questions: int = 5,
    weak_areas: list[dict] = None
) -> list[dict]:
    
    logger.info(
        f"Generating {n_questions} MCQs for section {section_id} "
        f"(adaptive={'yes' if weak_areas else 'no'})"
    )

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
{get_relevant_chunks(section_content, weak_areas)}

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

    try:
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
        logger.debug(f"LLM raw response length: {len(raw)} chars")

        # Clean markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        questions = json.loads(raw)
        logger.info(f"Successfully parsed {len(questions)} questions for section {section_id}")
        return questions

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response for section {section_id}: {e}")
        raise ValueError(f"LLM returned invalid JSON for section {section_id}: {e}")

    except Exception as e:
        logger.error(f"LLM API call failed for section {section_id}: {e}")
        raise


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