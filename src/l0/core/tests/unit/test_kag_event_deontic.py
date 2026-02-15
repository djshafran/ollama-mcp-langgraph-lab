from sprs_l0.analyze import analyze


def test_kag_event_deontic_norms_present():
    spir = analyze("कर्मण्येवाधिकारस्ते मा फलेषु कदाचन", kag_mode="full", include_provenance=True)
    kag = spir["semantics"]["kag"]
    assert isinstance(kag.get("nodes"), list)
    assert isinstance(kag.get("edges"), list)
    norms = kag.get("norms", [])
    assert isinstance(norms, list)
    assert len(norms) >= 1
    modalities = {norm.get("modality") for norm in norms}
    assert "prohibition" in modalities or "right" in modalities

