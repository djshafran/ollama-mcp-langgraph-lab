from __future__ import annotations

import os
import subprocess
from pathlib import Path

from testcontainers.compose import DockerCompose  # type: ignore

from tests.bdd.support.mcp_http import McpHttpClient


def before_all(context):
    project_root = Path(__file__).resolve().parents[2]
    compose_file = os.getenv("BDD_COMPOSE_FILE", "docker-compose.bdd.yml")

    context.compose = DockerCompose(
        context=str(project_root),
        compose_file_name=compose_file,
        pull=False,
        build=True,
    )
    context.compose.start()

    # Resolve host/port via docker compose CLI for compatibility across testcontainers versions.
    port_out = subprocess.check_output(
        ["docker", "compose", "-f", compose_file, "port", "l0", "8000"],
        cwd=str(project_root),
        text=True,
    ).strip()
    # format: 0.0.0.0:PORT or [::]:PORT
    host = "localhost"
    port = port_out.rsplit(":", 1)[-1]
    context.l0_mcp_url = f"http://{host}:{port}/mcp"

    context.mcp = McpHttpClient(context.l0_mcp_url)
    context.mcp.wait_ready(timeout_s=60.0)


def after_all(context):
    compose = getattr(context, "compose", None)
    if compose is not None:
        try:
            compose.stop()
        except Exception:
            pass
