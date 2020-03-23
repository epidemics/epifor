import datetime
import getpass
import json
import logging
import socket
from pathlib import Path

import jsonobject as jo
import numpy as np
import plotly.graph_objects as go
import yaml

from .data.export import ExportDoc, ExportRegion
from .gleam.gleamdef import GleamDef
from .gleam.simulation import Simulation
from .regions import Region, Regions

DEFAULT_LINE_STYLE = {
    "dash": "solid",
    "width": 2,
}

log = logging.getLogger("simulation")


class SimInfo(jo.JsonObject):
    id = jo.StringProperty(required=True)
    name = jo.StringProperty(required=True)
    line_style = jo.ObjectProperty()
    # Mitigation group
    group = jo.StringProperty()

    def __init__(self, *, sim=None, **kwrags):
        super().__init__(**kwrags)
        assert isinstance(sim, (Simulation, None))
        self.sim = sim


class Batch(jo.JsonObject):
    BATCH_FILE_NAME = "batch.yaml"

    config = jo.ObjectProperty()
    comment = jo.StringProperty()
    created = jo.DateTimeProperty(required=True)
    sims = jo.ListProperty(SimInfo)
    name = jo.StringProperty(required=True)
    # Map {region_key: {region estimates etc}}
    region_data = jo.ObjectProperty()

    @classmethod
    def new(cls, config, suffix=None):
        "Custom constructor (to avoid conflicts with loading from yaml)."
        now = datetime.datetime.now().astimezone()
        return cls(
            config=config,
            comment=f"{getpass.getuser()}@{socket.gethostname()}",
            created=now,
            sims=[],
            name=f"batch-{now.isoformat()}-{suffix}",
            region_data={},
        )

    def save(self):
        "Save batch metadata, autonaming the file."
        fname = self.get_out_dir() / self.BATCH_FILE_NAME
        log.info(f"Writing batch metadata to {fname}")
        with open(fname, "wt") as f:
            yaml.dump(self.to_json(), f)

    @classmethod
    def load(cls, path):
        "Load batch metadata from path."
        log.info(f"Reading batch metadata from {path}")
        with open(path, "rt") as f:
            cls(yaml.safe_load(f))

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

    def _add_simulation_info(self, gd: GleamDef, name, group, color=None, style=None):
        "Add sim info after batch creation (before running simulations)"
        if style is None:
            style = dict(DEFAULT_LINE_STYLE)
        if color is not None:
            style["color"] = color
        self.sims.append(
            SimInfo(id=gd.get_id(), name=name, line_style=style, group=group)
        )

    def load_sims(self, only_finished=False):
        "Load simulation all batch simulations (optionally failing if any uncomputed)"
        sims_dir = self.get_data_sims_dir()
        for bs in self.sims:
            bs.sim = Simulation.load_dir(sims_dir / f"{bs.id}.gvh5", only_finished=only_finished)

    def generate_region_traces(self, region: Region):
        "Generate {group: [plotly_traces]} for a Region."

        groups = set(bs.group for bs in self.sims)

        ## TODO: add initial estimates from and into region_data
        initial_number = 0.0
        for bs in self.sims:
            sq = bs.sim.get_seq(region.gleam_id, region.kind)
            initial_number = max(initial_number, -np.min(sq[2, :] - sq[3, :]))
        initial_number = max(initial_number, 0.0)

        groups_traces = {}
        for gname in groups:
            traces = []
            for bs in self.sims:
                if bs.group == gname and bs.sim.has_result():
                    start = bs.sim.definition.get_start_date().isoformat()
                    sq = bs.sim.get_seq(region.gleam_id, region.kind)
                    y = (sq[2, :] - sq[3, :] + initial_number) * 1000
                    x = None  # TODO, use start
                    traces.append(go.Scatter(
                        label=bs.name,
                        line=bs.line_style,
                        hoverlabel=dict(namelength=-1),
                        x=x,
                        y=y).to_plotly_json())

            groups_traces[gname] = traces
        return groups_traces

    def write_country_plots(self, regions: Regions):
        """
        High-level function that writes a Plotly traces as a JSON file for each
        country into the batch directory.
        """

        out_dir = self.get_out_dir()
        out_json = out_dir / f"data-CHANNEL-lines-v2.json"
        ed = ExportDoc(comment=f"{self.name}")

        for rkey in self.config["regions"]:
            r = regions[rkey]
            er = ed.add_region(r)
            assert er.gleam_id is not None
            assert er.kind is not None
            gt = self.generate_region_traces(r)
            rel_url =  f"{self.name}/lines-traces-{rkey.replace(' ', '-')}.json"
            with open(out_dir.parent / rel_url, 'wt') as f:
                json.dump(gt, f)
            er["infected_per_1000"] = {
                "traces_url": rel_url,
            }
        with open(out_json, "wt") as f:
            json.dump(ed.to_json(toweb=True), f)
        log.info(f"Wrote gleam chart data into {out_json}")
