#!/usr/bin/env python3

import argparse
import datetime
import json
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

from epifor import Region, Regions
from epifor.data.export import ExportDoc, ExportRegion
from epifor.gleam import SimSet

log = logging.getLogger()


def die(msg):
    log.fatal(msg)
    sys.exit(1)


def fetch_data(cfg):
    log.info(f"Fetching Foretold data ...")
    if cfg['foretold_channel'] == "SECRET":
        die("`foretold_channel` in the config file is not set to non-default value.")
    cmd = ["./fetch_foretold.py", "-c", cfg['foretold_channel']]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

    log.info(f"Fetching Foretold data ...")
    cmd = ["./fetch_csse.sh"]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)


def primary_phase(cfg, path):
    out_dir = Path(cfg["output_dir"]).expanduser()
    out_dir.mkdir(exist_ok=True)
    run_name = f"epifor-{datetime.datetime.now().astimezone().isoformat()}"

    est_xml = out_dir / (run_name + ".est.xml")
    log.info(f"Estimating population into {est_xml}")
    cmd = [
        "./estimate.py",
        path,
        "-k",
        "1000",
        "-E",
        str(cfg["compartments_mult"]["Exposed"]),
        "-D",
        cfg["start_date"].isoformat(),
        "-o",
        est_xml,   
    ]
    log.info(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

    sims_dir = Path(cfg["gleamviz_dir"]).expanduser() / "data" / "sims"
    log.info(f"Parametrizing runs into {sims_dir}")
    if not sims_dir.is_dir():
        die(f"Directory {sims_dir} does not exist!")

    Ps = []
    for m in cfg["mitigations"]:
        for s in cfg["scenarios"]:
            Ps.extend(
                [
                    "-P",
                    f"{s['param_seasonalityAlphaMin']:.3f},{s['param_occupancyRate'] / 100:.3f},{m['param_beta']:.3f}",
                ]
            )
    cmd = ["./parameterize.py", est_xml, "-D", sims_dir] + Ps
    log.info(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

    log.info(
        f"Added {len(Ps) // 2} configs into {sims_dir} with name prefix {run_name}"
    )


def secondary_phase(cfg):
    rs = Regions.load_from_yaml('data/regions.yaml')

    simset = SimSet()
    sims_dir = Path(cfg["gleamviz_dir"]).expanduser() / "data" / "sims"
    basename = None
    for d in sims_dir.iterdir():
        if d.suffix == '.gvh5':
            s = simset.load_sim(d)
            basename = s.definition.get_name().split(" ")[0]
    if not simset.sims:
        die("Did not load any results.")

    out_dir = Path(cfg["output_dir"]).expanduser()
    out_json = out_dir / f"epifor-{basename}.json"

    regions = [rs[rk] for rk in cfg['regions']]
    ed = ExportDoc(comment=f"{basename}")
    for r in regions:
        er = ed.add_region(r)
        assert er.gleam_id is not None
        assert er.kind is not None
        infected_per_1000 = {}

        initial_number = 1e10
        for s in simset.sims:
            sq = s.get_seq(er.gleam_id, er.kind)
            initial_number = max(initial_number, -np.min(sq[2, :] - sq[3, :]))
        initial_number = max(initial_number, 0.0)

        for mit in cfg["mitigations"]:
            lines = {}
            for sce in cfg["scenarios"]:
                k = (mit['param_beta'], sce['param_seasonalityAlphaMin'], sce['param_occupancyRate'])
                s = simset.by_param[k]
                sq = s.get_seq(er.gleam_id, er.kind)
                d = sq[2, :] - sq[3, :] + initial_number
                lines[sce['name']] = d
            infected_per_1000[mit['label']] = lines
        er.data["infected_per_1000"] = {
            "mitigations": infected_per_1000,
            "start": simset.sims[0].definition.get_start_date().isoformat(),
        }

    with open(out_json, "wt") as f:
        json.dump(ed.to_json(toweb=True), f)
    log.info(f"Wrote gleam chart data into {out_json}")


def main():
    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("CONFIG_YAML", help="YAML config to use.")
    ap.add_argument(
        "-P",
        "--primary",
        metavar="INPUT_XML",
        help="Run the phase *before* GLEAM with given XML as a template.",
    )
    ap.add_argument(
        "-S", "--secondary", action="store_true", help="Run phase *after* GLEAM."
    )
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages."
    )
    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    if bool(args.primary) == bool(args.secondary):
        die("Provide exactly one of -P, -S.")
    with open(args.CONFIG_YAML, "rt") as f:
        cfg = yaml.safe_load(f)

    if args.primary:
        fetch_data(cfg)
        primary_phase(cfg, args.primary)
    if args.secondary:
        secondary_phase(cfg)


if __name__ == "__main__":
    main()
