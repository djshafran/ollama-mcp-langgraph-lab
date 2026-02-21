from copy import deepcopy

from sprs_l0.analyze import analyze
from sprs_l0.validate import validate_spir


def _base_spir() -> dict:
    return analyze("मा रामः वनं गच्छति", artifacts_dir="src/l0/artifacts/current", kag_mode="full")


def test_validate_rejects_invalid_empty_node_id():
    spir = _base_spir()
    bad = deepcopy(spir)
    bad["syntax"]["ud"]["empty_nodes"] = [
        {
            "id": "E1",
            "anchor_token_id": 0,
            "predicate": "ELIDED",
        }
    ]
    bad["syntax"]["ud"]["enhanced_edges"].append({"head": 0, "dep": "E1", "rel": "dep"})

    result = validate_spir(bad)
    assert result["ok"] is False
    assert any("empty_nodes" in err for err in result["errors"])


def test_validate_rejects_unknown_enhanced_node_ref():
    spir = _base_spir()
    bad = deepcopy(spir)
    bad["syntax"]["ud"]["enhanced_edges"].append({"head": "1.1", "dep": "9.9", "rel": "dep"})
    bad["syntax"]["ud"]["empty_nodes"] = [
        {
            "id": "1.1",
            "anchor_token_id": 0,
            "predicate": "ELIDED",
        }
    ]

    result = validate_spir(bad)
    assert result["ok"] is False
    assert any("enhanced_edges" in err and "unknown node ref" in err for err in result["errors"])


def test_validate_rejects_unknown_kag_clause_reference():
    spir = _base_spir()
    bad = deepcopy(spir)
    assert bad["semantics"]["kag"]["norms"], "Expected at least one norm for test fixture"
    bad["semantics"]["kag"]["norms"][0]["provenance"]["clause_id"] = "c999"

    result = validate_spir(bad)
    assert result["ok"] is False
    assert any("provenance.clause_id" in err for err in result["errors"])
