# Doc Harbour Backend

Python backend scaffold for a single-business document chatbot.

## Status

Folder structure only. API endpoints, database setup, AI calls, dependency installation, and executable tests are not implemented yet. `compose.yaml` is a placeholder, not a runnable database setup.

## Structure

- `app/routes/`: document, chat, and settings endpoints.
- `app/services/`: extraction, chunking, Cloudflare embeddings, retrieval, and provider clients.
- `app/ai/`: LangGraph state, workflow nodes, and prompts.
- `app/config.py`, `database.py`, `models.py`, `schemas.py`: configuration, persistence, and API contracts.
- `tests/`: ingestion and answer test locations; no tests implemented yet.
- `samples/`: fictional sample text and expected answers. PDF/DOCX fixtures are pending.
- `uploads/`: original uploads, excluded from Git except the directory marker.

## Planned behavior

FastAPI + LangGraph, PostgreSQL with pgvector, Cloudflare Workers AI embeddings, and chat-provider BYOK. PDF citations use pages; DOCX/TXT use paragraph/line references. Credentials remain in backend memory for the running session. Document chunks and queries are sent to Cloudflare; retrieved excerpts are sent to the selected chat provider.

Unsupported questions return: “I couldn’t find this information in the uploaded documents”.

Installation, running, testing, deployment, and client handoff instructions will be added with the implementation.
