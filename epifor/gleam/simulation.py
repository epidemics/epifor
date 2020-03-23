import logging
import pathlib

import h5py

from .gleamdef import GleamDef

log = logging.getLogger("simulation")


class Simulation:
    def __init__(self, gleamdef, hdf_file, dir_path=None):
        self.definition = gleamdef
        self.name = self.definition.get_name()
        assert isinstance(hdf_file, (h5py.File, None))
        self.hdf = hdf_file
        self.dir = dir_path

    @classmethod
    def load_dir(cls, path, only_finished=True):
        path = pathlib.Path(path)
        h5path = path / "results.h5"
        if only_finished and not h5path.exists():
            log.info("Skipping uncomputed {}".format(path))
            return None
        log.info("Loading Gleam simulation from {}".format(path))
        if not h5path.exists():
            hf = None
        else:
            hf = h5py.File(h5path, "r")
        gd = GleamDef(path / "definition.xml")
        log.debug(f"Loaded Gleam info {gd.get_name()}")
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
        return self.hdf


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
