import asyncio
import csv
import json
import statistics
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.evaluation.dataset import EvaluationCase
from app.evaluation.metrics import (
    aggregate_refusals,
    aggregate_retrieval,
    classify_refusal,
    score_retrieval,
)
from app.evaluation.ragas_eval import RagasEvaluator, aggregate_ragas
from app.models import Document, User
from app.services.rag import RAGExecutionService
from app.services.retrieval import RetrievalService, RetrievedChunk


@dataclass(frozen=True, slots=True)
class RunOptions:
    mode: str
    top_k: int
    max_concurrency: int
    fail_on_error: bool


def safe_error(exc: Exception) -> str:
    message = str(exc)
    secret = get_settings().gemini_api_key
    if secret:
        message = message.replace(secret, "[REDACTED]")
    return f"{type(exc).__name__}: {message}"[:1000]


def serialize_result(item: RetrievedChunk) -> dict[str, Any]:
    return {
        "rank": item.rank,
        "chunk_id": str(item.chunk_id),
        "document_id": str(item.document_id),
        "document_name": item.document_name,
        "page_number": item.page_number,
        "chunk_index": item.chunk_index,
        "content": item.content,
        "similarity": item.similarity,
    }


async def resolve_user_and_documents(
    email: str, cases: list[EvaluationCase]
) -> tuple[uuid.UUID, dict[str, uuid.UUID]]:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            raise ValueError(f"No user found for email: {email}")
        documents = (
            await session.scalars(
                select(Document).where(Document.user_id == user.id, Document.status == "ready")
            )
        ).all()
    by_name: dict[str, uuid.UUID] = {}
    duplicates: set[str] = set()
    for document in documents:
        if document.original_filename in by_name:
            duplicates.add(document.original_filename)
        by_name[document.original_filename] = document.id
    requested = {name for case in cases for name in case.selected_documents}
    duplicate_requested = requested & duplicates
    if duplicate_requested:
        raise ValueError(f"Duplicate ready filenames: {', '.join(sorted(duplicate_requested))}")
    missing = requested - by_name.keys()
    if missing:
        raise ValueError(f"Ready documents not found: {', '.join(sorted(missing))}")
    return user.id, by_name


async def evaluate_case(
    case: EvaluationCase,
    user_id: uuid.UUID,
    document_map: dict[str, uuid.UUID],
    options: RunOptions,
    ragas: RagasEvaluator | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": case.id,
        "question": case.question,
        "answerable": case.answerable,
        "expected_behavior": case.expected_behavior,
        "selected_documents": case.selected_documents,
        "reference_answer": case.reference_answer,
        "tags": case.tags,
    }
    document_ids = [document_map[name] for name in case.selected_documents]
    try:
        async with SessionLocal() as session:
            started = time.perf_counter()
            retrieved = await RetrievalService().retrieve(
                session, user_id, document_ids, case.question, options.top_k
            )
            result["retrieval_latency_ms"] = (time.perf_counter() - started) * 1000
            result["retrieved"] = [serialize_result(item) for item in retrieved]
            if case.answerable:
                result["retrieval"] = asdict(score_retrieval(case, retrieved))
            if options.mode in {"ragas", "all"}:
                execution = await RAGExecutionService().execute(
                    session,
                    user_id,
                    document_ids,
                    case.question,
                    options.top_k,
                    retrieved=retrieved,
                )
                result["generated_answer"] = execution.generated_answer
                result["generation_latency_ms"] = execution.generation_latency_ms
                result["refusal_classification"] = classify_refusal(
                    case, execution.generated_answer
                )
                if ragas is not None and case.answerable:
                    try:
                        result["ragas"] = await ragas.evaluate(
                            case, execution.generated_answer, list(execution.sources)
                        )
                    except Exception as exc:
                        result["ragas_error"] = safe_error(exc)
    except Exception as exc:
        result["error"] = safe_error(exc)
    return result


async def run_evaluation(
    cases: list[EvaluationCase],
    user_email: str,
    options: RunOptions,
) -> dict[str, Any]:
    user_id, document_map = await resolve_user_and_documents(user_email, cases)
    ragas = RagasEvaluator(options.max_concurrency) if options.mode in {"ragas", "all"} else None
    semaphore = asyncio.Semaphore(options.max_concurrency)

    async def bounded(case: EvaluationCase) -> dict[str, Any]:
        async with semaphore:
            return await evaluate_case(case, user_id, document_map, options, ragas)

    case_results = await asyncio.gather(*(bounded(case) for case in cases))
    settings = get_settings()
    generation_latencies = [
        float(item["generation_latency_ms"])
        for item in case_results
        if not item.get("error") and "generation_latency_ms" in item
    ]
    return {
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "user_email": user_email,
            "mode": options.mode,
            "top_k": options.top_k,
            "embedding_model": settings.embedding_model,
            "generator_model": settings.gemini_model if options.mode != "retrieval" else None,
            "evaluator_model": settings.ragas_evaluator_model if ragas else None,
            "case_count": len(cases),
        },
        "retrieval_aggregate": aggregate_retrieval(case_results),
        "ragas_aggregate": aggregate_ragas(case_results) if ragas else {},
        "refusal_metrics": aggregate_refusals(case_results)
        if options.mode in {"ragas", "all"}
        else {},
        "latency_metrics": {
            "average_generation_latency_ms": statistics.fmean(generation_latencies)
            if generation_latencies
            else 0.0,
        },
        "api_failure_counts": {
            "generation_or_retrieval_failures": sum(
                bool(item.get("error")) for item in case_results
            ),
            "ragas_failures": sum(bool(item.get("ragas_error")) for item in case_results),
        },
        "cases": case_results,
    }


def save_results(results: dict[str, Any], output: Path) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    csv_path = output.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "answerable",
                "error",
                "hit_at_1",
                "hit_at_3",
                "hit_at_5",
                "reciprocal_rank",
                "recall_at_5",
                "retrieval_latency_ms",
                "generation_latency_ms",
                "refusal_classification",
                "generated_answer",
                "reference_answer",
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
                "factual_correctness",
            ],
        )
        writer.writeheader()
        for item in results["cases"]:
            retrieval = item.get("retrieval", {})
            ragas_scores = item.get("ragas", {})
            writer.writerow(
                {
                    "id": item["id"],
                    "answerable": item["answerable"],
                    "error": item.get("error", ""),
                    "retrieval_latency_ms": item.get("retrieval_latency_ms", ""),
                    "generation_latency_ms": item.get("generation_latency_ms", ""),
                    "refusal_classification": item.get("refusal_classification", ""),
                    "generated_answer": item.get("generated_answer", ""),
                    "reference_answer": item.get("reference_answer", ""),
                    **retrieval,
                    **ragas_scores,
                }
            )
    return output, csv_path
