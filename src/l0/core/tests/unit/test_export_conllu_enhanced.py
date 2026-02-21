import re

from sprs_l0.analyze import analyze
from sprs_l0.exporter import export_artifacts


def test_export_enhanced_conllu_contains_empty_node_rows(tmp_path):
    spir = analyze("रामः ca वनं", artifacts_dir="src/l0/artifacts/current", kag_mode="full")
    exported = export_artifacts(
        spir,
        formats=["conllu_enhanced", "kag_jsonl", "align_json"],
        output_dir=tmp_path,
    )

    conllu = exported["outputs"]["conllu_enhanced"]
    assert isinstance(conllu, str)
    assert re.search(r"^\d+\.\d+\t", conllu, re.MULTILINE), conllu
    assert (tmp_path / "work.ud.conllu").exists()
    assert (tmp_path / "work.kag.jsonl").exists()
    assert (tmp_path / "work.align.json").exists()
