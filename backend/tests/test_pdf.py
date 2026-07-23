import uuid

from app.services.pdf import chunk_pages, clean_text


def test_cleaning_repairs_whitespace():
    assert clean_text("a-\n b   c") == "ab c"


def test_chunks_are_deterministic_and_overlap():
    text = " ".join([f"word{i}." for i in range(120)])
    a = chunk_pages(
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        [(1, text)],
        20,
        25,
        5,
        5,
        lambda value: len(value.split()),
        lambda value, maximum: [value],
    )
    b = chunk_pages(
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        [(1, text)],
        20,
        25,
        5,
        5,
        lambda value: len(value.split()),
        lambda value, maximum: [value],
    )
    assert [x.id for x in a] == [x.id for x in b] and len(a) > 1


def test_oversized_sentence_uses_tokenizer_splitter() -> None:
    pieces = chunk_pages(
        uuid.uuid4(),
        [(1, "one two three four five six")],
        3,
        3,
        0,
        1,
        lambda value: len(value.split()),
        lambda value, maximum: ["one two three", "four five six"],
    )
    assert [piece.token_count for piece in pieces] == [3, 3]
