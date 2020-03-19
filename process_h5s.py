#!/usr/bin/env python3

import argparse
import csv
import logging
import pathlib
import json
import datetime

import numpy as np
import pandas as pd

from epifor.gleam.simulation import SimSet, Simulation
from epifor.regions import Regions
from epifor.data.export import ExportDoc, ExportRegion

log = logging.getLogger("process_data_hdf")


def make_export_doc(regions, simset):
    mitig_sims = {}
    for s in simset.sims:
        mitig_sims.setdefault(s.definition.param_mitigation, list()).append(s)
    ed = ExportDoc(comment=f"{simset.sims[0].name}")

    NAMES = ["High", "Medium", "Low"]
    for r in regions:
        er = ed.add_region(r)
        infected_per_1000 = {}
        pos_mits = sorted(x for x in mitig_sims.keys() if x > 0)

        ## Heuristic to find the intial rate of infected
        minimum = 1e10
        for mit in sorted(mitig_sims.keys()):
            for s in mitig_sims[mit]:
                sq = s.get_seq(er.gleam_id, er.kind)
                minimum = min(minimum, np.min(sq[2, :] - sq[3, :]))

        for mit in sorted(mitig_sims.keys()):
            mit_name = "None" if mit == 0.0 else NAMES[pos_mits.index(mit)]
            lines = {}
            for s in mitig_sims[mit]:
                lname = f"COVID seasonality {s.definition.param_seasonality:.2f}, Air traffic {s.definition.param_air_traffic:.2f}"
                assert er.gleam_id is not None
                assert er.kind is not None
                sq = s.get_seq(er.gleam_id, er.kind)
                d = sq[2, :] - sq[3, :] - minimum
                lines[lname] = [round(float(x * 1000), 4) for x in d]
            infected_per_1000[mit_name] = lines
        er.data["infected_per_1000"] = {
            "mitigations": infected_per_1000,
            "start": simset.sims[0].definition.get_start_date().isoformat(),
        }
    return ed


def main():
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        "SIM_DIRS",
        nargs="+",
        default=None,
        help="List of Gleam dirs with HDF5 files to read.",
    )
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages.",
    )
    ap.add_argument(
        "-o",
        "--output_json",
        default="data-staging-gleam.json",
        help="Write JSON output to this file.",
    )
    ap.add_argument(
        "-r",
        "--regions",
        type=str,
        default="data/regions.yaml",
        help="Regions YAML file to use.",
    )
    ap.add_argument(
        "-R", "--select_regions", required=True, help="Region keys separated with '|'.",
    )

    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    rs = Regions.load_from_yaml(args.regions)

    simset = SimSet()
    for d in args.SIM_DIRS:
        simset.load_sim(d)

    regs = [rs[key] for key in args.select_regions.split("|")]
    ed = make_export_doc(regs, simset)
    with open(args.output_json, "wt") as f:
        json.dump(ed.to_json(toweb=True), f)


if __name__ == "__main__":
    main()
