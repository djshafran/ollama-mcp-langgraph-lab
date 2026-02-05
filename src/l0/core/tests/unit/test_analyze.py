from sprs_l0.analyze import analyze
from sprs_l0.validate import validate_spir


def test_analyze_validate_ok():
    spir = analyze("Om namah shivaya")
    result = validate_spir(spir)
    assert result["ok"] is True
