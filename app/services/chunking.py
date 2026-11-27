from app.config import CHUNK_OVERLAP, CHUNK_SIZE
from app.services.extraction import ExtractedSection

def chunk_sections(sections: list[ExtractedSection]) -> list[tuple[str, str]]:
    chunks = []
    for section in sections:
        text = section.text.strip()
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                chunks.append((piece, section.reference))
            if end == len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks
