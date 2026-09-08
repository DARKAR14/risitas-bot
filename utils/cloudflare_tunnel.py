import asyncio
import contextlib
import os
from pathlib import Path


class CloudflareTunnel:
    """Ejecuta y supervisa un Cloudflare Tunnel administrado remotamente."""

    def __init__(self):
        self.token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
        self.binary = Path(__file__).resolve().parent.parent / "bin" / "cloudflared"
        self.process = None
        self.supervisor_task = None
        self.stopping = False

    async def start(self):
        if not self.token:
            print(
                "[INFO] Cloudflare Tunnel desactivado: "
                "CLOUDFLARE_TUNNEL_TOKEN no configurado.",
                flush=True,
            )
            return

        if any(character.isspace() for character in self.token) or not self.token.startswith("eyJ"):
            print(
                "[ERROR] CLOUDFLARE_TUNNEL_TOKEN no tiene el formato esperado. "
                "Pega solamente el token que empieza por 'eyJ', no el comando completo.",
                flush=True,
            )
            return

        if not self.binary.exists():
            print(
                "[WARN] No se encontro bin/cloudflared. "
                "Intentando instalarlo automaticamente...",
                flush=True,
            )
            try:
                from utils.install_cloudflared import main as install_cloudflared

                await asyncio.to_thread(install_cloudflared)
            except Exception as error:
                print(
                    f"[ERROR] No se pudo instalar cloudflared: "
                    f"{type(error).__name__}: {error}",
                    flush=True,
                )
                return

            if not self.binary.exists():
                print(
                    "[ERROR] cloudflared sigue sin estar disponible "
                    "despues de la instalacion.",
                    flush=True,
                )
                return

        self.stopping = False
        self.supervisor_task = asyncio.create_task(
            self._supervise(),
            name="cloudflare-tunnel-supervisor",
        )

    async def _supervise(self):
        restart_delay = 10

        while not self.stopping:
            try:
                self.process = await asyncio.create_subprocess_exec(
                    str(self.binary),
                    "tunnel",
                    "--no-autoupdate",
                    "--protocol",
                    "http2",
                    "run",
                    "--token",
                    self.token,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                print("[OK] Cloudflare Tunnel iniciado.", flush=True)
                await self._read_output()
                exit_code = await self.process.wait()
                self.process = None

                if not self.stopping:
                    print(
                        f"[WARN] Cloudflare Tunnel termino con codigo {exit_code}. "
                        f"Reintentando en {restart_delay} segundos.",
                        flush=True,
                    )
                    await asyncio.sleep(restart_delay)
            except asyncio.CancelledError:
                break
            except Exception as error:
                print(
                    f"[ERROR] Cloudflare Tunnel: "
                    f"{type(error).__name__}: {error}",
                    flush=True,
                )
                await asyncio.sleep(restart_delay)

    async def _read_output(self):
        if not self.process or not self.process.stdout:
            return

        async for raw_line in self.process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            safe_line = line.replace(self.token, "[TOKEN OCULTO]")
            lowered = safe_line.lower()

            if any(
                word in lowered
                for word in (
                    "error",
                    "failed",
                    "invalid",
                    "registered",
                    "connected",
                    "connection",
                )
            ):
                print(f"[cloudflared] {safe_line}", flush=True)

    async def close(self):
        self.stopping = True

        if self.process and self.process.returncode is None:
            self.process.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self.process.wait(), timeout=10)

            if self.process.returncode is None:
                self.process.kill()
                await self.process.wait()

        if self.supervisor_task:
            self.supervisor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.supervisor_task
            self.supervisor_task = None
