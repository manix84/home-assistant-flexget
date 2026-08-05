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
