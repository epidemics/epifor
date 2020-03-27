from epifor.common import mix_html_colors


def test_colors():
    assert mix_html_colors() == "#000000"
    assert mix_html_colors(("#023AFF", 1.0)) == "#023AFF"
    assert mix_html_colors(("00FFFF", 0.5), ("FF0000", 0.5)) == "#7F7F7F"

