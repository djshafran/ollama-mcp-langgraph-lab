from sprs_l0.analyze import analyze


def test_kag_event_deontic_norms_present():
    spir = analyze(
        "कर्मण्येवाधिकारस्ते मा फलेषु । मा ते सङ्गोस्त्वकर्मणि",
        kag_mode="full",
        include_provenance=True,
    )
    kag = spir["semantics"]["kag"]
    assert isinstance(kag.get("nodes"), list)
    assert isinstance(kag.get("edges"), list)
    norms = kag.get("norms", [])
    assert isinstance(norms, list)
    assert len(norms) >= 1
    event_nodes = [node for node in kag["nodes"] if node.get("type") == "Event"]
    assert len(event_nodes) >= 1
    modalities = {norm.get("modality") for norm in norms}
    assert "prohibition" in modalities or "right" in modalities
    assert all(isinstance((norm.get("provenance") or {}).get("clause_id"), str) for norm in norms)
