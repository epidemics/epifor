#!/usr/bin/env python3

import argparse
import datetime
import logging
import pathlib
import sys

import dateutil

from fttogv.csse import CSSEData
from fttogv.foretold import FTData
from fttogv.regions import Regions
from fttogv.gleamdef import GleamDef

log = logging.getLogger()


def main():
    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument(
        "INPUT_XML",
        nargs="?",
        default=None,
        help="GleamViz template to use (optional).",
    )
    ap.add_argument(
        "-o",
        "--output_xml",
        type=str,
        default=None,
        help="Override output XML path (default is 'INPUT.updated.xml').",
    )
    ap.add_argument(
        "--output_xml_limit",
        type=int,
        default=None,
        help="Only output top # of most-infected cities in the XML.",
    )
    ap.add_argument(
        "-E",
        "--add_exposed_mult",
        type=float,
        default=None,
        help="If present, add (Infectious * this) as Exposed to every city.",
    )
    ap.add_argument(
        "-O",
        "--output_est",
        type=str,
        default=None,
        help="Also write the city estimates as a csv file.",
    )
    ap.add_argument(
        "-r",
        "--regions",
        type=str,
        default="data/regions.csv",
        help="Regions csv file to use.",
    )
    ap.add_argument(
        "-f",
        "--foretold",
        type=str,
        default="foretold_data.json",
        help="Foretold JSON to use.",
    )
    ap.add_argument(
        "-C",
        "--csse_dir",
        type=str,
        default="data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/",
        help="Directory with CSSE 'time_series_19-covid-*.csv' files.",
    )

    ap.add_argument(
        "-D",
        "--by_date",
        type=str,
        default=None,
        help="Use latest Foretold and CSSE data before this date&time (no interpolation is done).",
    )
    ap.add_argument(
        "-T",
        "--show_tree",
        action="store_true",
        help="Debug: display final region tree with various values.",
    )
    ap.add_argument(
        "-d", "--debug", action="store_true", help="Display debugging mesages.",
    )
    ap.add_argument(
        "--only_params", action="store_true", help="Only change params & name.",
    )

    ap.add_argument(
        "-P",
        "--params",
        type=str, default=[],
        action="append",
        metavar=("seasonality,airtraffic,mitigation",),
        help="Override the three params, can be repeated for multiple outputs.",
    )
    ap.add_argument(
        "--name", type=str, default=None, help="Base name of def.xml.",
    )

    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    if args.INPUT_XML and args.output_xml is None:
        args.output_xml = str(pathlib.Path(args.INPUT_XML).with_suffix(".updated.xml"))
    if args.by_date is not None:
        args.by_date = dateutil.parser.parse(args.by_date).astimezone()
    if len(args.params) > 1:
        args.output_xml = None

    params_list = []
    for p in args.params:
        pfs = [float(x) for x in p.split(",")]
        assert len(pfs) == 3
        params_list.append(pfs)
    if not params_list:
        params_list = [None]

    rs = Regions()
    rs.load(args.regions)

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.fix_min_pops()

    if not args.only_params:
        # Load and apply FT
        ft = FTData()
        ft.load(args.foretold)
        ft.apply_to_regions(rs, before=args.by_date)

        # Load and apply CSSE
        csse = CSSEData()
        csse.load(args.csse_dir + "/time_series_19-covid-{}.csv")
        csse.apply_to_regions(rs)

        # Main computation: propagate estimates and fix for consistency with CSSE
        ft.propagate_down(rs)

        # Propagate estimates upwards to super-regions
        rs.fix_min_est("est_active", keep_nones=True)

        rs.check_missing_estimates("est_active")

        if args.output_est:
            rs.write_est_csv(args.output_est)

    if args.show_tree:
        rs.print_tree(kinds=("region", "continent", "world", "country"))

    if args.INPUT_XML:
        gv = GleamDef(args.INPUT_XML, base_name=args.name)
        # Update
        if not args.only_params:
            gv.clear_seeds()
            gv.add_seeds(rs, est_key="est_active", compartments={"Infectious": 1.0, "Exposed": args.add_exposed_mult}, top=args.output_xml_limit)
        # Write
        for ps in params_list:
            if ps is not None:
                gv.param_seasonality = ps[0]
                gv.param_air_traffic = ps[1]
                gv.params_mitigaton = ps[2]
            gv.save(args.output_xml)
        

if __name__ == "__main__":
    main()
