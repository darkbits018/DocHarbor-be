import asyncio
from sqlalchemy.orm import Session
from app.ai.prompts import SYSTEM_PROMPT, UNSUPPORTED_ANSWER
from app.services.embeddings import embed_texts
from app.services.providers import generate_answer
from app.services.retrieval import search_chunks


def retrieve_node(state: dict) -> dict:
    db: Session = state["db"]
    vector = asyncio.run(embed_texts([state["question"]]))[0]
    return {"evidence": search_chunks(db, vector, limit=5)}


def answer_node(state: dict) -> dict:
    evidence = state.get("evidence", [])
    if not evidence or evidence[0]["distance"] > 0.65:
        return {"answer": UNSUPPORTED_ANSWER}
    context = "\n\n".join(
        f"[{item['document_name']}, {item['reference']}]\n{item['text']}"
        for item in evidence
    )
    answer = asyncio.run(generate_answer(
        state["provider"], state["model"], state["api_key"],
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": f"Document excerpts:\n{context}\n\nQuestion: {state['question']}"}],
        state.get("base_url", ""),
    ))
    valid_sources = {f"[{item['document_name']}, {item['reference']}]" for item in evidence}
    if not any(source in answer for source in valid_sources):
        return {"answer": UNSUPPORTED_ANSWER}
    return {"answer": answer}
