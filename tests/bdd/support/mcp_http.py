from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests


@dataclass
class McpHttpClient:
    """Tiny MCP-over-HTTP (Streamable HTTP) client for FastMCP servers."""

    url: str
    session_id: Optional[str] = None
    _next_id: int = 0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _rpc(self, payload: dict[str, Any], timeout_s: float = 30.0) -> requests.Response:
        resp = requests.post(self.url, headers=self._headers(), json=payload, timeout=timeout_s)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _parse_response(resp: requests.Response) -> dict[str, Any]:
        try:
            return resp.json()
        except Exception:
            # Fallback for Streamable HTTP (text/event-stream)
            text = resp.content.decode("utf-8", errors="replace")
            events = text.split("\n\n")
            last_payload: str | None = None
            for event in events:
                data_lines: list[str] = []
                for line in event.splitlines():
                    if line.startswith("data:"):
                        data_lines.append(line[len("data:") :].lstrip())
                if data_lines:
                    last_payload = "\n".join(data_lines).strip()
                    if last_payload:
                        try:
                            return json.loads(last_payload)
                        except Exception:
                            continue
            if last_payload:
                return json.loads(last_payload)
            raise

    def initialize(self) -> None:
        if self.session_id:
            return

        self._next_id += 1
        init_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bdd-tests", "version": "0.1.0"},
            },
        }
        resp = self._rpc(init_payload, timeout_s=30.0)

        session_id = (
            resp.headers.get("mcp-session-id")
            or resp.headers.get("Mcp-Session-Id")
            or resp.headers.get("MCP-SESSION-ID")
        )
        if not session_id:
            raise RuntimeError(
                f"No mcp-session-id header from {self.url}. Headers={dict(resp.headers)} Body={resp.text[:300]}"
            )

        self.session_id = session_id

        self._rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout_s=30.0)

    def wait_ready(self, timeout_s: float = 60.0) -> None:
        deadline = time.time() + timeout_s
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                self.initialize()
                return
            except Exception as exc:  # pragma: no cover - retry
                last_err = exc
                time.sleep(0.5)
        raise RuntimeError(f"MCP server not ready at {self.url} after {timeout_s}s") from last_err

    def tools_list(self) -> dict[str, Any]:
        self.initialize()
        self._next_id += 1
        resp = self._rpc({"jsonrpc": "2.0", "id": self._next_id, "method": "tools/list", "params": {}})
        return self._parse_response(resp)

    def tools_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        self._next_id += 1
        resp = self._rpc(
            {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        return self._parse_response(resp)


def extract_json_from_tool_call(resp: dict[str, Any]) -> dict[str, Any]:
    result = resp.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "json" in item and isinstance(item["json"], dict):
                        return item["json"]
                    if "text" in item and isinstance(item["text"], str):
                        text = item["text"].strip()
                        try:
                            obj = json.loads(text)
                            if isinstance(obj, dict):
                                return obj
                        except Exception:
                            pass
        if "tokens" in result and "meta" in result:
            return result
    raise RuntimeError(f"Cannot extract JSON from tools/call response: {resp}")
