from dataclasses import dataclass
from pathlib import Path
from docx import Document as WordDocument
from pypdf import PdfReader

@dataclass
class ExtractedSection:
    reference: str
    text: str

def extract_sections(path: Path, file_type: str) -> list[ExtractedSection]:
    if file_type == ".pdf":
        return [ExtractedSection(f"Page {n}", page.extract_text() or "") for n, page in enumerate(PdfReader(str(path)).pages, 1)]
    if file_type == ".docx":
        doc = WordDocument(str(path))
        return [ExtractedSection(f"Paragraph {n}", p.text) for n, p in enumerate(doc.paragraphs, 1) if p.text.strip()]
    if file_type == ".txt":
        return [ExtractedSection(f"Line {n}", line) for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1) if line.strip()]
    raise ValueError("Unsupported file type")
