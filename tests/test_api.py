"""Tests for the asynchronous FlexGet client."""

import pytest
from aiohttp import ClientSession, web

from custom_components.flexget.api import (
    FlexGetAuthenticationError,
    FlexGetClient,
    FlexGetEndpoint,
    FlexGetUnsupportedApiError,
    normalize_api_path,
)


def test_endpoint_normalization_and_uniqueness() -> None:
    endpoint = FlexGetEndpoint("TORBOX.local.", 5053, "api/")
    assert endpoint.base_url == "http://torbox.local:5053/api"
    assert endpoint.unique_id == "torbox.local:5053"
    assert FlexGetEndpoint("torbox.local", 5054).unique_id != endpoint.unique_id


def test_normalize_api_path_rejects_urls() -> None:
    with pytest.raises(ValueError):
        normalize_api_path("https://example.test/api")


async def test_client_sends_token_and_queries_version(aiohttp_server, socket_enabled) -> None:
    async def version(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == "Token secret-token"
        return web.json_response({"flexget_version": "3.15.31", "api_version": "1.8"})

    app = web.Application()
    app.router.add_get("/api/server/version/", version)
    server = await aiohttp_server(app)
    endpoint = FlexGetEndpoint("127.0.0.1", server.port)
    async with ClientSession() as session:
        client = FlexGetClient(session, endpoint, "secret-token")
        assert (await client.async_get_version())["flexget_version"] == "3.15.31"


async def test_client_reads_history_total_count(aiohttp_server, socket_enabled) -> None:
    """Return pagination metadata alongside the newest history entry."""

    async def history(request: web.Request) -> web.Response:
        assert request.query == {"per_page": "1", "page": "1", "order": "desc"}
        return web.json_response(
            [{"task": "sort", "time": "2026-08-05T13:05:49.010966"}],
            headers={"Total-Count": "123"},
        )

    app = web.Application()
    app.router.add_get("/api/history/", history)
    server = await aiohttp_server(app)
    async with ClientSession() as session:
        client = FlexGetClient(session, FlexGetEndpoint("127.0.0.1", server.port), "token")
        data, count = await client.async_get_history_summary()
    assert count == 123
    assert data[0]["task"] == "sort"


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, FlexGetAuthenticationError),
        (403, FlexGetAuthenticationError),
        (404, FlexGetUnsupportedApiError),
    ],
)
async def test_client_maps_errors(aiohttp_server, socket_enabled, status, error) -> None:
    async def version(request: web.Request) -> web.Response:
        return web.Response(status=status)

    app = web.Application()
    app.router.add_get("/api/server/version/", version)
    server = await aiohttp_server(app)
    async with ClientSession() as session:
        client = FlexGetClient(session, FlexGetEndpoint("127.0.0.1", server.port), "bad")
        with pytest.raises(error):
            await client.async_get_version()
