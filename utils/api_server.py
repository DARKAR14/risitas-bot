import asyncio
import contextlib
import hmac
import os
import time

import aiohttp
from aiohttp import web

from utils.embed_templates import birthday_announcement_payload
from utils.birthday_settings import validate_settings, SettingsConflict


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as error:
        print(
            f"[ERROR] API {request.method} {request.path}: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )
        return web.json_response(
            {"error": "internal_server_error"},
            status=500,
        )


class BotAPIServer:
    """API administrativa para el panel del bot."""

    KEEPALIVE_INTERVAL_SECONDS = 14 * 60

    def __init__(self, bot):
        self.bot = bot
        self.started_at = time.monotonic()
        self.runner = None
        self.site = None
        self.keepalive_task = None
        self.api_key = os.getenv("API_KEY", "")
        origins = os.getenv("API_ALLOWED_ORIGINS", "*")
        self.allowed_origins = {
            origin.strip() for origin in origins.split(",") if origin.strip()
        }

    @web.middleware
    async def cors_middleware(self, request, handler):
        origin = request.headers.get("Origin")
        allowed_origin = None
        if "*" in self.allowed_origins:
            allowed_origin = "*"
        elif origin in self.allowed_origins:
            allowed_origin = origin

        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            response = await handler(request)

        if allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, X-API-Key"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, PUT, PATCH, POST, OPTIONS"
            )
        return response

    @web.middleware
    async def auth_middleware(self, request, handler):
        if request.method == "OPTIONS" or request.path in {
            "/",
            "/health",
            "/keepalive",
        }:
            return await handler(request)

        if not self.api_key:
            return web.json_response(
                {"error": "API_KEY no esta configurada"},
                status=503,
            )

        authorization = request.headers.get("Authorization", "")
        bearer = authorization[7:] if authorization.startswith("Bearer ") else ""
        supplied_key = request.headers.get("X-API-Key", bearer)

        if not supplied_key or not hmac.compare_digest(supplied_key, self.api_key):
            return web.json_response({"error": "unauthorized"}, status=401)

        return await handler(request)

    async def root(self, request):
        return web.json_response(
            {
                "service": "Risitas Bot API",
                "version": "1",
                "features": ["birthday_editor"],
                "status": "online",
                "health": "/health",
                "keepalive": "/keepalive",
                "api": "/api/v1",
            }
        )

    async def health(self, request):
        return web.json_response(self._health_payload("health"))

    async def keepalive(self, request):
        return web.json_response(self._health_payload("keepalive"))

    def _health_payload(self, endpoint):
        connected = self.bot.is_ready() and not self.bot.is_closed()
        latency_ms = None
        if connected and self.bot.latency != float("inf"):
            latency_ms = round(self.bot.latency * 1000, 2)

        return {
            "status": "ok",
            "endpoint": endpoint,
            "discord_status": "connected" if connected else "connecting",
            "discord_connected": connected,
            "latency_ms": latency_ms,
            "guilds": len(self.bot.guilds),
            "commands": len(self.bot.tree.get_commands()),
            "uptime_seconds": round(time.monotonic() - self.started_at),
        }

    async def api_index(self, request):
        return web.json_response(
            {
                "endpoints": {
                    "status": "GET /api/v1/status",
                    "commands": "GET /api/v1/commands",
                    "toggle_command": "PATCH /api/v1/commands/{name}",
                    "sync_commands": "POST /api/v1/commands/sync",
                    "birthday_embed": "GET /api/v1/embeds/birthday",
                    "birthday_settings": "GET, PUT /api/v1/birthday/settings",
                    "birthday_preview": "POST /api/v1/birthday/preview",
                }
            }
        )

    async def status(self, request):
        user = self.bot.user
        return web.json_response(
            {
                "bot": {
                    "id": str(user.id) if user else None,
                    "name": str(user) if user else None,
                    "avatar_url": str(user.display_avatar.url) if user else None,
                },
                "discord_connected": self.bot.is_ready(),
                "latency_ms": round(self.bot.latency * 1000, 2)
                if self.bot.is_ready()
                else None,
                "guilds": len(self.bot.guilds),
                "commands_total": len(self.bot.command_manager.catalog),
                "commands_enabled": len(self.bot.tree.get_commands()),
                "uptime_seconds": round(time.monotonic() - self.started_at),
            }
        )

    async def commands(self, request):
        return web.json_response(
            {"commands": self.bot.command_manager.list_commands()}
        )

    async def update_command(self, request):
        name = request.match_info["name"]
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        if not isinstance(data.get("enabled"), bool):
            return web.json_response(
                {"error": "enabled debe ser true o false"},
                status=400,
            )

        try:
            command = await self.bot.command_manager.set_enabled(
                name,
                data["enabled"],
            )
        except KeyError:
            return web.json_response({"error": "command_not_found"}, status=404)
        except Exception as error:
            return web.json_response(
                {"error": "discord_sync_failed", "detail": str(error)},
                status=502,
            )

        return web.json_response({"command": command})

    async def sync_commands(self, request):
        synced = await self.bot.tree.sync()
        return web.json_response(
            {
                "synced": len(synced),
                "commands": [command.name for command in synced],
            }
        )

    async def birthday_embed(self, request):
        document = await asyncio.to_thread(self.bot.db.birthday_settings().read)
        return web.json_response(
            birthday_announcement_payload(
                user_mention="<@123456789012345678>",
                settings=document["settings"],
            )
        )

    def birthday_options(self):
        channels, roles = [], []
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me) if guild.me else None
                if permissions and permissions.view_channel and permissions.send_messages and permissions.embed_links:
                    channels.append({"id": str(channel.id), "name": channel.name, "guild": guild.name, "guild_id": str(guild.id)})
            for role in guild.roles:
                if not role.is_default():
                    roles.append({"id": str(role.id), "name": role.name, "guild_id": str(guild.id)})
        return {"channels": channels, "roles": roles}

    async def birthday_config(self, request):
        try:
            document = await asyncio.to_thread(self.bot.db.birthday_settings().read)
            return web.json_response({**document, **self.birthday_options(),
                "preview": birthday_announcement_payload(settings=document["settings"])})
        except RuntimeError as error:
            return web.json_response({"error": str(error)}, status=503)

    async def birthday_write(self, request):
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError("Envía un objeto JSON.")
            settings = validate_settings(data.get("settings"))
            if request.path.endswith("/preview"):
                return web.json_response({"preview": birthday_announcement_payload(settings=settings)})
            options = self.birthday_options()
            channel = next((item for item in options["channels"] if item["id"] == settings["channel_id"]), None)
            if settings["enabled"] and not channel:
                raise ValueError("El bot no puede enviar embeds al canal seleccionado. Revisa sus permisos.")
            if settings["role_id"] and (not channel or not any(
                role["id"] == settings["role_id"] and role["guild_id"] == channel["guild_id"] for role in options["roles"]
            )):
                raise ValueError("El rol debe pertenecer al servidor del canal seleccionado.")
            document = await asyncio.to_thread(self.bot.db.birthday_settings().save, settings, data.get("revision"))
            return web.json_response({**document, **options, "preview": birthday_announcement_payload(settings=settings)})
        except SettingsConflict as error:
            return web.json_response({"error": str(error)}, status=409)
        except (ValueError, TypeError) as error:
            return web.json_response({"error": str(error)}, status=400)
        except RuntimeError as error:
            return web.json_response({"error": str(error)}, status=503)

    def create_app(self):
        app = web.Application(
            middlewares=[error_middleware, self.cors_middleware, self.auth_middleware]
        )
        app.router.add_get("/", self.root)
        app.router.add_get("/health", self.health)
        app.router.add_get("/keepalive", self.keepalive)
        app.router.add_get("/api/v1", self.api_index)
        app.router.add_get("/api/v1/status", self.status)
        app.router.add_get("/api/v1/commands", self.commands)
        app.router.add_patch("/api/v1/commands/{name}", self.update_command)
        app.router.add_post("/api/v1/commands/sync", self.sync_commands)
        app.router.add_get("/api/v1/embeds/birthday", self.birthday_embed)
        app.router.add_get("/api/v1/birthday/settings", self.birthday_config)
        app.router.add_put("/api/v1/birthday/settings", self.birthday_write)
        app.router.add_post("/api/v1/birthday/preview", self.birthday_write)
        return app

    async def start(self):
        host = "0.0.0.0"
        port = int(os.getenv("PORT", "10000"))

        try:
            self.runner = web.AppRunner(self.create_app())
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            auth_status = "configurada" if self.api_key else "NO CONFIGURADA"
            print(f"[OK] API HTTP escuchando en {host}:{port}", flush=True)
            print(f"[INFO] Seguridad API_KEY: {auth_status}", flush=True)
            self._start_keepalive()
        except Exception as error:
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            print(
                f"[ERROR] No se pudo iniciar la API HTTP: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            raise

    def _start_keepalive(self):
        external_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
        if not external_url:
            print(
                "[INFO] Autollamada desactivada: RENDER_EXTERNAL_URL no definida.",
                flush=True,
            )
            return

        keepalive_url = f"{external_url}/keepalive"
        self.keepalive_task = asyncio.create_task(
            self._keepalive_loop(keepalive_url),
            name="render-self-keepalive",
        )
        print(
            "[OK] Autollamada de Render configurada cada 14 minutos.",
            flush=True,
        )

    async def _keepalive_loop(self, keepalive_url):
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                await asyncio.sleep(self.KEEPALIVE_INTERVAL_SECONDS)
                try:
                    async with session.get(keepalive_url) as response:
                        await response.read()
                        if response.status >= 400:
                            print(
                                f"[WARN] Autollamada respondio HTTP {response.status}.",
                                flush=True,
                            )
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    print(
                        f"[WARN] Fallo la autollamada de Render: "
                        f"{type(error).__name__}: {error}",
                        flush=True,
                    )

    async def close(self):
        if self.keepalive_task:
            self.keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.keepalive_task
            self.keepalive_task = None

        if self.runner:
            await self.runner.cleanup()
            self.runner = None
            self.site = None
