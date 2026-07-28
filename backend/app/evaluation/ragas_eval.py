import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from google import genai

from app.core.config import get_settings
from app.evaluation.dataset import EvaluationCase
from app.services.retrieval import RetrievedChunk

RAGAS_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "factual_correctness",
)


def map_ragas_inputs(
    case: EvaluationCase, answer: str, retrieved: list[RetrievedChunk]
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "user_input": case.question,
        "response": answer,
        "retrieved_contexts": [item.content for item in retrieved],
    }
    if case.reference_answer:
        payload["reference"] = case.reference_answer
    return payload


def _score_value(result: Any) -> float:
    value = getattr(result, "value", result)
    return float(value)


class RagasEvaluator:
    def __init__(self, max_concurrency: int | None = None) -> None:
        settings = get_settings()
        if not settings.ragas_enabled:
            raise RuntimeError("RAGAS evaluation is disabled; set RAGAS_ENABLED=true")
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for RAGAS evaluation")
        self.settings = settings
        self.semaphore = asyncio.Semaphore(max_concurrency or settings.ragas_max_concurrency)
        self.cache_directory = settings.ragas_cache_directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        try:
            from ragas.llms import llm_factory
            from ragas.metrics.collections import (
                AnswerRelevancy,
                ContextPrecision,
                ContextRecall,
                FactualCorrectness,
                Faithfulness,
            )
        except ImportError as exc:
            raise RuntimeError("ragas==0.4.3 is required for RAGAS evaluation") from exc
        client = genai.Client(api_key=settings.gemini_api_key)
        llm = llm_factory(settings.ragas_evaluator_model, provider="google", client=client)
        self.metrics = {
            "faithfulness": Faithfulness(llm=llm),
            "answer_relevancy": AnswerRelevancy(llm=llm),
            "context_precision": ContextPrecision(llm=llm),
            "context_recall": ContextRecall(llm=llm),
            "factual_correctness": FactualCorrectness(llm=llm),
        }

    def _cache_path(self, metric: str, inputs: dict[str, Any]) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {"metric": metric, "model": self.settings.ragas_evaluator_model, **inputs},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return self.cache_directory / f"{key}.json"

    async def _score_metric(self, name: str, inputs: dict[str, Any]) -> float:
        cache_path = self._cache_path(name, inputs)
        if cache_path.exists():
            return float(json.loads(cache_path.read_text())["score"])
        metric = self.metrics[name]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(
                        metric.ascore(**inputs),
                        timeout=self.settings.ragas_evaluator_timeout_seconds,
                    )
                score = _score_value(result)
                cache_path.write_text(json.dumps({"score": score}))
                return score
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1)
        raise RuntimeError(
            f"RAGAS metric {name} failed: {type(last_error).__name__}"
        ) from last_error

    async def evaluate(
        self, case: EvaluationCase, answer: str, retrieved: list[RetrievedChunk]
    ) -> dict[str, float]:
        if not case.answerable or not case.reference_answer:
            return {}
        inputs = map_ragas_inputs(case, answer, retrieved)
        scores = await asyncio.gather(
            *(self._score_metric(name, inputs) for name in RAGAS_METRICS),
            return_exceptions=True,
        )
        output: dict[str, float] = {}
        errors: list[str] = []
        for name, score in zip(RAGAS_METRICS, scores, strict=True):
            if isinstance(score, BaseException):
                errors.append(f"{name}: {score}")
            else:
                output[name] = score
        if errors:
            raise RuntimeError("; ".join(errors))
        return output


def aggregate_ragas(case_results: list[dict[str, Any]]) -> dict[str, float]:
    successful = [
        item["ragas"] for item in case_results if not item.get("error") and item.get("ragas")
    ]
    return {
        metric: sum(float(item[metric]) for item in successful if metric in item)
        / sum(metric in item for item in successful)
        if any(metric in item for item in successful)
        else 0.0
        for metric in RAGAS_METRICS
    }
