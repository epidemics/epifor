#!/usr/bin/python3

import argparse
import datetime
import logging
import pathlib
import sys

import dateutil

from fttogv.csse import CSSEData
from fttogv.foretold import FTData
from fttogv.regions import Regions

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
        "-d",
        "--debug",
        action="store_true",
        help="Display debugging mesages.",
    )

    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    if args.INPUT_XML and args.output_xml is None:
        args.output_xml = str(pathlib.Path(args.INPUT_XML).with_suffix(".updated.xml"))
    if args.by_date is not None:
        args.by_date = dateutil.parser.parse(args.by_date).astimezone()

    rs = Regions()
    rs.load(args.regions)

    # Load and apply FT
    ft = FTData()
    ft.load(args.foretold)
    ft.apply_to_regions(rs, before=args.by_date)

    # Load and apply CSSE
    csse = CSSEData()
    csse.load(args.csse_dir + "/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.fix_min_pops()

    # Main computation: propagate estimates and fix for consistency with CSSE
    ft.propagate_down(rs)

    # Propagate estimates upwards to super-regions
    rs.fix_min_est("est_active", keep_nones=True)

    rs.check_missing_estimates('est_active')

    if args.show_tree:
        rs.print_tree(kinds=("region", "continent", "world", "country"))

    if args.output_est:
        rs.write_est_csv(args.output_est)

    if args.INPUT_XML:
        rs.update_gleamviz_seeds(
            args.INPUT_XML,
            args.output_xml,
            est="est_active",
            compartment="Infectious",
            top=args.output_xml_limit,
        )


if __name__ == "__main__":
    main()
