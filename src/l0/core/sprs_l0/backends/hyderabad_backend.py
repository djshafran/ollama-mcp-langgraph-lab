from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import urllib.parse
import urllib.request
from typing import Any


def _parse_http_params(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    params = dict(urllib.parse.parse_qsl(raw))
    return params


def _call_http(url: str, text: str) -> bytes:
    method = os.getenv("HYD_PARSER_HTTP_METHOD", "POST").strip().upper() or "POST"
    timeout = float(os.getenv("HYD_PARSER_HTTP_TIMEOUT", "10") or 10)
    params = _parse_http_params(os.getenv("HYD_PARSER_HTTP_PARAMS", ""))
    text_param = os.getenv("HYD_PARSER_TEXT_PARAM", "text").strip() or "text"
    params[text_param] = text

    if method == "GET":
        query = urllib.parse.urlencode(params)
        full_url = url + ("&" if "?" in url else "?") + query
        req = urllib.request.Request(full_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()

    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _call_cli(text: str) -> bytes:
    cmd = os.getenv("HYD_PARSER_CMD", "").strip()
    if not cmd:
        root = os.getenv("HYD_PARSER_ROOT", "").strip()
        if root:
            hint = f"Set HYD_PARSER_CMD to a runnable parser command (HYD_PARSER_ROOT={root})."
        else:
            hint = "Set HYD_PARSER_CMD or HYD_PARSER_URL to enable Hyderabad parser."
        raise RuntimeError(f"HYD_PARSER_CMD not configured. {hint}")

    timeout = float(os.getenv("HYD_PARSER_CLI_TIMEOUT", "10") or 10)
    if "{text}" in cmd:
        cmd = cmd.replace("{text}", text)
        args = shlex.split(cmd)
        proc = subprocess.run(args, capture_output=True, text=False, timeout=timeout)
    else:
        args = shlex.split(cmd)
        proc = subprocess.run(
            args,
            input=text.encode("utf-8"),
            capture_output=True,
            text=False,
            timeout=timeout,
        )

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError(f"HYD parser CLI failed (code {proc.returncode}): {stderr}")

    return proc.stdout


def _parse_dependency_lines(text: str) -> list[dict[str, Any]]:
    deps: list[dict[str, Any]] = []
    pattern_arrow = re.compile(r"(?P<head>-?\d+)\s*[-=]?>\s*(?P<dep>-?\d+)\s*[:=\t ]+\s*(?P<role>\S+)")
    pattern_cols = re.compile(r"(?P<head>-?\d+)\s+(?P<dep>-?\d+)\s+(?P<role>\S+)")

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = pattern_arrow.search(line)
        if not m:
            m = pattern_cols.search(line)
        if not m:
            continue
        deps.append(
            {
                "head": m.group("head"),
                "dep": m.group("dep"),
                "role": m.group("role"),
            }
        )

    return deps


def _extract_dependencies(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in (
            "dependencies",
            "deps",
            "relations",
            "edges",
            "karaka",
            "karakas",
            "links",
        ):
            if isinstance(payload.get(key), list):
                return payload[key]
        # Fallback: first list-valued entry
        for value in payload.values():
            if isinstance(value, list):
                return value
    if isinstance(payload, str):
        return _parse_dependency_lines(payload)
    return []


def parse_dependencies(text: str, tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    url = os.getenv("HYD_PARSER_URL", "").strip()
    if url:
        raw = _call_http(url, text)
    else:
        raw = _call_cli(text)

    decoded = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)

    payload: Any
    try:
        payload = json.loads(decoded)
    except Exception:
        payload = decoded

    deps = _extract_dependencies(payload)
    if not deps:
        raise RuntimeError("Hyderabad parser returned no dependencies")

    # Ensure list of dicts
    normalized: list[dict[str, Any]] = []
    for item in deps:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            head, dep, role = item[:3]
            normalized.append({"head": head, "dep": dep, "role": role})
        elif isinstance(item, str):
            normalized.extend(_parse_dependency_lines(item))

    if not normalized:
        raise RuntimeError("Hyderabad parser output could not be parsed into dependencies")

    return normalized
