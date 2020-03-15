#!/usr/bin/python3

import logging
import pathlib
import sys
import datetime

from fttogv.csse import CSSEData
from fttogv.foretold import FTData
from fttogv.regions import Regions

log = logging.getLogger()



def main():
    rs = Regions()
    rs.load("data/regions.csv")

    # Load and apply FT
    ft = FTData()
    ft.load("foretold_data.json")
    ft.apply_to_regions(rs, before=datetime.datetime(2020, 3, 17).astimezone())

    # Load and apply CSSE
    csse = CSSEData()
    csse.load("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.fix_min_pops()

    # Propagate estimates and fix for consistency
    ft.propagate_down(rs)

    # rs.hack_fill_downward_with('est_active', 'csse_active')
    rs.fix_min_est('est_active', keep_nones=True)

    miss_c = []
    for r in rs.regions:
        if r.est.get('est_active') is None and r.kind == 'city':
            miss_c.append(r.name)
    log.info("{} cities have no 'est_active' estmate: {}".format(len(miss_c), miss_c))

    #rs.print_tree(kinds=('region', 'continent', 'world', 'country'))
    rs.write_est_csv("estimated_active.csv")

    if len(sys.argv) >= 2:
        fp = sys.argv[1]
        p2 = pathlib.Path(fp).with_suffix('.updated.xml')
        rs.update_gleamviz_seeds(fp, p2, est='est_active', compartment="Infectious", top=None)


if __name__ == '__main__':
    print("Usage: %s INPUT_XML" % sys.argv[0])
    main()
