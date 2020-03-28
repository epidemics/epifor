import datetime
import getpass
import json
import logging
import re
import socket
from copy import copy, deepcopy
from pathlib import Path

import dateutil
import jsonobject as jo
import numpy as np
import plotly.graph_objects as go
from scipy.stats import lognorm, norm

from ..common import IgnoredProperty, die, mix_html_colors, yaml
from ..data.export import ExportDoc, ExportRegion
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

    def generate_simgroup_traces(self, region, sims, initial_number):
        def trace_for_seqs(bs1, bs2=None, *, q=1.0, name=None, vis=1.0):
            if bs2 is None:
                bs2 = bs1
            sq1 = bs1.sim.get_seq(region.gleam_id, region.kind)
            y1 = sq1[2, :] - sq1[3, :] + initial_number
            sq2 = bs2.sim.get_seq(region.gleam_id, region.kind)
            y2 = sq2[2, :] - sq2[3, :] + initial_number
            # NOTE: mult by 1000 to go to *_per_1000
            y = ((q * y1 + (1.0 - q) * y2) * 1000).tolist()
            x = [start]  # For compression, will be filled by JS
            style = copy(bs1.line_style)
            style.color = mix_html_colors(
                (bs1.line_style["color"], q), (bs2.line_style["color"], (1 - q)),
            )
            kws = {"opacity": vis}
            if name is None:
                kws["showlegend"] = False
                kws["hoverinfo"] = "skip"
            return go.Scatter(
                name=name, line=style, hoverlabel=dict(namelength=-1), x=x, y=y, **kws,
            ).to_plotly_json()

        if not sims:
            return []
        start = sims[0].sim.definition.get_start_date().isoformat()
        traces = []

        # group by air traffic
        at_sims = {}
        for bs in sims:
            at_sims.setdefault(
                bs.sim.definition.get_traffic_occupancy(), list()
            ).append(bs)

        # Add 2 interpolations
        for simseq in at_sims.values():
            simseq.sort(key=lambda bs: bs.sim.definition.get_seasonality())
            for bs1, bs2 in zip(simseq[:-1], simseq[1:]):
                for q in [0.33, 0.66]:
                    traces.append(trace_for_seqs(bs1, bs2, q=q, vis=0.35))

        # Add the full trace
        for bs in sims:
            traces.append(trace_for_seqs(bs, name=bs.name))

    def generate_simgroup_stats(self, region, sims, initial_number):
        tot_infected = []
        max_active_infected = []
        for bs in sims:
            sq = bs.sim.get_seq(region.gleam_id, region.kind)
            tot_infected.append(sq[2, -1] + initial_number)
            max_active_infected.append(np.max(sq[2, :] - sq[3, :] + initial_number))
        stats = {}
        for data, name in [
            (tot_infected, "TotalInfected"),
            (max_active_infected, "MaxActiveInfected"),
        ]:
            m, v = norm.fit(data)
            v = max(v, 1e-2)
            dist = norm(m, v)
            stats[f"{name}_per1000_mean"] = dist.mean() * 1000
            stats[f"{name}_per1000_q05"] = max(dist.ppf(0.05), 0.0) * 1000
            stats[f"{name}_per1000_q95"] = min(dist.ppf(0.95), 1.0) * 1000
        return stats

    def generate_region_traces_and_stats(self, region: Region):
        """
        Generate {group: [plotly_traces]} and {group: {stats}} for a Region.
        """

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
        groups_stats = {}
        for gname in groups:
            sims = [bs for bs in self.sims if bs.group == gname and bs.sim.has_result()]
            groups_traces[gname] = self.generate_simgroup_traces(
                region, sims, initial_number
            )
            groups_stats[gname] = self.generate_simgroup_stats(
                region, sims, initial_number
            )
        return groups_traces, groups_stats

    def export_region_traces(self, er: ExportRegion, out_dir: Path):
        # Plots and sim summaries
        if (er.gleam_id is None) or (er.kind is None):
            die(f"Missing gleam_id or kind for {er.region!r}")
        gt, gs = self.generate_region_traces_and_stats(er.region)
        rel_url = f"{self.name}/lines-traces-{er.region.key.replace(' ', '-')}.json"
        with open(out_dir.parent / rel_url, "wt") as f:
            json.dump(gt, f)
        er.data["infected_per_1000"] = {
            "traces_url": rel_url,
        }
        er.data["mitigation_stats"] = gs

    def export_region_estimates(self, er: ExportRegion):
        # Stats
        ests = {
            k: self.region_data.get(er.region.key, {}).get(k)
            for k in [
                "JH_Deaths",
                "JH_Confirmed",
                "JH_Recovered",
                "JH_Infected",
                "FT_Infected",
            ]
        }
        # TODO: add more days?
        # BUG: The last date may be different from start_date!
        er.data["estimates"] = {"days": {self.config["start_date"].isoformat(): ests}}

    def write_export_data(self, regions: Regions):
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
            self.export_region_estimates(er)
            self.export_region_traces(er, out_dir=out_dir)

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
