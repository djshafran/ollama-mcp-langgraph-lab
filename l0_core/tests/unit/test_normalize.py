from sprs_l0.normalize import normalize_text


def test_normalize_text_collapses_whitespace():
    assert normalize_text("  a   b \n c ") == "a b c"
