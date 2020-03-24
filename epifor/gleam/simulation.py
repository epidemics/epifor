import logging
import pathlib

import h5py

from .gleamdef import GleamDef

log = logging.getLogger(__name__)


class Simulation:
    def __init__(self, gleamdef, hdf_file, dir_path=None):
        self.definition = gleamdef
        self.name = self.definition.get_name()
        assert hdf_file is None or isinstance(hdf_file, h5py.File)
        self.hdf = hdf_file
        self.dir = dir_path

    @classmethod
    def load_dir(cls, path, skip_unfinished=False):
        path = pathlib.Path(path)
        h5path = path / "results.h5"
        if skip_unfinished and not h5path.exists():
            log.info("Skipping uncomputed {}".format(path))
            return None
        log.info("Loading Gleam simulation from {} ..".format(path))
        if not h5path.exists():
            hf = None
            res_msg = "(without result)"
        else:
            hf = h5py.File(h5path, "r")
            res_msg = ""
        gd = GleamDef(path / "definition.xml")
        log.debug(f".. loaded Gleam info {gd.get_name()} {res_msg}")
        return cls(gd, hf, path)

    def __repr__(self):
        return "<Simulation {!r}>".format(self.name)

    def get_seq(self, num, kind, cumulative=True, sub="median"):
        if kind == "city":
            kind = "basin"
        p = "population/{}/{}/{}/dset".format(
            ["new", "cumulative"][cumulative], kind, sub
        )
        return self.hdf[p][:, 0, num, :]

    def has_result(self):
        return self.hdf is not None


class SimSet:
    def __init__(self):
        self.sims = []
        self.by_param = {}

    def load_sim(self, path):
        s = Simulation.load_dir(path, only_finished=True)
        if not s:
            return None
        k = (
            s.definition.get_beta(),
            s.definition.get_seasonality(),
            s.definition.get_traffic_occupancy(),
        )
        assert k not in self.by_param
        self.by_param[k] = s
        self.sims.append(s)
        return s

    def load_dir(self, path):
        path = pathlib.Path(path)
        assert path.is_dir()
        for p in path.iterdir():
            if p.suffix == ".gvh5":
                self.load_sim(p)
