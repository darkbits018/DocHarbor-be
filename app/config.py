import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://docharbor:replace-with-local-password@localhost:5432/docharbor")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
