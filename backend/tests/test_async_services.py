from pathlib import Path


def test_ingestion_offloads_synchronous_model_and_pdf_work() -> None:
    source = (Path(__file__).parents[1] / "app/services/ingestion.py").read_text()
    assert "await asyncio.to_thread(extract_pages" in source
    assert "await asyncio.to_thread(embed" in source


def test_gemini_generation_is_offloaded_from_route_loop() -> None:
    source = (Path(__file__).parents[1] / "app/api/v1/routes.py").read_text()
    assert "answer = await asyncio.to_thread(generate)" in source
