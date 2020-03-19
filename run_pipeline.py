#!/usr/bin/env python3

import argparse
import datetime
import logging
import sys
from pathlib import Path
import subprocess

import yaml

log = logging.getLogger()


def primary_phase(cfg, path):
    out_dir = Path(cfg["output_dir"]).expanduser()
    out_dir.mkdir(exist_ok=True)
    run_name = f"epifor-{datetime.datetime.now().astimezone().isoformat()}"

    log.info(f"Fetching Foretold data ...")
    cmd = ["./fetch_foretold.py", "-c", cfg['foretold_channel']]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

    log.info(f"Fetching Foretold data ...")
    cmd = ["./fetch_csse.sh"]
    log.debug(f"Running {cmd!r}")
    subprocess.run(cmd, check=True)

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
    assert sims_dir.is_dir()
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
    pass


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
        logging.fatal("Provide exactly one of -P, -S.")
        sys.exit(1)
    with open(args.CONFIG_YAML, "rt") as f:
        cfg = yaml.safe_load(f)

    if args.primary:
        primary_phase(cfg, args.primary)
    if args.secondary:
        secondary_phase(cfg)


if __name__ == "__main__":
    main()
