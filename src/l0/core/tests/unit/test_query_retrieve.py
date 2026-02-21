from sprs_l0.analyze import analyze
from sprs_l0.query import query_understand
from sprs_l0.retrieve import retrieve_candidates


def test_query_understand_and_retrieve_with_provenance():
    spir = analyze("धर्मक्षेत्रे कुरुक्षेत्रे", kag_mode="full")
    bundle = query_understand(spir=spir)
    out = retrieve_candidates(
        bundle["kag_query"],
        top_k=2,
        artifacts_dir="src/l0/artifacts/current",
        retrieval_backend="hybrid_prod",
    )
    assert isinstance(out.get("candidates"), list)
    assert len(out["candidates"]) >= 1
    assert isinstance(out.get("provenance"), list)
    assert len(out["provenance"]) >= 1
    assert isinstance(out.get("meta"), dict)
    assert out["meta"].get("backend_requested") == "hybrid_prod"
    assert out["meta"].get("backend_used") in {"hybrid_prod", "hybrid_prod_partial", "baseline"}
