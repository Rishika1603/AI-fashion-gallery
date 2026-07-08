import ast
import os
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv
from sqlalchemy import inspect as sqlalchemy_inspect
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

try:
    from .config import (
        AppConfig,
        get_config,
    )
except ImportError:  # pragma: no cover - standalone execution
    from config import (
        AppConfig,
        get_config,
    )

logger = logging.getLogger(__name__)


class OrchestratorState(TypedDict):
    """Shared graph state passed between nodes."""

    messages: Annotated[Sequence[Any], add_messages]
    user_query: str
    session_id: Optional[str]
    request_metadata: Dict[str, Any]
    research_findings: Optional[str]
    evidence_ids: Optional[List[str]]
    final_response: Optional[str]
    metadata: Dict[str, Any]


class OrchestrationResult:
    """Value object returned by the orchestrator."""

    def __init__(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.response = response
        self.metadata = metadata or {}


class Orchestrator:
    """Minimal multi-agent orchestrator using LangGraph."""

    def __new__(cls, config: Optional[AppConfig] = None) -> "Orchestrator":
        """Return an instance backed by a module-level compiled graph."""
        instance = super().__new__(cls)
        instance._config = config or get_config()
        return instance

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        if getattr(self, "_config", None) is None:
            self._config = config or get_config()
        self._graph = _build_graph()

    async def run(self, user_query: str, session_id: Optional[str] = None, request_metadata: Optional[Dict[str, Any]] = None) -> OrchestrationResult:
        state: OrchestratorState = {
            "messages": [("user", user_query)],
            "user_query": user_query,
            "session_id": session_id,
            "request_metadata": request_metadata or {},
            "research_findings": None,
            "evidence_ids": None,
            "final_response": None,
            "metadata": {},
        }
        outcome = await self._graph.ainvoke(state)
        response = outcome.get("final_response") or outcome.get("messages", [""])[-1]
        return OrchestrationResult(response=response or "", metadata=outcome.get("metadata", {}))


def _build_graph():
    builder = StateGraph(OrchestratorState)
    builder.add_node("researcher", _researcher_node)
    builder.add_node("synthesizer", _synthesizer_node)

    builder.set_entry_point("researcher")
    builder.add_conditional_edges(
        "researcher",
        _after_researcher,
        {
            "synthesizer": "synthesizer",
            "synthesizer_complete": "synthesizer",
            "stub": "synthesizer",
        },
    )
    builder.add_conditional_edges(
        "synthesizer",
        _after_synthesizer,
        {
            "researcher": "researcher",
            END: END,
            "stub": END,
        },
    )
    return builder.compile()


async def _researcher_node(state: OrchestratorState) -> OrchestratorState:
    config = get_config()
    user_query = state["user_query"]

    logger.info("Running researcher for user query: %s", user_query)

    vector_findings = None
    db_findings = None

    try:
        vector_findings = await _research_vector_store(user_query)
    except Exception as exc:
        logger.warning("Vector store research failed: %s", exc, exc_info=True)

    if vector_findings is None:
        try:
            db_findings = await _research_database(user_query)
        except Exception as exc:
            logger.warning("Database research failed: %s", exc, exc_info=True)

    research_findings = _format_research_findings(user_query, vector_findings, db_findings)
    evidence_payload = vector_findings if vector_findings is not None else db_findings

    return _append_state(state, {
        "research_findings": research_findings,
        "evidence_ids": _extract_evidence_ids(evidence_payload),
    })

async def _synthesizer_node(state: OrchestratorState) -> OrchestratorState:
    config = get_config()
    user_query = state["user_query"]
    research_findings = state.get("research_findings")

    metadata = dict(state.get("metadata", {}))

    if research_findings is None:
        response = _fallback_response(user_query, metadata)
        return _append_state(state, {"final_response": response, "metadata": metadata})

    prompt = (
        "You are a style-focused shopping assistant for an online fashion gallery.\n\n"
        f"Question: {user_query}\n\n"
        f"Findings:\n{research_findings}\n\n"
        "Use the findings above to ground your answer. Prefer the most relevant item(s), "
        "note price ranges and categories, and mention stock if available. "
        "If nothing looks like a good match, say so. "
        "Keep the tone helpful and concise. Do not mention unavailable or unrelated items.\n"
    )

    if metadata.get("retry_reason") == "insufficient_evidence":
        prompt += "Priority: weaken uncertainty conservatively and either clearly identify the best available match or state plainly that no strong match exists.\n"

    response = await _call_llm(prompt)
    metadata.setdefault("llm_model", getattr(config.genai, "model_name", "unknown"))
    metadata.setdefault("research_sources", " vector_store" if state.get("evidence_ids") else "database")

    return _append_state(state, {"final_response": response, "metadata": metadata})

def _after_researcher(state: OrchestratorState) -> str:
    metadata = dict(state.get("metadata", {}))
    findings = state.get("research_findings")
    fallback_reason = metadata.get("researcher_fallback_reason")

    if findings:
        metadata.setdefault("research_sources", "vector_store")
        metadata.pop("researcher_fallback_reason", None)
    elif fallback_reason:
        metadata.setdefault("research_sources", f"database:{fallback_reason}")
    else:
        metadata.setdefault("research_sources", "database:empty")

    state["metadata"] = metadata

    if findings:
        return "synthesizer"
    return "stub"

def _after_synthesizer(state: OrchestratorState) -> str:
    metadata = dict(state.get("metadata", {}))
    retry_reason = metadata.pop("synthesizer_retry_reason", None)

    if retry_reason:
        metadata["retry_reason"] = retry_reason
        state["metadata"] = metadata
        return "researcher"

    return END


async def _call_llm(prompt: str) -> str:
    config = get_config()
    if not config.genai:
        raise RuntimeError("No LLM configuration available. Set GEMINI_API_KEY and model_name.")

    try:
        import google.genai as genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("google-genai is required for the orchestrator.") from exc

    genai_client = genai.Client(api_key=config.genai.api_key)
    response = await genai_client.aio.models.generate_content(
        model=config.genai.model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError(f"LLM returned an empty response for prompt: {prompt!r}")
    return text


async def _research_vector_store(user_query: str):
    from .vector_store import query_vectors_async
    from .embeddings import get_text_embedding_async, normalize_score
    from starlette.concurrency import run_in_threadpool

    embedding = await get_text_embedding_async(user_query)
    matches = await query_vectors_async(query_embedding=embedding, top_k=5)
    if not matches:
        return None
    return _normalize_vector_results(matches)


def _normalize_vector_results(matches: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    seen = set()

    for match in matches:
        match_id = match.get("id")
        if match_id is None:
            continue
        key = str(match_id)

        metadata = match.get("metadata") or {}
        metadata.setdefault("match_score", match.get("score"))
        try:
            metadata["match_score_pct"] = normalize_score(float(match.get("score", 0.0)))
        except Exception:
            metadata["match_score_pct"] = None

        if key not in seen:
            seen.add(key)
            results.append({"id": key, "metadata": metadata})

    return results or None


def _research_database_sync(raw_values):
    from .database import SessionLocal
    from .models import Product

    user_query = raw_values.get("user_query", "")

    session = SessionLocal()
    try:
        query = session.query(Product)
        if user_query:
            query = query.filter(Product.name.ilike(f"%{user_query}%"))
        rows = query.limit(10).all()
        if not rows:
            return {
                "fallback_reason": "empty",
                "results": [],
            }
        return {
            "fallback_reason": None,
            "results": [_serialize_product(row) for row in rows],
        }
    finally:
        session.close()


async def _research_database(user_query: str):
    from starlette.concurrency import run_in_threadpool
    payload = await run_in_threadpool(_research_database_sync, {"user_query": user_query})
    return payload

def _serialize_product(product) -> Dict[str, Any]:
    return {
        "id": str(product.id),
        "name": product.name,
        "category": product.category,
        "price_min": product.price_min,
        "price_max": product.price_max,
        "in_stock": int(product.in_stock or 0),
        "image_url": product.image_url,
        "social_label": getattr(product, "social_label", None),
        "likes": int(product.likes or 0),
        "style_code": getattr(product, "style_code", None),
        "color_swatches": getattr(product, "color_swatches", None),
    }


def _fallback_response(user_query: str, metadata: Dict[str, Any]) -> str:
    fallback_reason = metadata.get("researcher_fallback_reason")
    if fallback_reason == "unsupported_query_type":
        return (
            "For this question, only catalog lookups are supported right now. "
            "Try describing a garment or asking what is in stock."
        )
    if fallback_reason == "empty":
        return (
            "I searched the fashion gallery catalog but did not find a strong match for that request. "
            "Try another style, color, or category."
        )
    return (
        "I could not research that right now. Please try again, or share more details about the garment you want."
    )


def _format_research_findings(user_query: str, vector_findings: Optional[List[Dict[str, Any]]], database_findings: Optional[Dict[str, Any]]) -> str:
    if vector_findings is not None:
        lines: List[str] = ["vector_store_findings:"]
        for entry in vector_findings:
            line = _vector_entry_as_text(entry)
            lines.append(line)
        return "\n".join(lines)

    if database_findings is not None:
        lines = ["database_findings:"]
        results = database_findings.get("results") or []
        for entry in results:
            line = _database_entry_as_text(entry)
            lines.append(line)
        if not lines[1:]:
            lines.append("No matching rows.")
        return "\n".join(lines)

    return "No findings from researcher."


def _vector_entry_as_text(entry: Dict[str, Any]) -> str:
    metadata = entry.get("metadata", {}) or {}
    score_pct = metadata.get("match_score_pct")
    score_pct_text = f"{score_pct}%" if isinstance(score_pct, (int, float)) else "unknown"
    return (
        "- [{entry_id}] {name}, category: {category}, price: {price_min} to {price_max}, "
        "stock: {stock}, match: {match}%, likes: {likes}, style_code: {style_code}"
    ).format(
        entry_id=entry.get("id"),
        name=metadata.get("name", "Unknown"),
        category=metadata.get("category", "Unknown"),
        price_min=metadata.get("price_min", 0),
        price_max=metadata.get("price_max", 0),
        stock="yes" if metadata.get("in_stock") else "no",
        match=score_pct_text,
        likes=metadata.get("likes", 0),
        style_code=metadata.get("style_code") or "n/a",
    )


def _database_entry_as_text(entry: Dict[str, Any]) -> str:
    return (
        f"- [{entry.get('id')}] {entry.get('name', 'Unknown')}, category: {entry.get('category', 'Unknown')}, "
        f"price: {entry.get('price_min', 0)} to {entry.get('price_max', 0)}, "
        f"stock: {'yes' if entry.get('in_stock') else 'no'}, "
        f"likes: {entry.get('likes', 0)}, style_code: {entry.get('style_code') or 'n/a'}"
    )


def _append_state(state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    metadata = dict(state.get("metadata", {}))
    metadata.update(updates.pop("metadata", {}))
    state.update(updates)
    state["metadata"] = metadata
    return state


def _extract_evidence_ids(payload: Any) -> Optional[List[str]]:
    if isinstance(payload, list):
        return [str(item["id"]) for item in payload if isinstance(item, dict) and "id" in item]
    if isinstance(payload, dict):
        results = payload.get("results") or []
        return [str(item.get("id")) for item in results if isinstance(item, dict) and "id" in item]
    return None


def _detect_unsupported_query_type(user_query: str) -> bool:
    lowered = user_query.lower()
    keywords = [
        "order status",
        "track shipment",
        "return policy",
        "shipping cost",
        "login",
        "account",
        "password",
        "support ticket",
        "warehouse",
        "employee",
        "revenue",
        "profit",
        "database schema",
    ]
    return any(keyword in lowered for keyword in keywords)


def create_orchestrator(config: Optional[AppConfig] = None) -> Orchestrator:
    return Orchestrator(config=config)

_orchestrator_singleton: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    global _orchestrator_singleton
    if _orchestrator_singleton is None:
        _orchestrator_singleton = create_orchestrator()
    return _orchestrator_singleton


async def run_session(user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    orchestrator = get_orchestrator()
    result = await orchestrator.run(user_query=user_query, session_id=session_id)
    return {
        "response": result.response,
        "session_id": session_id,
        "metadata": result.metadata,
    }


async def warmup_orchestrator() -> None:
    query = "Warmup blazer"
    await get_orchestrator().run(query)


async def main(argv: Optional[Sequence[str]] = None) -> int:
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description="Run the MOA orchestrator locally.")
    parser.add_argument("--test-query", dest="test_query", default=None, help="Query to run once and print the result.")
    parser.add_argument("--query", default="Summer blazer", help="Default query for an interactive run.")
    parser.add_argument("--session-id", default=None, help="Optional external session id.")
    args = parser.parse_args(argv)
    user_query = args.test_query or args.query
    if not user_query:
        parser.error("Provide --test-query or --query.")

    payload = await run_session(user_query=user_query, session_id=args.session_id)
    print(payload["response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
