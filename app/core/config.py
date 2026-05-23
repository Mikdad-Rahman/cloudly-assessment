import os

# Active PDF path — can be changed at runtime via /upload-pdf
_active_pdf_path = os.getenv("PDF_PATH", "SLATEFALL_DOSSIER.pdf")


def get_pdf_path() -> str:
    return _active_pdf_path


def set_pdf_path(path: str):
    global _active_pdf_path
    _active_pdf_path = path