import logging
import pathlib
import sys
import datetime

from csse import CSSEData
from foretold import FTData
from regions import Regions

log = logging.getLogger()



def main():
    rs = Regions()
    rs.load("data/regions.csv")

    # Load and apply FT
    ft = FTData()
    ft.load("data/foretold_data.json")
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

    rs.hack_fill_downward_with('est_active', 'csse_active')
    rs.fix_min_est('est_active', keep_nones=True)

    for r in rs.regions:
        if r.est.get('est_active') is None and r.kind == 'city':
            log.warning("{!r} has no 'est_active' estmate".format(r))

    rs.print_tree(kinds=('region', 'continent', 'world', 'country'))
    rs.write_est_csv("data/est_active.csv")

    if len(sys.argv) >= 2:
        fp = sys.argv[1]
        p2 = pathlib.Path(fp).with_suffix('.updated.xml')
        rs.update_gleamviz_seeds(fp, p2, est='est_active', compartment="Infectious", top=None)


if __name__ == '__main__':
    print("Usage: %s INPUT_XML" % sys.argv[0])
    main()
