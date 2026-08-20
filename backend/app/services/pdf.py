import re
import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import fitz


@dataclass
class Chunk:
    id: uuid.UUID
    content: str
    page_number: int
    chunk_index: int
    token_count: int


def extract_pages(path: str) -> list[tuple[int, str]]:
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise ValueError("The file is not a readable PDF") from exc
    if doc.needs_pass:
        raise ValueError("Password-protected PDFs are not supported")
    pages = []
    for number, page in enumerate(doc, 1):
        page_text = clean_text(page.get_text("text"))
        if page_text:
            pages.append((number, page_text))
    if not pages:
        raise ValueError("The PDF has no extractable text")
    return pages


def clean_text(text: str) -> str:
    """Normalize extracted PDF text before chunking or database storage."""
    text = text.replace("\x00", " ")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def _tail_for_overlap(
    units: list[str],
    overlap: int,
    count: Callable[[str], int],
) -> list[str]:
    if overlap <= 0:
        return []

    selected: list[str] = []
    total = 0

    for unit in reversed(units):
        unit_tokens = count(unit)

        if selected and total + unit_tokens > overlap:
            break

        selected.append(unit)
        total += unit_tokens

        if total >= overlap:
            break

    return list(reversed(selected))


def chunk_pages(
    document_id: uuid.UUID,
    pages: list[tuple[int, str]],
    target: int,
    maximum: int,
    overlap: int,
    minimum: int,
    token_counter: Callable[[str], int],
    split_oversized_sentence: Callable[[str, int], list[str]],
) -> list[Chunk]:
    """Create sentence-boundary chunks using the embedding model's tokenizer."""
    chunks: list[Chunk] = []
    index = 0
    for page, page_text in pages:
        sentences = [item for item in re.split(r"(?<=[.!?])\s+", page_text) if item]
        units: list[str] = []
        for sentence in sentences:
            if token_counter(sentence) > maximum:
                units.extend(split_oversized_sentence(sentence, maximum))
            else:
                units.append(sentence)
        current: list[str] = []
        current_tokens = 0

        def emit(units_to_emit: list[str], tokens_to_emit: int, page_number: int) -> None:
            nonlocal index
            content = " ".join(units_to_emit).strip()
            if content and tokens_to_emit >= minimum:
                chunks.append(
                    Chunk(
                        uuid.uuid5(document_id, f"{page_number}:{index}:{content}"),
                        content,
                        page_number,
                        index,
                        tokens_to_emit,
                    )
                )
                index += 1

        for unit in units:
            unit_tokens = token_counter(unit)
            if current and current_tokens + unit_tokens > maximum:
                emit(current, current_tokens, page)
                current = _tail_for_overlap(current, overlap, token_counter)
                current_tokens = sum(token_counter(item) for item in current)
            current.append(unit)
            current_tokens += unit_tokens
            if current_tokens >= target:
                emit(current, current_tokens, page)
                current = _tail_for_overlap(current, overlap, token_counter)
                current_tokens = sum(token_counter(item) for item in current)
        emit(current, current_tokens, page)
    return chunks
