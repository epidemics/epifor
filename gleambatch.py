#!/usr/bin/env python3

import argparse
import datetime
import logging
import random
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import epifor
from epifor import Regions
from epifor.common import die, log_level, run_command, yaml
from epifor.data.batch import Batch
from epifor.data.csse import CSSEData
from epifor.data.fetch_foretold import fetch_foretold
from epifor.data.foretold import FTData
from epifor.gleam import GleamDef, Simulation

log = logging.getLogger("gleambatch")


def update_data(args):
    "The `update` subcommand (update foretold and CSSE data)"

    with open(args.CONFIG_YAML, "rt") as f:
        config = yaml.load(f)
    Path(config["output_dir"]).expanduser().mkdir(exist_ok=True, parents=True)

    if config["use_foretold"]:
        log.info(f"Fetching Foretold data into {config['foretold_file']} ...")
        if config["foretold_channel"] == "SECRET":
            die(
                "`foretold_channel` in the config file is not set to non-default value."
            )
        data = fetch_foretold(config["foretold_channel"])
        with open(config["foretold_file"], "wb") as outfile:
            outfile.write(data)

    else:
        log.info(f"Skipping Foretold update")

    log.info(f"Fetching/updating CSSE John Hopkins data from github ...")
    run_command(["./fetch_csse.sh"])


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


def estimates_to_gleamdef(batch, rs: Regions, input_xml_path, top_seeds=None):
    gv = GleamDef(input_xml_path)
    gv.set_start_date(batch.config["start_date"])
    gv.clear_seeds()
    for comp, coef in batch.config["compartments_mult"].items():
        gv.add_seeds(rs, est_key="est_active", compartments={comp: coef}, top=top_seeds)

    return gv


def parameterize(batch, gv):
    last_ts = 0
    for mit in batch.config["mitigations"]:
        for sce in batch.config["scenarios"]:
            gv2 = gv.copy()
            gv2.set_seasonality(sce["param_seasonalityAlphaMin"])
            gv2.set_traffic_occupancy(sce["param_occupancyRate"])
            gv2.set_beta(mit["param_beta"])
            # NOTE: No idea where `.574` comes from, but all my
            # Gleamviz-imported defnitions have it
            # NOTE: Gleamviz seems to have timestamp-based IDs (in milisec);
            # take care not to reuse them here
            last_ts = max(last_ts + 1, int(time.time() * 1000))
            gv2id = f"{last_ts}.574"
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


SIM_DEF_DIR = "simulation-defs"


def generate(args):
    "The 'generate' subcommand"

    with open(args.CONFIG_YAML, "rt") as f:
        config = yaml.load(f)
    out_dir = Path(config["output_dir"]).expanduser().mkdir(exist_ok=True, parents=True)
    batch = Batch.new(config, suffix=args.comment.replace(" ", "-"))

    log.info(f"Reading regions from {batch.config['regions_file']} ...")
    rs = Regions.load_from_yaml(batch.config["regions_file"])

    estimate(batch, rs)

    gv = estimates_to_gleamdef(batch, rs, args.GLEAM_XML, top_seeds=args.top_seeds)

    parameterize(batch, gv)

    # Save to Gleam sims directory
    batch.save_sim_defs_to_gleam()

    # Save to batch directory
    sims_dir = batch.get_out_dir() / SIM_DEF_DIR
    sims_dir.mkdir()
    with log_level(epifor.gleam.gleamdef.log, logging.WARNING):
        batch.save_sim_defs_to_gleam(sims_dir)

    batch.save()

    log.info(
        f"Run '{sys.argv[0]} process {batch.get_batch_file_path()}' after"
        " running and retrieving simulations in GleamViz (and closing Gleamviz)."
    )


def upload_data(args):
    "The 'upload' subcommand"

    CMD = [
        "gsutil",
        "-m",
        "-h",
        "Cache-Control:public, max-age=10",
        "cp",
        "-a",
        "public-read",
    ]

    batch = Batch.load(args.BATCH_YAML)
    gs = batch.config["gs_prefix"].rstrip("/")
    gs_url = batch.config["gs_url_prefix"].rstrip("/")
    out = batch.get_out_dir()
    out_file = out / batch.DATA_FILE_NAME
    if not out_file.exists():
        die(f"File {out_file} not found - did you run `process`?")

    log.info(f"Uploading data folder {out} to {gs}/{batch.name}")
    run_command(CMD + ["-R", out, gs])

    datafile_channel = batch.DATA_FILE_NAME.replace("CHANNEL", args.channel)
    gs_data_tgt = f"{gs}/{datafile_channel}"
    log.info(f"Uploading main data file as {gs_data_tgt}")
    run_command(CMD + [out_file, gs_data_tgt])
    log.info(f"File URL: {gs_url}/{datafile_channel}")

    log.info(f"Zipping and uploading sim defs ..")
    zip_file = out / "sims.zip"
    run_command(["zip", zip_file, out / SIM_DEF_DIR])
    run_command(CMD + [zip_file, f"{gs}/simulation-defs-{args.channel}.zip"])
    log.info(f"File URL: {gs_url}/simulation-defs-{args.channel}.zip")
    if args.channel != "main":
        log.info(
            f"Custom web URL: http://epidemicforecasting.org/?channel={args.channel}"
        )


def process(args):
    "The 'process' subcommand"

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
    genp.add_argument(
        "--top-seeds",
        default=1800,
        type=int,
        help="Limit the number of seed cities (Gleam seems to fail if too many, ~2000?).",
    )
    genp.set_defaults(func=generate)

    procp = sp.add_parser(
        "process", help="Process finished simulations from a batch, generate graphs.",
    )
    procp.add_argument("BATCH_YAML", help="Batch config to use.")
    procp.set_defaults(func=process)
    procp.add_argument(
        "-M",
        "--allow-missing",
        action="store_true",
        help="Allow missing simulation results.",
    )

    uplp = sp.add_parser("upload", help="Upload data to the configured GCS bucket")
    uplp.add_argument("BATCH_YAML", help="Batch config to use.")
    uplp.add_argument(
        "-C",
        "--channel",
        default="staging",
        help="Channel to upload to ('main' for main site).",
    )
    uplp.set_defaults(func=upload_data)

    return ap


def main():
    logging.basicConfig(level=logging.INFO)
    args = create_parser().parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    args.func(args)


if __name__ == "__main__":
    main()
