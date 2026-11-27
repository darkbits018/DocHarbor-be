import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads")).resolve()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://docharbor:replace-with-local-password@localhost:5432/docharbor")
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_EMBEDDING_MODEL = "@cf/baai/bge-m3"
SETTINGS_ENCRYPTION_KEY = os.getenv("SETTINGS_ENCRYPTION_KEY", "")
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "openai")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_DIMENSIONS = 1024
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
