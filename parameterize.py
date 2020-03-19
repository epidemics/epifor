#!/usr/bin/env python3

import itertools
import argparse
import datetime
import json
import logging
import pathlib
import sys
import random

import dateutil

from epifor.gleam import GleamDef

log = logging.getLogger()


def main():
    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        "INPUT_XML", help="Gleam definition template to use.",
    )
    ap.add_argument(
        "PREFIX", help="Prefix for output defs, can be 'PATH/PREFIX'. With -D, it should be the GLEAMViz/data/sims/ dir",
    )
    ap.add_argument(
        "-P",
        "--params",
        required=True,
        type=str,
        default=[],
        action="append",
        metavar=("seasonality,airtraffic,mitigation",),
        help="""
            Override the three params, can be repeated for multiple outputs.
            This is parsed as a JSON array (adding "[]").
            If any of the params is an array of values, a cartesian product will be created.
            
            Example: `-P [0.85,0.7,0.5],[0.2,0.7],[0.0,0.3,0.4,0.5]`
            """,
    )
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages.",
    )
    ap.add_argument(
        "-D", "--gleam_dirs", action="store_true", help="Create gleam dirs and set random IDs. PREFIX should be the GLEAMViz/data/sims/ dir.",
    )

    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    params_list = []
    for ptext in args.params:
        p0 = "[" + ptext + "]"
        try:
            p1 = json.loads(p0)
        except json.decoder.JSONDecodeError:
            log.error("Can't decode value {!r} as JSON".format(p0))
            raise
        assert len(p1) == 3
        p2 = [p if isinstance(p, list) else [p] for p in p1]
        params_list.extend(itertools.product(*p2))
    log.info(
        "Creating definitions for {} parameters: {!r}".format(
            len(params_list), params_list
        )
    )

    gv = GleamDef(args.INPUT_XML)

    if args.gleam_dirs:
        args.PREFIX = pathlib.Path(args.PREFIX)
        assert args.PREFIX.is_dir()

    for ps in params_list:
        gv2 = gv.copy()
        gv2.set_seasonality(ps[0])
        gv2.set_air_traffic(ps[1])
        #gv2.param_mitigation = ps[2]
        gv2.set_beta(ps[2])
        gvp = pathlib.Path(args.INPUT_XML)
        gv2.set_name(gv2.full_name(gvp.with_suffix('').with_suffix('').stem))
        if args.gleam_dirs:
            gvid = "{}.574".format(random.randint(1700000000000, 1800000000000))
            gv2.set_id(gvid)
            p = args.PREFIX / "{}.gvh5".format(gvid)
            p.mkdir()
            gv2.save(p / "definition.xml")
        else:
            gv2.save(prefix=args.PREFIX)


if __name__ == "__main__":
    main()
