import asyncio
import contextlib
import os
import unittest
from unittest.mock import patch

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from utils.api_server import BotAPIServer


class FakeTree:
    def get_commands(self):
        return [object(), object()]


class FakeBot:
    def __init__(self, ready=False):
        self.ready = ready
        self.latency = 0.125
        self.guilds = [object()]
        self.tree = FakeTree()

    def is_ready(self):
        return self.ready

    def is_closed(self):
        return False


class BotAPIServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.api = BotAPIServer(FakeBot())
        self.client = TestClient(TestServer(self.api.create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.environment.stop()

    async def test_health_is_public_and_healthy_while_discord_connects(self):
        response = await self.client.get("/health")
        payload = await response.json()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["discord_status"], "connecting")
        self.assertFalse(payload["discord_connected"])

    async def test_keepalive_is_public(self):
        response = await self.client.get("/keepalive")
        payload = await response.json()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["endpoint"], "keepalive")

    async def test_private_endpoints_still_require_api_key(self):
        response = await self.client.get("/api/v1/status")

        self.assertEqual(response.status, 503)

    async def test_self_keepalive_calls_render_external_url(self):
        called = asyncio.Event()

        async def target(request):
            called.set()
            return web.json_response({"status": "ok"})

        target_app = web.Application()
        target_app.router.add_get("/keepalive", target)
        target_server = TestServer(target_app)
        await target_server.start_server()

        self.api.KEEPALIVE_INTERVAL_SECONDS = 0.01
        task = asyncio.create_task(
            self.api._keepalive_loop(str(target_server.make_url("/keepalive")))
        )
        try:
            await asyncio.wait_for(called.wait(), timeout=1)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await target_server.close()

    async def test_server_binds_to_all_interfaces_using_port(self):
        await self.client.close()
        with patch.dict(os.environ, {"PORT": "0"}, clear=True):
            api = BotAPIServer(FakeBot())
            await api.start()
            try:
                sockets = api.site._server.sockets
                self.assertTrue(sockets)
                self.assertEqual(sockets[0].getsockname()[0], "0.0.0.0")
            finally:
                await api.close()
