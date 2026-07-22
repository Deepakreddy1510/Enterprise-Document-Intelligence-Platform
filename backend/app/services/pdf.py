import re
import unicodedata
import uuid
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
        text = clean_text(page.get_text("text"))
        if text:
            pages.append((number, text))
    if not pages:
        raise ValueError("The PDF has no extractable text")
    return pages


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def chunk_pages(
    document_id: uuid.UUID,
    pages: list[tuple[int, str]],
    target: int,
    maximum: int,
    overlap: int,
    minimum: int,
) -> list[Chunk]:
    result = []
    index = 0
    for page, text in pages:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current: list[str] = []
        for sentence in sentences:
            words = sentence.split()
            if len(current) + len(words) > maximum and current:
                content = " ".join(current)
                if len(current) >= minimum:
                    result.append(
                        Chunk(
                            uuid.uuid5(document_id, f"{page}:{index}:{content}"),
                            content,
                            page,
                            index,
                            len(current),
                        )
                    )
                    index += 1
                current = current[-overlap:] + words
            else:
                current += words
            if len(current) >= target:
                content = " ".join(current)
                result.append(
                    Chunk(
                        uuid.uuid5(document_id, f"{page}:{index}:{content}"),
                        content,
                        page,
                        index,
                        len(current),
                    )
                )
                index += 1
                current = current[-overlap:]
        if len(current) >= minimum:
            content = " ".join(current)
            result.append(
                Chunk(
                    uuid.uuid5(document_id, f"{page}:{index}:{content}"),
                    content,
                    page,
                    index,
                    len(current),
                )
            )
            index += 1
    return result
