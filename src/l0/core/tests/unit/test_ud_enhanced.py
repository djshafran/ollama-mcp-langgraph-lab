from sprs_l0.eud import build_enhanced_ud


def test_enhanced_ud_adds_empty_node_for_elliptic_clause():
    tokens = [
        {"surface": "रामः", "lemma": "राम"},
        {"surface": "ca", "lemma": "ca"},
        {"surface": "वनं", "lemma": "वन"},
    ]
    basic = [
        {"head": None, "dep": 0, "rel": "root"},
        {"head": 0, "dep": 1, "rel": "dep"},
        {"head": 0, "dep": 2, "rel": "obj"},
    ]
    clauses = [{"clause_id": "c1", "root_token_id": 0, "token_span": [0, 3], "clause_type": "elliptic"}]

    enhanced, empty_nodes, _meta = build_enhanced_ud(tokens=tokens, basic_edges=basic, clauses=clauses)
    assert len(enhanced) >= len(basic)
    assert len(empty_nodes) >= 1
    assert "." in empty_nodes[0]["id"]
    assert isinstance(empty_nodes[0]["anchor_token_id"], int)
    assert any(isinstance(edge.get("dep"), str) for edge in enhanced)
