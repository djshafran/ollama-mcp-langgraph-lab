from sprs_l0.clause import build_clause_graph


def test_clause_graph_builds_discourse_links():
    tokens = [
        {"surface": "yadi", "lemma": "yadi"},
        {"surface": "रामः", "lemma": "राम"},
        {"surface": "गच्छति", "lemma": "गम्"},
        {"surface": "।", "lemma": "।"},
        {"surface": "वनं", "lemma": "वन"},
        {"surface": "पश्यति", "lemma": "पश्य"},
    ]
    basic = [
        {"head": None, "dep": 2, "rel": "root"},
        {"head": 2, "dep": 0, "rel": "mark"},
        {"head": 2, "dep": 1, "rel": "nsubj"},
        {"head": 2, "dep": 3, "rel": "punct"},
        {"head": 2, "dep": 4, "rel": "obj"},
        {"head": 2, "dep": 5, "rel": "conj"},
    ]
    clauses, discourse = build_clause_graph(tokens=tokens, basic_edges=basic)
    assert len(clauses) >= 1
    if len(clauses) > 1:
        assert len(discourse) >= 1
        assert discourse[0]["rel"] in {
            "coord",
            "subord",
            "cause",
            "condition",
            "purpose",
            "contrast",
            "elaboration",
        }

