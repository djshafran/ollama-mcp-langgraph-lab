import os
from pathlib import Path

from fastmcp import FastMCP

from sprs_l0 import analyze, compress_passages, constraints, extract_keys, validate_spir

mcp = FastMCP("L0")

ARTIFACT_DIR = Path(os.getenv("L0_ARTIFACT_DIR", "/artifacts/current"))
DATA_DIR = Path(os.getenv("L0_DATA_DIR", "/data"))


@mcp.tool()
def l0_analyze(
    text: str,
    input_format: str = "auto",
    k_best: int = 5,
    return_lattice: bool = True,
) -> dict:
    """Analyze input text into SPIR v0.1."""
    return analyze(
        text,
        input_format=input_format,
        k_best=k_best,
        return_lattice=return_lattice,
        artifacts_dir=str(ARTIFACT_DIR),
    )


@mcp.tool()
def l0_keys(query_spir: dict, max_terms: int = 12) -> dict:
    """Extract key terms from SPIR."""
    return extract_keys(query_spir, max_terms=max_terms)


@mcp.tool()
def l0_compress(
    query_spir: dict,
    passages: list,
    policy: str | None = None,
    max_chars: int = 2000,
) -> dict:
    """Compress passages with a simple policy."""
    return compress_passages(
        query_spir=query_spir,
        passages=passages,
        policy=policy,
        max_chars=max_chars,
    )


@mcp.tool()
def l0_validate(spir: dict) -> dict:
    """Validate SPIR structure."""
    return validate_spir(spir)


@mcp.tool()
def l0_constraints(state_or_spir: dict) -> dict:
    """Return hard/soft constraints (placeholder)."""
    return constraints(state_or_spir)


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)
