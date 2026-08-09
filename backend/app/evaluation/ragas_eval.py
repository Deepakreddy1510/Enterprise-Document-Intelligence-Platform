import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from google import genai
from openai import AsyncOpenAI

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

GEMINI_OPENAI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)


class RateLimitedAsyncHTTPClient(httpx.AsyncClient):
    def __init__(
        self,
        min_interval_seconds: float = 16.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.min_interval_seconds = min_interval_seconds
        self._rate_lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def send(
        self,
        request: httpx.Request,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        async with self._rate_lock:
            loop = asyncio.get_running_loop()

            elapsed = loop.time() - self._last_request_at

            remaining = (
                self.min_interval_seconds - elapsed
            )

            if remaining > 0:
                await asyncio.sleep(remaining)

            self._last_request_at = loop.time()

        return await super().send(
            request,
            *args,
            **kwargs,
        )


def map_ragas_inputs(
    case: EvaluationCase,
    answer: str,
    retrieved: list[RetrievedChunk],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "user_input": case.question,
        "response": answer,
        "retrieved_contexts": [
            item.content
            for item in retrieved
        ],
    }

    if case.reference_answer:
        payload["reference"] = case.reference_answer

    return payload


def _score_value(result: Any) -> float:
    value = getattr(result, "value", result)
    return float(value)


class RagasEvaluator:
    def __init__(
        self,
        max_concurrency: int | None = None,
    ) -> None:
        settings = get_settings()

        if not settings.ragas_enabled:
            raise RuntimeError(
                "RAGAS evaluation is disabled; "
                "set RAGAS_ENABLED=true"
            )

        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is required "
                "for RAGAS evaluation"
            )

        self.settings = settings

        self.semaphore = asyncio.Semaphore(
            max_concurrency
            or settings.ragas_max_concurrency
        )

        self.cache_directory = (
            settings.ragas_cache_directory
        )

        self.cache_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            from ragas.embeddings import GoogleEmbeddings
            from ragas.llms import llm_factory
            from ragas.metrics.collections import (
                AnswerRelevancy,
                ContextPrecision,
                ContextRecall,
                FactualCorrectness,
                Faithfulness,
            )
        except ImportError as exc:
            raise RuntimeError(
                "ragas==0.4.3 is required "
                "for RAGAS evaluation"
            ) from exc

        # Used for Gemini embeddings.
        self.genai_client = genai.Client(
            api_key=settings.gemini_api_key,
        )

        # Rate-limit RAGAS judge requests because
        # the Gemini free tier has a low RPM quota.
        self.ragas_http_client = (
            RateLimitedAsyncHTTPClient(
                min_interval_seconds=16.0,
            )
        )

        # Gemini is accessed through Google's
        # OpenAI-compatible endpoint so RAGAS can
        # use a true asynchronous client.
        self.openai_client = AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url=GEMINI_OPENAI_BASE_URL,
            http_client=self.ragas_http_client,
        )

        llm = llm_factory(
            settings.ragas_evaluator_model,
            provider="openai",
            client=self.openai_client,
            adapter="instructor",
        )

        # AnswerRelevancy requires embeddings.
        embeddings = GoogleEmbeddings(
            client=self.genai_client,
            model="gemini-embedding-001",
        )

        self.metrics = {
            "faithfulness": Faithfulness(
                llm=llm,
            ),
            "answer_relevancy": AnswerRelevancy(
                llm=llm,
                embeddings=embeddings,
            ),
            "context_precision": ContextPrecision(
                llm=llm,
            ),
            "context_recall": ContextRecall(
                llm=llm,
            ),
            "factual_correctness": FactualCorrectness(
                llm=llm,
            ),
        }

    def _cache_path(
        self,
        metric: str,
        inputs: dict[str, Any],
    ) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {
                    "metric": metric,
                    "model": (
                        self.settings
                        .ragas_evaluator_model
                    ),
                    "provider": (
                        "gemini-openai-compatible"
                    ),
                    **inputs,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

        return (
            self.cache_directory
            / f"{key}.json"
        )

    def _metric_inputs(
        self,
        name: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        if name == "faithfulness":
            return {
                "user_input": inputs["user_input"],
                "response": inputs["response"],
                "retrieved_contexts": (
                    inputs["retrieved_contexts"]
                ),
            }

        if name == "answer_relevancy":
            return {
                "user_input": inputs["user_input"],
                "response": inputs["response"],
            }

        if name == "context_precision":
            return {
                "user_input": inputs["user_input"],
                "reference": inputs["reference"],
                "retrieved_contexts": (
                    inputs["retrieved_contexts"]
                ),
            }

        if name == "context_recall":
            return {
                "user_input": inputs["user_input"],
                "retrieved_contexts": (
                    inputs["retrieved_contexts"]
                ),
                "reference": inputs["reference"],
            }

        if name == "factual_correctness":
            return {
                "response": inputs["response"],
                "reference": inputs["reference"],
            }

        raise ValueError(
            f"Unsupported RAGAS metric: {name}"
        )

    async def _score_metric(
        self,
        name: str,
        inputs: dict[str, Any],
    ) -> float:
        metric_inputs = self._metric_inputs(
            name,
            inputs,
        )

        cache_path = self._cache_path(
            name,
            metric_inputs,
        )

        if cache_path.exists():
            cached = json.loads(
                cache_path.read_text(
                    encoding="utf-8",
                )
            )

            return float(
                cached["score"]
            )

        metric = self.metrics[name]
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(
                        metric.ascore(
                            **metric_inputs
                        ),
                        timeout=(
                            self.settings
                            .ragas_evaluator_timeout_seconds
                        ),
                    )

                score = _score_value(result)

                cache_path.write_text(
                    json.dumps(
                        {
                            "score": score,
                        }
                    ),
                    encoding="utf-8",
                )

                return score

            except Exception as exc:
                last_error = exc

                if attempt == 0:
                    await asyncio.sleep(5)

        raise RuntimeError(
            f"RAGAS metric {name} failed: "
            f"{type(last_error).__name__}: "
            f"{last_error}"
        ) from last_error

    async def evaluate(
        self,
        case: EvaluationCase,
        answer: str,
        retrieved: list[RetrievedChunk],
    ) -> dict[str, float]:
        if not case.answerable:
            return {}

        if not case.reference_answer:
            return {}

        inputs = map_ragas_inputs(
            case,
            answer,
            retrieved,
        )

        scores = await asyncio.gather(
            *(
                self._score_metric(
                    name,
                    inputs,
                )
                for name in RAGAS_METRICS
            ),
            return_exceptions=True,
        )

        output: dict[str, float] = {}
        errors: list[str] = []

        for name, score in zip(
            RAGAS_METRICS,
            scores,
            strict=True,
        ):
            if isinstance(
                score,
                BaseException,
            ):
                errors.append(
                    f"{name}: {score}"
                )
            else:
                output[name] = score

        if errors:
            raise RuntimeError(
                "; ".join(errors)
            )

        return output


def aggregate_ragas(
    case_results: list[dict[str, Any]],
) -> dict[str, float]:
    successful = [
        item["ragas"]
        for item in case_results
        if not item.get("error")
        and item.get("ragas")
    ]

    return {
        metric: (
            sum(
                float(item[metric])
                for item in successful
                if metric in item
            )
            / sum(
                metric in item
                for item in successful
            )
            if any(
                metric in item
                for item in successful
            )
            else 0.0
        )
        for metric in RAGAS_METRICS
    }