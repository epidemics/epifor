#!/usr/bin/env python3

import argparse
import logging
import pathlib

import dateutil

from epifor import Regions
from epifor.data import CSSEData, FTData
from epifor.gleam import GleamDef

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
        help="Override output XML path (default is 'INPUT.est.xml').",
    )
    ap.add_argument(
        "-k",
        "--keep_cities",
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
        default="data/regions.yaml",
        help="Regions YAML file to use.",
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
        "--output-case", type=str, default=None, help="A path to output case JSON data",
    )

    ap.add_argument(
        "--config",
        type=str,
        default=None,
        help="Config to use for filtering case data. Make sense only with `--output-case",
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

    args = ap.parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)
    if args.INPUT_XML and args.output_xml is None:
        args.output_xml = str(pathlib.Path(args.INPUT_XML).with_suffix(".est.xml"))
    if args.by_date is not None:
        args.by_date = dateutil.parser.parse(args.by_date)

    rs = Regions.load_from_yaml(args.regions)

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.fix_min_pops()

    # Load and apply FT
    ft = FTData()
    ft.load(args.foretold)
    ft.apply_to_regions(rs, before=args.by_date.astimezone())

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

    if args.output_est:
        rs.write_est_csv(args.output_est, kinds=None)

    from pathlib import Path
    import pandas as pd
    import yaml

    REGION_COLUMN_NAME = "_iso_code"
    WANTED_COLUMNS = [
        "Recovered",
        "Confirmed",
        "Deaths",
        "Active",
        "name",
        "est_active",
    ]

    def check_countries(df: pd.DataFrame, regions: set) -> None:
        unq_regions = set(df.name.unique())
        diff = regions - unq_regions
        if diff:
            raise RuntimeError(
                f"Some wanted regions are not present in the case data: {diff}."
            )

    from pycountry import countries
    ISO_FALLBACK_DICT = {"Korea, South": "KOR", "Cruise Ship": "INVALID"}
    CSSE_DICT = {"US": "USA",
                 "Martinique": "MTQ",
                 "Peru": "PER",
                 "Jordan": "JOR",
                 "Ireland": "IRL",
                 "Mexico": "MEX",
                 "Georgia": "GEO",
                 "Oman": "OMN",
                 "Spain": "ESP",
                 "India": "IND",
                 "Luxembourg": "LUX",
                 "China": "CHN",
                 "Iran": "IRN",
                 "Taiwan": "TWN"}
    def _get_iso(_x: str):
        x = _x.strip('*')  # i.e. "Taiwan*"
        try:
            search = countries.search_fuzzy(x)
        except LookupError:
            if x in ISO_FALLBACK_DICT:
                return ISO_FALLBACK_DICT[x]
            else:
                logging.error("Did my best but couldn't guess value for %s. Returning None", x)
                return None

        if len(search) > 1:
            if x in CSSE_DICT:
                return CSSE_DICT[x]
            else:
                logging.warning("Not knowing ISO code for %s. Guessing: %s (from %s)", x, search[0].alpha_3, search)
        return search[0].alpha_3

    def filter_countries(df: pd.DataFrame, config_path: str) -> pd.DataFrame:
        regions = set(yaml.load(open(config_path), Loader=yaml.Loader)["regions"])
        isos = {_get_iso(x) for x in regions}
        print(f"Countries wanted: {isos}")
        selected = df.loc[df[REGION_COLUMN_NAME].isin(isos)]
        breakpoint()
        check_countries(selected, isos)
        return selected

    def write_json_case(df: pd.DataFrame) -> pd.DataFrame:
        return df


    def add_iso3166_code(df: pd.DataFrame, source_column: str):
        isos = {x: _get_iso(x) for x in df[source_column].unique()}
        df[REGION_COLUMN_NAME] = df[source_column].map(isos)
        return df

    def write_case_data(
        _tmp_estimated: str, csse_df: pd.DataFrame, config_path: str
    ) -> None:
        tmp_estimated = Path(_tmp_estimated)
        rs.write_est_csv(tmp_estimated, kinds=None)
        css_iso = add_iso3166_code(csse_df, "Country/Region")
        estimates_iso = (
            pd.read_csv(tmp_estimated)
            .pipe(lambda x: x.loc[x["kind"].isin({"country", "state"})])
            .pipe(add_iso3166_code, "name")
        )
        res = (
            pd.merge(estimates_iso, css_iso, on="_iso_code", indicator="merge_key")
            .filter(items=WANTED_COLUMNS + [REGION_COLUMN_NAME])
            .pipe(filter_countries, config_path)
            .pipe(write_json_case)
        )
        breakpoint()
        # res.to_csv("case_data.csv")

    if args.output_case:
        write_case_data("/tmp/_estimated.csv", csse.df, args.config)

    if args.show_tree:
        rs.print_tree(kinds=("region", "continent", "world", "country"))

    breakpoint()

    # Load and update
    if args.INPUT_XML:
        gv = GleamDef(args.INPUT_XML)
        gv.set_start_date(args.by_date)
        gv.clear_seeds()
        gv.add_seeds(
            rs,
            est_key="est_active",
            compartments={"Infectious": 1.0, "Exposed": args.add_exposed_mult},
            top=args.keep_cities,
        )
        gv.save(args.output_xml)


if __name__ == "__main__":
    main()
