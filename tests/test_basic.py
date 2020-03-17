import pathlib
import subprocess
import sys

import pytest


def test_imports():
    import epifor
    from epifor import Regions, Region
    from epifor.data import CSSEData, FTPrediction, FTData
    from epifor.gleam import GleamDef


SCRIPTS = ["estimate.py", "fetch_foretold.py", "parameterize.py"]


@pytest.mark.parametrize("path", SCRIPTS)
def test_scripts_help(path):
    path = pathlib.Path(path)
    r = subprocess.run(
        ["python3", path, "--help"], stderr=subprocess.PIPE, stdout=subprocess.PIPE
    )
    if r.returncode != 0:
        sys.stdout.write(r.stdout.decode('utf8'))
        sys.stderr.write(r.stderr.decode('utf8'))
        assert r.returncode == 0
