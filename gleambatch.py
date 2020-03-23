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
from epifor.gleam import SimSet, Simulation
from epifor.data.batch import Batch

log = logging.getLogger()


def die(msg):
    log.fatal(msg)
    sys.exit(1)


def fetch_data(cfg):
    "Fetch foretold and CSSE data (runs external scripts)"

    log.info(f"Fetching Foretold data ...")
    if cfg["foretold_channel"] == "SECRET":
        die("`foretold_channel` in the config file is not set to non-default value.")
    cmd = [
        "./fetch_foretold.py",
        "-c",
        cfg["foretold_channel"],
        "-o",
        cfg["foretold_file"],
    ]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

    log.info(f"Fetching Foretold data ...")
    cmd = ["./fetch_csse.sh"]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)


def estimate(batch, rs: Regions):
    """
    Create estimates and write them to `est` of all the regions.

    Returns an updated GleamDef object.
    """

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.fix_min_pops()

    # Load and apply FT
    ft = FTData()
    ft.load(batch.config["foretold_file"])
    ft_before = datetime.datetime.combine(
        batch.start_date, datetime.time(23, 59, 59)
    ).astimezone()
    ft.apply_to_regions(rs, before=ft_before)

    # Load and apply CSSE
    csse = CSSEData()
    csse.load(args.csse_dir + "/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

    # Main computation: propagate estimates and fix for consistency with CSSE
    ft.propagate_down(rs)

    # Propagate estimates upwards to super-regions
    rs.fix_min_est(
        "est_active", keep_nones=True, minimum_from="csse_active", minimum_mult=3.0
    )  ## TODO: param for mult

    rs.check_missing_estimates("est_active")


def estimates_to_gleamdef(batch, rs: Regions, input_xml_path):
    gv = GleamDef(input_xml_path)
    gv.set_start_date(batch.start_date)
    gv.clear_seeds()
    for comp, coef in batch.config["compartments_mult"].items():
        gv.add_seeds(
            rs, est_key="est_active", compartments={comp: coef}, top=args.keep_cities
        )

    return gv


def parameterize(batch, gv):
    for mit in batch.config["mitigations"]:
        for sce in batch.config["scenarios"]:
            gv2 = gv.copy()
            gv2.set_seasonality(sce["param_seasonalityAlphaMin"])
            gv2.set_air_traffic(sce["param_occupancyRate"])
            gv2.set_beta(mit["param_beta"])
            gv2id = "{}.574".format(random.randint(1700000000000, 1800000000000))
            gv2.set_id(gv2id)
            gv2.set_name(gv2.full_name(batch.name))
            sim = Simulation(gv2, None)
            batch.add_simulation_info(
                sim,
                name=sce["name"],
                group=mit["label"],
                color=sce.get("color"),
                style=sce.get("style"),
            )


def generate(args):
    "Run the 'generate' subcommand"

    with open(args.CONFIG_YAML, "rt") as f:
        config = yaml.safe_load(f)
    batch = Batch.new(config, suffix=args.comment.replace(" ", "-"))
    rs = Regions.load_from_yaml(batch.config["regions_file"])

    fetch_data(batch.config)

    estimate(batch, args)

    gv = estimates_to_gleamdef(batch, rs, args.INPUT_XML)

    parameterize(batch, gv)

    batch.save_sim_defs_to_gleam()


def process(args):
    "Run the 'process' subcommand"

    batch = Batch.load(args.BATCH_YAML)
    rs = Regions.load_from_yaml(batch.config["regions_file"])
    batch.load_sims(only_finished=not args.allow_missing)
    batch.write_country_plots(rs)


def create_parser():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages."
    )
    sp = ap.add_subparsers(title="subcommands")

    genp = sp.add_parser(
        "generate", aliases=["gen"], help="Create a new batch, generate GLEAM configs"
    )
    genp.add_argument("CONFIG_YAML", help="YAML config to use.")
    genp.add_argument("GLEAM_XML", help="Use given XML as GLEAM def template.")
    genp.add_argument("-c", "--comment", default="", help="Optional name comment.")

    procp = sp.add_parser(
        "process",
        aliases=["proc"],
        help="Process finished simulations from a batch, generate graphs.",
    )
    procp.add_argument("BATCH_YAML", help="Batch config to use.")
    ap.add_argument(
        "-M",
        "--allow_missing",
        action="store_true",
        help="Allow missing simulation results.",
    )

    return ap


def main():
    logging.basicConfig(level=logging.INFO)
    args = create_parser().parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    args.func(args)


if __name__ == "__main__":
    main()
