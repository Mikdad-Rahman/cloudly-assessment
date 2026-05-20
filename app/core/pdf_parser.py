import fitz  # this is PyMuPDF
import re
from pathlib import Path


def load_pdf_text(pdf_path: str) -> str:
    """
    Read the entire PDF and return all text as a single string.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text


def extract_sections(pdf_path: str) -> dict[int, dict]:
    """
    Split the PDF text into its 10 sections.
    Returns a dict like:
    {
        1: {"title": "Identity, Background...", "content": "..."},
        2: {"title": "Powers, Abilities...", "content": "..."},
        ...
    }
    """
    full_text = load_pdf_text(pdf_path)

    # This pattern matches "Section 1.", "Section 2." etc.
    section_pattern = re.compile(
        r'(Section\s+(\d+)\.\s+([^\n]+))', re.IGNORECASE
    )

    matches = list(section_pattern.finditer(full_text))

    sections = {}

    for i, match in enumerate(matches):
        section_num = int(match.group(2))
        section_title = match.group(3).strip()
        start = match.start()

        # Content goes from this match to the next section (or end of text)
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(full_text)

        content = full_text[start:end].strip()

        sections[section_num] = {
            "title": section_title,
            "content": content
        }

    return sections


if __name__ == "__main__":
    # Test the parser directly
    pdf_path = "SLATEFALL_DOSSIER.pdf"
    sections = extract_sections(pdf_path)

    print(f"Found {len(sections)} sections:\n")
    for num, data in sections.items():
        preview = data['content'][:100].replace('\n', ' ')
        print(f"Section {num}: {data['title']}")
        print(f"  Preview: {preview}...")
        print()
