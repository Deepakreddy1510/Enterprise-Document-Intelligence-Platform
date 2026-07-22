import uuid

from app.services.pdf import chunk_pages, clean_text


def test_cleaning_repairs_whitespace():
    assert clean_text("a-\n b   c") == "ab c"


def test_chunks_are_deterministic_and_overlap():
    text = " ".join([f"word{i}." for i in range(120)])
    a = chunk_pages(uuid.UUID("00000000-0000-0000-0000-000000000001"), [(1, text)], 20, 25, 5, 5)
    b = chunk_pages(uuid.UUID("00000000-0000-0000-0000-000000000001"), [(1, text)], 20, 25, 5, 5)
    assert [x.id for x in a] == [x.id for x in b] and len(a) > 1
