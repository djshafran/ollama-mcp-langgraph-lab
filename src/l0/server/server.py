import os
from pathlib import Path

from fastmcp import FastMCP

from sprs_l0 import (
    analyze,
    compress_passages,
    constraints,
    export_artifacts,
    extract_keys,
    query_understand,
    retrieve_candidates,
    validate_spir,
)

mcp = FastMCP("L0")

ARTIFACT_DIR = Path(os.getenv("L0_ARTIFACT_DIR", "/artifacts/current"))
DATA_DIR = Path(os.getenv("L0_DATA_DIR", "/data"))


@mcp.tool()
def l0_analyze(
    text: str,
    input_format: str = "auto",
    k_best: int = 5,
    return_lattice: bool = True,
    syntax_backend: str | None = None,
    return_ud: bool = True,
    return_syntax: bool = True,
    ud_mode: str = "head_rules",
    include_enhanced: bool = True,
    include_kag: bool = True,
    include_provenance: bool = True,
    doc: str | None = None,
    ref: str | None = None,
) -> dict:
    """Analyze input text into SPIR v0.5 with syntax + KAG."""
    return analyze(
        text,
        input_format=input_format,
        k_best=k_best,
        return_lattice=return_lattice,
        artifacts_dir=str(ARTIFACT_DIR),
        syntax_backend=syntax_backend,
        return_ud=return_ud,
        return_syntax=return_syntax,
        ud_mode=ud_mode,
        include_enhanced=include_enhanced,
        kag_mode="full" if include_kag else "none",
        include_provenance=include_provenance,
        doc=doc,
        ref=ref,
    )


@mcp.tool()
def l0_query_understand(
    text: str | None = None,
    spir: dict | None = None,
    max_terms: int = 12,
) -> dict:
    """Build KAG-aware query plan from text or SPIR."""

    def _analyzer(payload: str) -> dict:
        return analyze(payload, artifacts_dir=str(ARTIFACT_DIR), kag_mode="full")

    return query_understand(
        text=text,
        spir=spir,
        analyzer=_analyzer,
        max_terms=max_terms,
    )


@mcp.tool()
def l0_retrieve(
    kag_query: dict,
    top_k: int = 5,
    filters: dict | None = None,
    corpus_path: str | None = None,
    retrieval_backend: str | None = None,
) -> dict:
    """Tiered retrieval backend: baseline or hybrid_prod."""
    return retrieve_candidates(
        kag_query,
        top_k=top_k,
        filters=filters,
        corpus_path=corpus_path,
        artifacts_dir=str(ARTIFACT_DIR),
        retrieval_backend=retrieval_backend,
    )


@mcp.tool()
def l0_export(
    spir: dict,
    formats: list[str] | None = None,
    output_dir: str | None = None,
) -> dict:
    """Export sidecar artifacts: conllu_basic, conllu_enhanced, kag_jsonl, align_json."""
    return export_artifacts(
        spir,
        formats=formats,
        output_dir=output_dir,
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
    """Validate SPIR v0.5 structure."""
    return validate_spir(spir)


@mcp.tool()
def l0_constraints(state_or_spir: dict) -> dict:
    """Return hard/soft constraints (placeholder)."""
    return constraints(state_or_spir)


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)
