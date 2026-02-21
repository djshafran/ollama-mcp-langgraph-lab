import json

from sprs_l0.analyze import analyze
from sprs_l0.normalize import normalize_text
from sprs_l0.spir import hash_text


def test_overrides_recompute_downstream_layers(tmp_path, monkeypatch):
    text = "रामः वनं गच्छति । मा फलम्"
    normalized = normalize_text(text)
    input_hash = hash_text(normalized)

    override_path = tmp_path / "overrides.jsonl"
    override = {
        "input_hash": input_hash,
        "ud_patch": {
            "replace_all": [
                {"head": None, "dep": 0, "rel": "root"},
                {"head": 0, "dep": 1, "rel": "dep"},
                {"head": 0, "dep": 2, "rel": "dep"},
                {"head": 0, "dep": 3, "rel": "punct"},
                {"head": 0, "dep": 4, "rel": "dep"},
                {"head": 0, "dep": 5, "rel": "dep"},
            ]
        },
    }
    override_path.write_text(json.dumps(override, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("SYNTAX_OVERRIDES_PATH", str(override_path))

    spir = analyze(text, artifacts_dir="src/l0/artifacts/current", kag_mode="full")
    syntax = spir["syntax"]
    clauses = syntax["clauses"]
    kag = spir["semantics"]["kag"]

    assert syntax["meta"]["overrides_applied"] is True
    assert clauses[0]["root_token_id"] == 0
    event_roots = {node.get("data", {}).get("root_token_id") for node in kag["nodes"] if node.get("type") == "Event"}
    assert 0 in event_roots
