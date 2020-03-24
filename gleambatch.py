#!/usr/bin/env python3

import argparse
import datetime
import logging
import random
import subprocess
import sys
from pathlib import Path

from epifor import Regions
from epifor.common import die, yaml
from epifor.data.batch import Batch
from epifor.data.csse import CSSEData
from epifor.data.foretold import FTData
from epifor.gleam import GleamDef, Simulation

log = logging.getLogger("gleambatch")


def update_data(args):
    "Fetch/update foretold and CSSE data (runs external scripts)"

    with open(args.CONFIG_YAML, "rt") as f:
        config = yaml.load(f)
    Path(config["output_dir"]).expanduser().mkdir(exist_ok=True, parents=True)

    if config["use_foretold"]:
        log.info(f"Fetching Foretold data ...")
        if config["foretold_channel"] == "SECRET":
            die(
                "`foretold_channel` in the config file is not set to non-default value."
            )
        cmd = [
            "./fetch_foretold.py",
            "-c",
            config["foretold_channel"],
            "-o",
            config["foretold_file"],
        ]
        log.debug(f"Running {cmd!r}")
        subprocess.run(cmd, check=True)
    else:
        log.info(f"Skipping Foretold update")

    log.info(f"Fetching/updating CSSE John Hopkins data from github ...")
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

    # Load and apply CSSE
    csse = CSSEData()
    csse.load(batch.config["CSSE_dir"] + "/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

    if batch.config["use_foretold"]:
        log.info("Loading and applying Foretold data")
        # Load and apply FT
        ft = FTData()
        ft.load(batch.config["foretold_file"])
        ft_before = datetime.datetime.combine(
            batch.config["start_date"], datetime.time(23, 59, 59)
        ).astimezone()
        ft.apply_to_regions(rs, before=ft_before)

    # TODO: This is asking for a good refactor of the redistribution code ...
    override = batch.config.get("region_active_estimates")
    if override is not None:
        log.info(f"Overriding 'ft_mean' for {len(override)} regions ...")
        for key, est in override.items():
            rs[key].est["ft_mean"] = est

    # Main computation: propagate estimates and fix for consistency with CSSE
    FTData.propagate_down(rs)

    # Propagate estimates upwards to super-regions
    rs.fix_min_est(
        "est_active", keep_nones=True, minimum_from="csse_active", minimum_mult=2.0
    )  ## TODO: param for mult

    rs.check_missing_estimates("est_active")

    # Store the initial estimates in batch data
    rs.fix_min_est("est_active")
    batch.store_region_estimates(rs, "est_active", "FT_Infected")
    # Finally, propagate csse upwards and also store
    for loc_key, rem_key in [
        ("csse_deaths", "JH_Deaths"),
        ("csse_confirmed", "JH_Confirmed"),
        ("csse_recovered", "JH_Recovered"),
        ("csse_active", "JH_Infected"),
    ]:
        # Fix one-city provinces
        for r in rs.regions:
            if (
                r.parent is not None
                and len(r.parent.sub) == 1
                and r.est.get(loc_key) is None
            ):
                r.est[loc_key] = r.parent.est.get(loc_key)
        # Propagate up
        rs.fix_min_est(loc_key)
        # Store in batch
        batch.store_region_estimates(rs, loc_key, rem_key)


def estimates_to_gleamdef(batch, rs: Regions, input_xml_path):
    gv = GleamDef(input_xml_path)
    gv.set_start_date(batch.config["start_date"])
    gv.clear_seeds()
    for comp, coef in batch.config["compartments_mult"].items():
        gv.add_seeds(rs, est_key="est_active", compartments={comp: coef})

    return gv


def parameterize(batch, gv):
    for mit in batch.config["mitigations"]:
        for sce in batch.config["scenarios"]:
            gv2 = gv.copy()
            gv2.set_seasonality(sce["param_seasonalityAlphaMin"])
            gv2.set_traffic_occupancy(sce["param_occupancyRate"])
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
        config = yaml.load(f)
    Path(config["output_dir"]).expanduser().mkdir(exist_ok=True, parents=True)
    batch = Batch.new(config, suffix=args.comment.replace(" ", "-"))

    log.info(f"Reading regions from {batch.config['regions_file']} ...")
    rs = Regions.load_from_yaml(batch.config["regions_file"])

    estimate(batch, rs)

    gv = estimates_to_gleamdef(batch, rs, args.GLEAM_XML)

    parameterize(batch, gv)

    batch.save_sim_defs_to_gleam()

    batch.save()

    log.info(
        f"Run '{sys.argv[0]} process {batch.get_batch_file_path()}' after"
        " running and retrieving simulations in GleamViz (and closing Gleamviz)."
    )


def process(args):
    "Run the 'process' subcommand"

    batch = Batch.load(args.BATCH_YAML)
    log.info(f"Reading regions from {batch.config['regions_file']} ...")
    rs = Regions.load_from_yaml(batch.config["regions_file"])
    batch.load_sims(allow_unfinished=args.allow_missing)
    batch.write_country_plots(rs)


def create_parser():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages."
    )
    sp = ap.add_subparsers(title="subcommands", required=True, dest="cmd")

    updatep = sp.add_parser("update", help="Fetch/update data from CSSE and Foretold")
    updatep.add_argument("CONFIG_YAML", help="YAML config to use.")
    updatep.set_defaults(func=update_data)

    genp = sp.add_parser("generate", help="Create a new batch, generate GLEAM configs")
    genp.add_argument("CONFIG_YAML", help="YAML config to use.")
    genp.add_argument("GLEAM_XML", help="Use given XML as GLEAM def template.")
    genp.add_argument("-c", "--comment", default="", help="Optional name comment.")
    genp.set_defaults(func=generate)

    procp = sp.add_parser(
        "process", help="Process finished simulations from a batch, generate graphs.",
    )
    procp.add_argument("BATCH_YAML", help="Batch config to use.")
    procp.set_defaults(func=process)
    procp.add_argument(
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
