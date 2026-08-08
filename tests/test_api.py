"""Tests for the asynchronous FlexGet client."""

from datetime import datetime

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
    endpoint = FlexGetEndpoint("FLEXGET.local.", 5053, "api/")
    assert endpoint.base_url == "http://flexget.local:5053/api"
    assert endpoint.unique_id == "flexget.local:5053"
    assert FlexGetEndpoint("flexget.local", 5054).unique_id != endpoint.unique_id


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


async def test_client_reads_optional_monitoring_endpoints(aiohttp_server, socket_enabled) -> None:
    """Query monitoring endpoints with bounded payloads."""

    async def status(request: web.Request) -> web.Response:
        assert request.query["include_execution"] == "true"
        return web.json_response([{"id": 4, "name": "sort", "last_execution": {}}])

    async def failed(request: web.Request) -> web.Response:
        assert request.query["per_page"] == "100"
        return web.json_response([], headers={"Total-Count": "3"})

    async def pending(request: web.Request) -> web.Response:
        assert request.query["approved"] == "false"
        assert request.query["order"] == "asc"
        return web.json_response([], headers={"Total-Count": "2"})

    async def schedule(request: web.Request) -> web.Response:
        return web.json_response({"id": 17, "next_run_time": "2026-08-05T14:00:00+00:00"})

    async def executions(request: web.Request) -> web.Response:
        assert request.query["start_date"] == "2026-08-05T00:00:00+00:00"
        assert request.query["produced"] == "false"
        return web.json_response([{"succeeded": True, "accepted": 1}])

    async def task(request: web.Request) -> web.Response:
        if request.method == "PUT":
            payload = await request.json()
            assert payload == {"name": "sort", "config": {"manual": True}}
        return web.json_response({"name": "sort", "config": {"manual": True}})

    async def execute(request: web.Request) -> web.Response:
        assert await request.json() == {"tasks": ["sort"]}
        return web.json_response({"tasks": [{"id": "one", "name": "sort"}]})

    async def plugins(request: web.Request) -> web.Response:
        assert request.query["include_schema"] == "false"
        return web.json_response([{"name": "rss", "builtin": True}], headers={"Total-Count": "1"})

    async def irc_connections(request: web.Request) -> web.Response:
        return web.json_response([{"announce": {"alive": True, "connected_channels": []}}])

    async def series(request: web.Request) -> web.Response:
        assert request.query["per_page"] == "1"
        return web.json_response([], headers={"Total-Count": "12"})

    async def managed_lists(request: web.Request) -> web.Response:
        return web.json_response([{"id": 1, "name": "example"}])

    app = web.Application()
    app.router.add_get("/api/tasks/status/", status)
    app.router.add_get("/api/failed/", failed)
    app.router.add_get("/api/pending/", pending)
    app.router.add_get("/api/schedules/17/", schedule)
    app.router.add_get("/api/tasks/status/4/executions/", executions)
    app.router.add_get("/api/tasks/sort/", task)
    app.router.add_put("/api/tasks/sort/", task)
    app.router.add_post("/api/tasks/execute/", execute)
    app.router.add_get("/api/plugins/", plugins)
    app.router.add_get("/api/irc/connections/", irc_connections)
    app.router.add_get("/api/series/", series)
    app.router.add_get("/api/entry_list/", managed_lists)
    app.router.add_get("/api/movie_list/", managed_lists)
    app.router.add_get("/api/pending_list/", managed_lists)
    server = await aiohttp_server(app)
    async with ClientSession() as session:
        client = FlexGetClient(session, FlexGetEndpoint("127.0.0.1", server.port), "token")
        assert (await client.async_get_task_status())[0]["name"] == "sort"
        assert (await client.async_get_failed_summary())[1] == 3
        assert (await client.async_get_pending_approval_summary())[1] == 2
        assert (await client.async_get_schedule_details([{"id": 17}]))[0]["id"] == 17
        recent = await client.async_get_recent_executions(
            [{"id": 4}], datetime.fromisoformat("2026-08-05T00:00:00+00:00")
        )
        assert recent[0][0]["accepted"] == 1
        assert (await client.async_get_task("sort"))["config"]["manual"] is True
        await client.async_update_task("sort", {"manual": True})
        await client.async_execute_task("sort")
        assert (await client.async_get_plugins())[0]["name"] == "rss"
        assert len(await client.async_get_irc_connections()) == 1
        assert await client.async_get_series_count() == 12
        assert len(await client.async_get_entry_lists()) == 1
        assert len(await client.async_get_movie_lists()) == 1
        assert len(await client.async_get_pending_lists()) == 1


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
