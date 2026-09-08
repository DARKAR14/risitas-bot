"""Descarga cloudflared para el contenedor Linux de Discloud."""

import os
import platform
import stat
import urllib.request
from pathlib import Path


DOWNLOADS = {
    "x86_64": "cloudflared-linux-amd64",
    "amd64": "cloudflared-linux-amd64",
    "aarch64": "cloudflared-linux-arm64",
    "arm64": "cloudflared-linux-arm64",
}


def main():
    if platform.system() != "Linux":
        print("[INFO] cloudflared solo se instala durante el build Linux.")
        return

    architecture = platform.machine().lower()
    asset = DOWNLOADS.get(architecture)
    if not asset:
        raise RuntimeError(f"Arquitectura no compatible: {architecture}")

    project_root = Path(__file__).resolve().parent.parent
    binary_path = project_root / "bin" / "cloudflared"
    binary_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{asset}"
    print(f"[BUILD] Descargando {asset}...", flush=True)
    urllib.request.urlretrieve(url, binary_path)
    binary_path.chmod(binary_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    if not binary_path.exists() or binary_path.stat().st_size == 0:
        raise RuntimeError("La descarga de cloudflared quedo vacia")

    print("[BUILD] cloudflared instalado correctamente.", flush=True)


if __name__ == "__main__":
    main()
