from foretold import FTData
from csse import CSSEData
from regions import Regions, _n




def main():
    rs = Regions()
    rs.load("data/regions.csv")
    ft = FTData()
    ft.load("data/foretold_data.json")
    csse = CSSEData()
    csse.load("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-{}.csv")
    pass


if __name__ == '__main__':
    main()