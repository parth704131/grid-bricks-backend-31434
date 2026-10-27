from types import SimpleNamespace

import httpx
import pytest

from app.clients.elexon import ElexonClient, ElexonClientError


def _response(status_code: int, payload: list[dict] | None = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        request=httpx.Request("GET", "https://example.test/dataset"),
        json=payload,
    )


def test_client_retries_transient_server_failure(monkeypatch) -> None:
    responses = [_response(500), _response(200, [{"generation": 100}])]
    client = ElexonClient()
    client.client = SimpleNamespace(get=lambda *_args, **_kwargs: responses.pop(0))
    monkeypatch.setattr("app.clients.elexon.sleep", lambda _: None)

    assert client._get("/dataset", {}) == [{"generation": 100}]
    assert responses == []


def test_client_does_not_retry_normal_client_error(monkeypatch) -> None:
    responses = [_response(400)]
    client = ElexonClient()
    client.client = SimpleNamespace(get=lambda *_args, **_kwargs: responses.pop(0))
    monkeypatch.setattr("app.clients.elexon.sleep", lambda _: None)

    with pytest.raises(ElexonClientError):
        client._get("/dataset", {})

    assert responses == []
