from sprs_l0.analyze import analyze


def test_provenance_is_attached_to_kag():
    spir = analyze("रामः वनं गच्छति", kag_mode="full", include_provenance=True)
    kag = spir["semantics"]["kag"]

    for node in kag.get("nodes", []):
        prov = node.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov

    for edge in kag.get("edges", []):
        prov = edge.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov

    for norm in kag.get("norms", []):
        prov = norm.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov

