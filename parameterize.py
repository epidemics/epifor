#!/usr/bin/env python3

import itertools
import argparse
import datetime
import json
import logging
import pathlib
import sys

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
        "PREFIX", help="Prefix for output defs, can be 'PATH/PREFIX'.",
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
            
            Example: `-P [1.0,0.85,0.7],[0.2,0.7],[0.0,0.3,0.4,0.5]`
            """,
    )
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages.",
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

    for ps in params_list:
        gv.param_seasonality = ps[0]
        gv.param_air_traffic = ps[1]
        gv.params_mitigaton = ps[2]
        gv.save(prefix=args.PREFIX)


if __name__ == "__main__":
    main()
