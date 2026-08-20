from pathlib import Path


def test_ingestion_offloads_synchronous_model_and_pdf_work() -> None:
    source = (
        Path(__file__).parents[1]
        / "app/services/ingestion.py"
    ).read_text()

    assert "pages = await asyncio.to_thread(" in source
    assert "extract_pages," in source

    assert "chunks = await asyncio.to_thread(" in source
    assert "chunk_pages," in source

    assert "batch_vectors = await asyncio.to_thread(" in source
    assert "embed," in source


def test_gemini_generation_is_offloaded_from_service_loop() -> None:
    source = (
        Path(__file__).parents[1]
        / "app/services/rag.py"
    ).read_text()

    assert "answer = await asyncio.to_thread(generate)" in source