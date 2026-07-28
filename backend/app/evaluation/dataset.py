import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question: str
    selected_documents: list[str] = Field(min_length=1)
    relevant_pages: dict[str, list[int]] = Field(default_factory=dict)
    reference_answer: str | None = None
    answerable: bool
    expected_behavior: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question cannot be blank")
        return value.strip()

    @field_validator("selected_documents")
    @classmethod
    def documents_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("selected document names cannot be blank")
        return value

    @field_validator("relevant_pages")
    @classmethod
    def pages_are_positive(cls, value: dict[str, list[int]]) -> dict[str, list[int]]:
        if any(page <= 0 for pages in value.values() for page in pages):
            raise ValueError("page numbers must be positive integers")
        return value

    @model_validator(mode="after")
    def answerable_requirements(self) -> "EvaluationCase":
        if self.answerable:
            if not self.reference_answer or not self.reference_answer.strip():
                raise ValueError("answerable cases require reference_answer")
            if not any(self.relevant_pages.values()):
                raise ValueError("answerable cases require relevant_pages")
        return self


def load_dataset(path: Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    ids: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                case = EvaluationCase.model_validate(json.loads(line))
            except Exception as exc:
                raise ValueError(f"Invalid dataset line {line_number}: {exc}") from exc
            if case.id in ids:
                raise ValueError(f"Duplicate evaluation case ID: {case.id}")
            ids.add(case.id)
            cases.append(case)
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases
