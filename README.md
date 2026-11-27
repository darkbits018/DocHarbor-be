# Doc Harbour Backend

A local Python API for uploading business documents, storing text chunks and Cloudflare embeddings in PostgreSQL with pgvector, and answering questions through LangGraph with citations and an unsupported-answer fallback.

## Requirements

Install Python 3.11 or newer. Development uses a free hosted PostgreSQL database from Neon; you do not need a local database server. Installing Python packages requires internet access.

## Set up the hosted development database

In PowerShell from this folder:

```powershell
1. Create a free PostgreSQL project at [Neon](https://neon.com/).
2. In the Neon SQL Editor, run `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Copy the database connection string from the Neon dashboard.
4. In PowerShell, copy the example settings and edit `.env`:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

5. Put the Neon connection URL into `DATABASE_URL`. Change its scheme to `postgresql+psycopg://` and keep `sslmode=require`.
6. In the Cloudflare dashboard, create a Workers AI API token with Workers AI access, then copy your account ID and token into `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` in `.env`. Never commit or share `.env`.
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

The API accepts PDF, DOCX, and UTF-8 TXT files up to 20 MB by default. Duplicate filenames return HTTP 409. Original uploads use generated names under `uploads/`; PostgreSQL stores the original filename, text chunks, Cloudflare BGE-M3 embeddings, and page, paragraph, or line references. PDF files need selectable text; OCR is not included. Cloudflare Workers AI usage may incur charges; check the account's current limits and pricing.

## Endpoints

- `GET /api/health` — database health.
- `POST /api/documents` — upload one document.
- `GET /api/documents` — list uploaded documents and chunk counts.
- `DELETE /api/documents/{id}` — delete a document, its chunks, embeddings, and local original.
- `PUT /api/settings` / `GET /api/settings` — accept the provider, model, API key, optional OpenAI-compatible base URL, and owner contact URL from the frontend BYOK form. Chat credentials are not environment settings; the backend keeps them in memory only for the current process and never returns the key.
- `POST /api/chat` — ask a question and receive an answer with document references.

Supported chat providers: OpenAI, Anthropic, and Google. Model names are entered as provider-specific values. The answer workflow retrieves up to five chunks and returns the exact unsupported-answer message when the closest result is below the configured relevance threshold or the model omits valid source citations. This citation check is a guardrail, not a guarantee that every generated claim is entailed by its source.
- Similarity retrieval is available in `app.services.retrieval.search_chunks` and will be used by the upcoming chat endpoint.

Tables are created at API startup. `DATABASE_URL` is the only database setting the app needs, so later you can point it at a local PostgreSQL + pgvector installation by changing that value. Authentication is not implemented; keep this development server local and do not expose it publicly. Do not put real client documents in the free development database.
