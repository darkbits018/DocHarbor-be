from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.config import UPLOAD_DIR
from app.database import Base, engine
from app import models
from app.routes.documents import router as documents_router

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        raise RuntimeError("Database unavailable. Start PostgreSQL and check DATABASE_URL in your .env file.") from exc
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="Doc Harbour API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(documents_router)

@app.get("/api/health")
def health() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "database": "connected"})
    except SQLAlchemyError:
        return JSONResponse({"status": "error", "database": "unavailable"}, status_code=503)
