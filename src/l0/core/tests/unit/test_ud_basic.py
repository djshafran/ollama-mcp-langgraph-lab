from sprs_l0.ud import map_karaka_to_ud, validate_basic_ud_tree


def test_ud_basic_tree_validity():
    tokens = [
        {"surface": "रामः", "lemma": "राम"},
        {"surface": "वनं", "lemma": "वन"},
        {"surface": "गच्छति", "lemma": "गम्"},
    ]
    karaka_edges = [
        {"head": None, "dep": 2, "role": "root"},
        {"head": 2, "dep": 0, "role": "kartṛ"},
        {"head": 2, "dep": 1, "role": "karman"},
    ]
    basic, meta = map_karaka_to_ud(karaka_edges, tokens=tokens)
    assert meta["errors"] == []
    ok, errors, _warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic)
    assert ok, errors
    roots = [e for e in basic if e.get("head") is None and e.get("rel") == "root"]
    assert len(roots) == 1


def test_ud_basic_tree_detects_cycle():
    tokens = [
        {"surface": "a", "lemma": "a"},
        {"surface": "b", "lemma": "b"},
    ]
    basic = [
        {"head": 1, "dep": 0, "rel": "dep"},
        {"head": 0, "dep": 1, "rel": "root"},
    ]
    ok, errors, _warnings = validate_basic_ud_tree(tokens=tokens, basic_edges=basic)
    assert not ok
    assert errors

