import datetime
import getpass
import json
import logging
import socket
from pathlib import Path

import dateutil
import jsonobject as jo
import numpy as np
import plotly.graph_objects as go

from ..common import IgnoredProperty, die, yaml
from ..data.export import ExportDoc
from ..gleam.simulation import Simulation
from ..regions import Region, Regions

log = logging.getLogger(__name__)


DEFAULT_LINE_STYLE = {
    "dash": "solid",
    "width": 2,
}


class SimInfo(jo.JsonObject):
    id = jo.StringProperty(required=True)
    name = jo.StringProperty(required=True)
    line_style = jo.DictProperty()
    # Mitigation group
    group = jo.StringProperty()
    # Ignored property
    sim = IgnoredProperty()


class Batch(jo.JsonObject):
    BATCH_FILE_NAME = "batch.yaml"
    DATA_FILE_NAME = "data-CHANNEL-v3.json"

    config = jo.DictProperty()
    comment = jo.StringProperty()
    created = jo.DateTimeProperty(required=True)
    sims = jo.ListProperty(SimInfo)
    name = jo.StringProperty(required=True)
    # Map {region_key: {region estimates etc}}
    region_data = jo.DictProperty()

    @classmethod
    def new(cls, config, suffix=None):
        "Custom constructor (to avoid conflicts with loading from yaml)."
        now = datetime.datetime.now().astimezone()
        name0 = f"batch-{now.isoformat()}" + (f"-{suffix}" if suffix else "")
        return cls(
            config=config,
            comment=f"{getpass.getuser()}@{socket.gethostname()}",
            created=now,
            sims=[],
            name=name0.replace(":", "-").replace(" ", "_"),
            region_data={},
        )

    def save(self):
        "Save batch metadata, autonaming the file."
        fname = self.get_batch_file_path()
        log.info(f"Writing batch metadata to {fname}")
        with open(fname, "wt") as f:
            yaml.dump(self.to_json(), f)

    @classmethod
    def load(cls, path):
        "Load batch metadata from path. Does not load the Simulations (see `load_sims`)"
        log.info(f"Reading batch metadata from {path}")
        with open(path, "rt") as f:
            d = yaml.load(f)
        return Batch(d)

    def get_batch_file_path(self):
        return self.get_out_dir() / self.BATCH_FILE_NAME

    def get_data_sims_dir(self):
        "GleamViz data dir Path, checks existence."
        p = Path(self.config["gleamviz_dir"]).expanduser() / "data" / "sims"
        assert p.exists() and p.is_dir()
        return p

    def get_out_dir(self, create=True):
        "Batch output dir Path, creates by default."
        p = Path(self.config["output_dir"]).expanduser() / self.name
        if create:
            p.mkdir(parents=True, exist_ok=True)
        assert p.exists()
        return p

    def add_simulation_info(self, sim: Simulation, name, group, color=None, style=None):
        "Add sim info after batch creation (before running simulations)"
        if style is None:
            style = dict(DEFAULT_LINE_STYLE)
        if color is not None:
            style["color"] = color
        bs = SimInfo(
            id=sim.definition.get_id(), name=name, line_style=style, group=group,
        )
        bs.sim = sim
        self.sims.append(bs)

    def load_sims(self, allow_unfinished=False, sims_dir=None):
        "Load simulation all batch simulations (optionally failing if any uncomputed)"
        if sims_dir is None:
            sims_dir = self.get_data_sims_dir()
        else:
            sims_dir = Path(sims_dir)
        for bs in self.sims:
            sdir = sims_dir / f"{bs.id}.gvh5"
            bs.sim = Simulation.load_dir(sdir, skip_unfinished=False)
            if not bs.sim.has_result() and not allow_unfinished:
                die(f"Simulation {bs.sim.name!r} in {sdir} does not have result")
        with_res = sum(int(bs.sim.has_result()) for bs in self.sims)
        log.info(
            f"Loaded {len(self.sims)} simulations, {with_res} of that have results"
        )

    def save_sim_defs_to_gleam(self, sims_dir=None):
        "Create and save the definitions of all sontained simulations into gleam sim dir."
        if sims_dir is None:
            sims_dir = self.get_data_sims_dir()
        else:
            sims_dir = Path(sims_dir)
        for bs in self.sims:
            assert bs.sim is not None
            p = sims_dir / f"{bs.sim.definition.get_id()}.gvh5"
            p.mkdir(exist_ok=False)
            bs.sim.definition.save(p / "definition.xml")
        log.info(f"Saved {len(self.sims)} simulation definitions to {sims_dir}")

    def generate_region_traces(self, region: Region):
        "Generate {group: [plotly_traces]} for a Region."

        groups = set(bs.group for bs in self.sims)

        min_number = 0.0
        for bs in self.sims:
            if bs.sim.has_result():
                sq = bs.sim.get_seq(region.gleam_id, region.kind)
                min_number = max(min_number, -np.min(sq[2, :] - sq[3, :]))

        # TODO: add initial estimates from and into region_data
        # TODO: The following would require exact populations
        # sim_number = self.region_data[region.key]["FT_Infected"]
        # print(min_number, sim_number)
        # initial_number = max(min_number, sim_number, 0.0)

        initial_number = max(min_number, 0.0)

        groups_traces = {}
        for gname in groups:
            traces = []
            for bs in self.sims:
                if bs.group == gname and bs.sim.has_result():
                    start = bs.sim.definition.get_start_date().isoformat()
                    sq = bs.sim.get_seq(region.gleam_id, region.kind)
                    # NOTE: mult by 1000 to go to *_per_1000
                    y = ((sq[2, :] - sq[3, :] + initial_number) * 1000).tolist()
                    x = [start]  # For compression, will be filled by JS
                    traces.append(
                        go.Scatter(
                            name=bs.name,
                            line=bs.line_style,
                            hoverlabel=dict(namelength=-1),
                            x=x,
                            y=y,
                        ).to_plotly_json()
                    )

            groups_traces[gname] = traces
        return groups_traces

    def write_country_plots(self, regions: Regions):
        """
        High-level function that writes a Plotly traces as a JSON file for each
        country into the batch directory.
        """

        out_dir = self.get_out_dir()
        out_json = out_dir / self.DATA_FILE_NAME
        ed = ExportDoc(comment=f"{self.name}")

        for rkey in self.config["regions"]:
            r = regions[rkey]
            er = ed.add_region(r)

            # Plots
            if (er.gleam_id is None) or (er.kind is None):
                die(f"Missing gleam_id or kind for {r!r}")
            gt = self.generate_region_traces(r)
            rel_url = f"{self.name}/lines-traces-{rkey.replace(' ', '-')}.json"
            with open(out_dir.parent / rel_url, "wt") as f:
                json.dump(gt, f)
            er.data["infected_per_1000"] = {
                "traces_url": rel_url,
            }

            # Stats
            ests = {
                k: self.region_data.get(rkey, {}).get(k)
                for k in [
                    "JH_Deaths",
                    "JH_Confirmed",
                    "JH_Recovered",
                    "JH_Infected",
                    "FT_Infected",
                ]
            }
            # TODO: add more days?
            # BUG: The current date may be different from start_date!
            er.data["estimates"] = {
                "days": {self.config["start_date"].isoformat(): ests}
            }

        log.info(f"Wrote {len(self.config['regions'])} single-region gleam trace files")
        with open(out_json, "wt") as f:
            json.dump(ed.to_json(toweb=True), f)
        log.info(f"Wrote gleam chart data into {out_json}")

    def store_region_estimates(self, regions: Regions, est_key, reg_data_key):
        """
        Transfer values from `Region.est[est_key]` to `self.region_data[reg_key][reg_data_key]`
        for regions selected in the config.
        """
        for rk in self.config["regions"]:
            r = regions[rk]
            self.region_data.setdefault(rk, dict())
            self.region_data[rk][reg_data_key] = float(r.est.get(est_key))
