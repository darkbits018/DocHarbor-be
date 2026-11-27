import asyncio
import logging
import re
import time
from sqlalchemy.orm import Session
from app.ai.prompts import SYSTEM_PROMPT, UNSUPPORTED_ANSWER
from app.services.embeddings import embed_texts
from app.services.providers import generate_answer
from app.services.retrieval import search_chunks

logger = logging.getLogger(__name__)


def _citation_matches(answer: str, item: dict) -> bool:
    """Accept common citation punctuation/casing while still requiring file and page."""
    normalized_answer = re.sub(r"[^a-z0-9]+", " ", answer.casefold()).strip()
    filename = item["document_name"]
    name_candidates = {filename, filename.rsplit(".", 1)[0]}
    has_document = any(
        re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip() in normalized_answer
        for name in name_candidates
    )
    reference = item["reference"]
    page_match = re.fullmatch(r"page\s+(\d+)", reference, flags=re.IGNORECASE)
    if page_match:
        number = page_match.group(1)
        reference_candidates = {f"page {number}", f"p {number}", f"pg {number}"}
    else:
        reference_candidates = {reference}
    has_reference = any(
        re.sub(r"[^a-z0-9]+", " ", ref.casefold()).strip() in normalized_answer
        for ref in reference_candidates
    )
    return has_document and has_reference


def retrieve_node(state: dict) -> dict:
    db: Session = state["db"]
    started = time.perf_counter()
    logger.info("Chat retrieval started: question_chars=%d", len(state["question"]))
    vector = asyncio.run(embed_texts([state["question"]]))[0]
    logger.info("Query embedding created: dimensions=%d", len(vector))
    evidence = search_chunks(db, vector, limit=5)
    logger.info("Chat retrieval finished: elapsed_ms=%.1f", (time.perf_counter() - started) * 1000)
    return {"evidence": evidence}


def answer_node(state: dict) -> dict:
    evidence = state.get("evidence", [])
    if not evidence or evidence[0]["distance"] > 0.65:
        reason = "no_candidates" if not evidence else "nearest_candidate_over_threshold"
        nearest = evidence[0]["distance"] if evidence else None
        logger.info(
            "Answer skipped: reason=%s nearest_distance=%s threshold=0.65",
            reason, f"{nearest:.4f}" if nearest is not None else "none",
        )
        return {"answer": UNSUPPORTED_ANSWER}
    logger.info(
        "Answer generation started: provider=%s model=%s evidence_count=%d nearest_distance=%.4f",
        state["provider"], state["model"], len(evidence), evidence[0]["distance"],
    )
    started = time.perf_counter()
    context = "\n\n".join(
        f"[{item['document_name']}, {item['reference']}]\n{item['text']}"
        for item in evidence
    )
    allowed_labels = sorted({f"[{item['document_name']}, {item['reference']}]" for item in evidence})
    answer = asyncio.run(generate_answer(
        state["provider"], state["model"], state["api_key"],
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": f"Allowed source labels (copy one exactly when answering): {', '.join(allowed_labels)}\n\nDocument excerpts:\n{context}\n\nQuestion: {state['question']}"}],
        state.get("base_url", ""),
    ))
    logger.info(
        "Answer generation finished: elapsed_ms=%.1f answer_chars=%d",
        (time.perf_counter() - started) * 1000, len(answer),
    )
    cited_evidence = [item for item in evidence if _citation_matches(answer, item)]
    logger.info(
        "Citation validation: matched=%d retrieved=%d",
        len(cited_evidence), len(evidence),
    )
    if not cited_evidence:
        logger.warning("Answer rejected: response did not cite a retrieved document and source reference")
        return {"answer": UNSUPPORTED_ANSWER}
    canonical_sources = sorted({f"[{item['document_name']}, {item['reference']}]" for item in cited_evidence})
    if not any(source in answer for source in canonical_sources):
        answer = f"{answer.rstrip()}\n\nSources: {', '.join(canonical_sources)}"
    logger.info("Answer accepted: validated_source_count=%d", len(canonical_sources))
    return {"answer": answer}
