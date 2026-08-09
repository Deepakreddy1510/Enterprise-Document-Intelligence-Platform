import math
import statistics
from dataclasses import dataclass
from typing import Any

from app.evaluation.dataset import EvaluationCase
from app.services.retrieval import RetrievedChunk


@dataclass(frozen=True, slots=True)
class RetrievalScores:
    hit_at_1: float
    hit_at_3: float
    hit_at_5: float
    reciprocal_rank: float
    recall_at_5: float


def is_relevant(result: RetrievedChunk, case: EvaluationCase) -> bool:
    return result.page_number in case.relevant_pages.get(result.document_name, [])


def score_retrieval(case: EvaluationCase, results: list[RetrievedChunk]) -> RetrievalScores:
    relevant = [(name, page) for name, pages in case.relevant_pages.items() for page in pages]
    ranks = [result.rank for result in results if is_relevant(result, case)]
    retrieved_relevant = {
        (result.document_name, result.page_number)
        for result in results[:5]
        if is_relevant(result, case)
    }
    return RetrievalScores(
        float(any(rank <= 1 for rank in ranks)),
        float(any(rank <= 3 for rank in ranks)),
        float(any(rank <= 5 for rank in ranks)),
        1.0 / min(ranks) if ranks else 0.0,
        len(retrieved_relevant) / len(set(relevant)) if relevant else 0.0,
    )


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def aggregate_retrieval(case_results: list[dict[str, Any]]) -> dict[str, float]:
    retrieval_completed = [item for item in case_results if "retrieval_latency_ms" in item]
    answerable = [
        item for item in retrieval_completed if item["answerable"] and item.get("retrieval")
    ]
    latencies = [float(item["retrieval_latency_ms"]) for item in retrieval_completed]

    def mean(name: str) -> float:
        values = [float(item["retrieval"][name]) for item in answerable]
        return statistics.fmean(values) if values else 0.0

    return {
        "evaluated_answerable_cases": float(len(answerable)),
        "failed_cases": float(len(case_results) - len(retrieval_completed)),
        "hit_at_1": mean("hit_at_1"),
        "hit_at_3": mean("hit_at_3"),
        "hit_at_5": mean("hit_at_5"),
        "mrr": mean("reciprocal_rank"),
        "recall_at_5": mean("recall_at_5"),
        "average_retrieval_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "median_retrieval_latency_ms": statistics.median(latencies) if latencies else 0.0,
        "p95_retrieval_latency_ms": percentile(latencies, 0.95),
    }


def is_refusal(answer: str) -> bool:
    normalized = answer.casefold()
    phrases = (
        "insufficient context",
        "not enough information",
        "cannot answer",
        "can't answer",
        "not available in the selected",
        "do not contain enough",
    )
    return any(phrase in normalized for phrase in phrases)


def classify_refusal(case: EvaluationCase, answer: str) -> str:
    refusal = is_refusal(answer)
    if case.answerable and refusal:
        return "incorrect_refusal"
    if not case.answerable and refusal:
        return "correct_refusal"
    if not case.answerable:
        return "hallucinated_answer"
    return "answered"


def aggregate_refusals(case_results: list[dict[str, Any]]) -> dict[str, float]:
    labels = [item.get("refusal_classification") for item in case_results if not item.get("error")]
    unanswerable = sum(not item["answerable"] for item in case_results if not item.get("error"))
    correct = labels.count("correct_refusal")
    return {
        "correct_refusal": float(correct),
        "incorrect_refusal": float(labels.count("incorrect_refusal")),
        "hallucinated_answer": float(labels.count("hallucinated_answer")),
        "refusal_accuracy": correct / unanswerable if unanswerable else 0.0,
    }
