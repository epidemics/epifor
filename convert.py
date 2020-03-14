import logging


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
    ft.apply_to_regions(rs)

    # Load and apply CSSE
    csse = CSSEData()
    csse.load("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

    # Fix any missing / inconsistent pops
    rs.heuristic_set_pops()
    rs.heuristic_set_pops()

    # Propagate estimates and fix for consistency
    ft.propagate_down(rs)

    rs.hack_fill_downward_with('est_active', 'csse_active')
    rs.fix_min_est('est_active', keep_nones=True)

    for r in rs.regions:
        if r.est.get('est_active') is None and r.kind == 'city':
            log.warning("{!r} has no 'est_active' estmate".format(r))

    rs.write_est_csv("data/est_active.csv")

if __name__ == '__main__':
    main()
