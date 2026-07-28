import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.dataset import EvaluationCase, load_dataset
from app.evaluation.metrics import (
    aggregate_refusals,
    aggregate_retrieval,
    classify_refusal,
    percentile,
    score_retrieval,
)
from app.evaluation.ragas_eval import aggregate_ragas, map_ragas_inputs
from app.services.retrieval import RetrievedChunk


def case(answerable: bool = True) -> EvaluationCase:
    return EvaluationCase(
        id="case-1",
        question="Where is the policy?",
        selected_documents=["policy.pdf"],
        relevant_pages={"policy.pdf": [2, 4]} if answerable else {},
        reference_answer="It is on the labelled pages." if answerable else None,
        answerable=answerable,
        expected_behavior="Answer with evidence" if answerable else "Refuse",
    )


def result(rank: int, name: str = "policy.pdf", page: int = 2) -> RetrievedChunk:
    return RetrievedChunk(
        rank, uuid.uuid4(), uuid.uuid4(), name, page, rank - 1, f"context-{rank}", 0.9
    )


def test_hit_mrr_and_recall_require_document_and_page() -> None:
    scores = score_retrieval(case(), [result(1, page=9), result(2, page=2)])
    assert scores.hit_at_1 == 0
    assert scores.hit_at_3 == scores.hit_at_5 == 1
    assert scores.reciprocal_rank == 0.5
    assert scores.recall_at_5 == 0.5
    wrong_document = score_retrieval(case(), [result(1, "other.pdf", 2)])
    assert wrong_document.hit_at_5 == 0


def test_latency_percentiles_are_interpolated() -> None:
    assert percentile([10, 20, 30, 40, 50], 0.95) == pytest.approx(48)
    assert percentile([], 0.95) == 0


def test_dataset_validation_and_duplicate_ids(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        EvaluationCase(
            id="bad",
            question=" ",
            selected_documents=[],
            relevant_pages={"a.pdf": [0]},
            reference_answer="",
            answerable=True,
            expected_behavior="answer",
        )
    row = case().model_dump()
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        load_dataset(dataset)


def test_answerable_partition_and_failed_cases_are_excluded() -> None:
    rows = [
        {
            "answerable": True,
            "retrieval_latency_ms": 10,
            "retrieval": {
                "hit_at_1": 1,
                "hit_at_3": 1,
                "hit_at_5": 1,
                "reciprocal_rank": 1,
                "recall_at_5": 0.5,
            },
        },
        {"answerable": True, "error": "provider failed"},
        {"answerable": False, "retrieval_latency_ms": 30},
    ]
    aggregate = aggregate_retrieval(rows)
    assert aggregate["evaluated_answerable_cases"] == 1
    assert aggregate["failed_cases"] == 1
    assert aggregate["hit_at_1"] == 1
    assert aggregate["average_retrieval_latency_ms"] == 20
    ragas = aggregate_ragas([{"ragas": {"faithfulness": 0.8}}, {"error": "bad"}])
    assert ragas["faithfulness"] == 0.8


def test_ragas_mapping_uses_ranked_exact_contexts_and_reference() -> None:
    inputs = map_ragas_inputs(case(), "answer", [result(1), result(2, page=4)])
    assert inputs == {
        "user_input": "Where is the policy?",
        "response": "answer",
        "retrieved_contexts": ["context-1", "context-2"],
        "reference": "It is on the labelled pages.",
    }
    assert "reference" not in map_ragas_inputs(case(False), "refusal", [result(1)])


def test_refusal_classification_and_accuracy() -> None:
    assert classify_refusal(case(False), "There is not enough information.") == "correct_refusal"
    assert classify_refusal(case(False), "The allowance is $500.") == "hallucinated_answer"
    assert classify_refusal(case(), "I cannot answer from these pages.") == "incorrect_refusal"
    aggregate = aggregate_refusals(
        [
            {"answerable": False, "refusal_classification": "correct_refusal"},
            {"answerable": False, "refusal_classification": "hallucinated_answer"},
            {"answerable": True, "refusal_classification": "incorrect_refusal"},
        ]
    )
    assert aggregate["refusal_accuracy"] == 0.5


@pytest.mark.asyncio
async def test_ragas_external_metric_calls_are_mocked_and_answerable_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.evaluation.ragas_eval import RAGAS_METRICS, RagasEvaluator

    evaluator = object.__new__(RagasEvaluator)

    async def fake_score(name: str, inputs: dict[str, object]) -> float:
        assert inputs["user_input"] == "Where is the policy?"
        return 0.75

    monkeypatch.setattr(evaluator, "_score_metric", fake_score)
    scores = await evaluator.evaluate(case(), "answer", [result(1)])
    assert scores == {name: 0.75 for name in RAGAS_METRICS}
    assert await evaluator.evaluate(case(False), "refusal", [result(1)]) == {}
