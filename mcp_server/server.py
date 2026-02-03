import os
from pathlib import Path
from datetime import datetime, timezone

from fastmcp import FastMCP

mcp = FastMCP("LabMCP")

ALLOWED_DIR = Path(os.getenv("ALLOWED_DIR", "/workspace")).resolve()
ALLOWED_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(rel_path: str) -> Path:
    p = (ALLOWED_DIR / rel_path).resolve()
    # prevent path traversal outside ALLOWED_DIR
    if not p.is_relative_to(ALLOWED_DIR):
        raise ValueError("Path escapes ALLOWED_DIR")
    return p


@mcp.tool()
def now_utc_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@mcp.tool()
def list_files(rel_dir: str = ".") -> list[str]:
    """List files under ALLOWED_DIR/rel_dir."""
    d = _safe_path(rel_dir)
    if not d.exists():
        return []
    return [str(p.relative_to(ALLOWED_DIR)) for p in d.rglob("*") if p.is_file()]


@mcp.tool()
def read_text(rel_path: str) -> str:
    """Read a UTF-8 text file under ALLOWED_DIR."""
    p = _safe_path(rel_path)
    return p.read_text(encoding="utf-8")


@mcp.tool()
def write_text(rel_path: str, content: str) -> str:
    """Write a UTF-8 text file under ALLOWED_DIR."""
    p = _safe_path(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content)} chars to {rel_path}"


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    # FastMCP HTTP transport -> endpoint /mcp
    mcp.run(transport="http", host=host, port=port)
