from pathlib import Path

from epifor import Regions


def test_region_yaml(tmp_path):
    p1 = Path("data/regions.yaml")
    p2 = tmp_path / "tmp.yaml"
    rs = Regions.load_from_yaml(p1)
    with open(p2, 'wt') as f:
        rs.write_yaml(f)
    rs2 = Regions.load_from_yaml(p2)
    assert rs.root == rs2.root
    #assert p1.read_text() == p2.read_text()
