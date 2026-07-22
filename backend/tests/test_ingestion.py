import uuid

from app.services.pdf import chunk_pages


def test_short_blocks_are_filtered() -> None:
    assert (
        chunk_pages(
            uuid.uuid4(),
            [(1, "tiny")],
            20,
            25,
            5,
            10,
            lambda value: len(value.split()),
            lambda value, maximum: [value],
        )
        == []
    )


def test_chunks_keep_page_and_sentence_text() -> None:
    chunks = chunk_pages(
        uuid.uuid4(),
        [(3, "First sentence. Second sentence. Third sentence.")],
        3,
        5,
        1,
        1,
        lambda value: len(value.split()),
        lambda value, maximum: [value],
    )
    assert chunks and all(chunk.page_number == 3 for chunk in chunks)
    assert all(chunk.content.endswith((".", "sentence.")) for chunk in chunks)
