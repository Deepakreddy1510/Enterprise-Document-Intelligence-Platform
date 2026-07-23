import pytest

from app.api.v1 import routes


@pytest.mark.asyncio
async def test_query_embedding_uses_asyncio_thread_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, list[str]]] = []

    async def fake_to_thread(function: object, texts: list[str]) -> list[list[float]]:
        calls.append((function, texts))
        return [[0.1, 0.2]]

    monkeypatch.setattr(routes.asyncio, "to_thread", fake_to_thread)
    result = await routes.embed_query_in_thread("How is the document structured?")

    assert result == [0.1, 0.2]
    assert calls == [(routes.embed, ["How is the document structured?"])]
