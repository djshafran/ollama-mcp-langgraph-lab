from sprs_l0.ud import build_basic_ud, load_head_rules, map_karaka_to_ud, validate_basic_ud_tree


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


def test_ud_head_rules_mode_is_deterministic():
    tokens = [
        {"surface": "रामः", "lemma": "राम", "pos": "NOUN", "feats": {"case": "nom"}},
        {"surface": "वनं", "lemma": "वन", "pos": "NOUN", "feats": {"case": "acc"}},
        {"surface": "गच्छति", "lemma": "गम्", "pos": "VERB", "feats": {"verbform": "fin"}},
    ]
    paninian_edges = [
        {"head": None, "dep": 2, "role": "root"},
        {"head": 2, "dep": 0, "role": "kartṛ"},
        {"head": 2, "dep": 1, "role": "karman"},
    ]
    mapping = {"kartṛ": "nsubj", "karman": "obj", "root": "root", "dep": "dep"}
    rules = [
        {"id": "finite_verb_root", "priority": 100},
        {"id": "fallback_first_content", "priority": 1},
    ]
    first, _ = build_basic_ud(
        tokens=tokens,
        paninian_edges=paninian_edges,
        mapping=mapping,
        ud_mode="head_rules",
        head_rules=rules,
    )
    second, _ = build_basic_ud(
        tokens=tokens,
        paninian_edges=paninian_edges,
        mapping=mapping,
        ud_mode="head_rules",
        head_rules=rules,
    )
    assert first == second


def test_head_rules_file_is_runtime_active(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    syntax_dir = artifacts_dir / "syntax"
    syntax_dir.mkdir(parents=True)
    (syntax_dir / "head_rules.yaml").write_text(
        "\n".join(
            [
                "version: test",
                "rules:",
                "  - id: fallback_first_content",
                "    priority: 100",
                "  - id: finite_verb_root",
                "    priority: 10",
            ]
        ),
        encoding="utf-8",
    )
    rules, version = load_head_rules(artifacts_dir=artifacts_dir)
    assert version == "test"

    tokens = [
        {"surface": "रामः", "lemma": "राम", "pos": "NOUN", "feats": {"case": "nom"}},
        {"surface": "वनं", "lemma": "वन", "pos": "NOUN", "feats": {"case": "acc"}},
        {"surface": "गच्छति", "lemma": "गम्", "pos": "VERB", "feats": {"verbform": "fin"}},
    ]
    paninian_edges = [
        {"head": None, "dep": 2, "role": "root"},
        {"head": 2, "dep": 0, "role": "kartṛ"},
        {"head": 2, "dep": 1, "role": "karman"},
    ]
    mapping = {"kartṛ": "nsubj", "karman": "obj", "root": "root", "dep": "dep"}
    basic, _meta = build_basic_ud(
        tokens=tokens,
        paninian_edges=paninian_edges,
        mapping=mapping,
        ud_mode="head_rules",
        head_rules=rules,
    )
    roots = [edge for edge in basic if edge["head"] is None and edge["rel"] == "root"]
    assert roots[0]["dep"] == 0
