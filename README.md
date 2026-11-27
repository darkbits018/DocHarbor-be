# Doc Harbour Backend

A local Python API for uploading business documents and storing searchable text chunks. This stage includes FastAPI, PostgreSQL with pgvector enabled, PDF/DOCX/TXT extraction, source references, and chunk persistence. Embeddings, chat, and LangGraph follow next.

## Requirements

Install Python 3.11+ and PostgreSQL 16 or newer with the pgvector extension installed. Installing Python packages requires internet access.

## Set up PostgreSQL

In PowerShell from this folder:

```powershell
Copy-Item .env.example .env
# Edit DATABASE_URL with the username, password, host, port, and database you created.
```

## Install and run the API

Open another PowerShell window in this folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

If PowerShell blocks environment activation, use `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

Interactive API page: http://127.0.0.1:8000/docs. Health check: http://127.0.0.1:8000/api/health.

## Upload the sample

```powershell
curl.exe -F "file=@samples/office-hours.txt" http://127.0.0.1:8000/api/documents
curl.exe http://127.0.0.1:8000/api/documents
```

The API accepts PDF, DOCX, and UTF-8 TXT files up to 20 MB by default. Duplicate filenames return HTTP 409. Original uploads use generated names under `uploads/`; PostgreSQL stores the original filename, text chunks, and page, paragraph, or line references. PDF files need selectable text; OCR is not included.

## Endpoints

- `GET /api/health` — database health.
- `POST /api/documents` — upload one document.
- `GET /api/documents` — list uploaded documents and chunk counts.

Tables are created at API startup and the pgvector extension is enabled for the next stage. Authentication is not implemented; keep this development server local and do not expose it publicly.
