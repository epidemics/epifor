import logging
import pprint

from csse import CSSEData, UNABBREV
from foretold import FTData
from regions import Regions, _n

log = logging.getLogger()



def main():
    rs = Regions()
    rs.load("data/regions.csv")
    ft = FTData()
    ft.load("data/foretold_data.json")
    ft.apply_to_regions(rs)
    csse = CSSEData()
    csse.load("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-{}.csv")
    csse.apply_to_regions(rs)

if __name__ == '__main__':
    main()
