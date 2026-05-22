import os
import json
from groq import Groq
from dotenv import load_dotenv
from app.core.logger import get_logger

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
logger = get_logger("llm")

SYSTEM_PROMPT = """You are an expert quiz generator.
You generate Multiple Choice Questions (MCQs) from study material.
You always respond with valid JSON only. No extra text, no markdown, no backticks.
"""


def chunk_section(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Split section text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def get_relevant_chunks(
    text: str,
    weak_areas: list[dict] = None,
    max_chars: int = 4000
) -> str:
    """
    Keyword-based fallback retrieval.
    Used when RAG is not available.
    """
    chunks = chunk_section(text)

    if not weak_areas or len(text) <= max_chars:
        return text[:max_chars]

    keywords = []
    for w in weak_areas:
        words = [
            word.lower()
            for word in w["question_text"].split()
            if len(word) > 4
        ]
        keywords.extend(words)

    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for kw in keywords if kw in chunk_lower)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    selected = ""
    for score, chunk in scored_chunks:
        if len(selected) + len(chunk) <= max_chars:
            selected += chunk + "\n\n"
        else:
            break

    return selected.strip() if selected else text[:max_chars]


def get_rag_context(
    section_ids: list[int],
    weak_areas: list[dict] = None,
    section_content: str = None
) -> str:
    """
    Get relevant context using RAG (ChromaDB vector search).
    Falls back to keyword chunking if RAG fails.
    """
    try:
        from app.core.rag import retrieve_relevant_chunks

        # Build query from weak areas or use generic query
        if weak_areas:
            query = " ".join([w["question_text"] for w in weak_areas[:3]])
        else:
            query = "key facts, limits, procedures, and important details"

        context = retrieve_relevant_chunks(
            query=query,
            section_ids=section_ids,
            n_results=6
        )

        if context:
            logger.info(f"RAG retrieved context for sections {section_ids}")
            return context

    except Exception as e:
        logger.warning(f"RAG retrieval failed, falling back to chunking: {e}")

    # Fallback to keyword chunking
    if section_content:
        return get_relevant_chunks(section_content, weak_areas)

    return ""


def generate_mcqs(
    section_content: str,
    section_id: int,
    n_questions: int = 5,
    weak_areas: list[dict] = None
) -> list[dict]:
    """
    Generate MCQs using RAG-retrieved context.
    Falls back to keyword chunking if RAG unavailable.
    """
    logger.info(
        f"Generating {n_questions} MCQs for section {section_id} "
        f"(adaptive={'yes' if weak_areas else 'no'})"
    )

    # Get context via RAG
    context = get_rag_context(
        section_ids=[section_id],
        weak_areas=weak_areas,
        section_content=section_content
    )

    # Build adaptive focus instructions
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

STUDY MATERIAL (retrieved via semantic search):
{context}

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

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        questions = json.loads(raw)
        logger.info(
            f"Successfully parsed {len(questions)} questions for section {section_id}"
        )
        return questions

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON for section {section_id}: {e}")
        raise ValueError(f"LLM returned invalid JSON for section {section_id}: {e}")

    except Exception as e:
        logger.error(f"LLM API call failed for section {section_id}: {e}")
        raise