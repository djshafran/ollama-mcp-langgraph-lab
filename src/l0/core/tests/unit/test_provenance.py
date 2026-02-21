from sprs_l0.analyze import analyze


def test_provenance_is_attached_to_kag():
    spir = analyze("रामः वनं गच्छति", kag_mode="full", include_provenance=True)
    kag = spir["semantics"]["kag"]
    clauses = spir["syntax"]["clauses"]
    clause_ids = {clause["clause_id"] for clause in clauses}
    token_count = len(spir["tokens"])

    for node in kag.get("nodes", []):
        prov = node.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov
        for token_id in prov.get("token_ids", []):
            assert 0 <= token_id < token_count
        clause_id = prov.get("clause_id")
        if clause_id is not None:
            assert clause_id in clause_ids

    for edge in kag.get("edges", []):
        prov = edge.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov
        clause_id = prov.get("clause_id")
        if clause_id is not None:
            assert clause_id in clause_ids

    for norm in kag.get("norms", []):
        prov = norm.get("provenance")
        assert isinstance(prov, dict)
        assert "token_ids" in prov
        assert "source_ref" in prov
        clause_id = prov.get("clause_id")
        if clause_id is not None:
            assert clause_id in clause_ids
