### HEAVILY WIP

import logging
import re

import numpy as np
import pandas as pd
import datetime

from ..common import SKIP, UNABBREV, _n

log = logging.getLogger(__name__)

EXTERNAL_US = ["puerto rico", "virgin islands, u.s.", "guam"]

FORCE_KINDS = {
    "liberia": "country",
    "luxembourg": "country",
    "lebanon": "country",
    "kuwait": "country",
}


class CSSEData:
    def __init__(self):
        self.df = None
        self.HIST_FILE_NAME = "csse_history_data.h5"

    @staticmethod
    def convert_date(string):
        " Convert string from csv to pandas allowed format"
        try:
            return datetime.datetime.strptime(string, "%m/%d/%Y").strftime("%Y%m%d")
        except ValueError:
            return datetime.datetime.strptime(string, "%m/%d/%y").strftime("%Y%m%d")

    @staticmethod
    def nearest_date(items, pivot):
        " Find the nearest date to start_date from config "
        items = [datetime.datetime.strptime(x, "%Y%m%d") for x in items]
        pivot = datetime.datetime.strptime(pivot, "%Y%m%d")
        return min(items, key=lambda x: abs(x - pivot)).strftime("%Y%m%d")

    def load(self, pattern, by_date):
        dfs = []
        shortest_list_dcs = None
        by_date = by_date.strftime("%Y%m%d")
        for name in ["confirmed", "deaths", "recovered"]:
            df = pd.read_csv(pattern.format(name), header=0)

            dcs = list(df.columns)[4:]
            # Rename columns to format pandas would accept
            df = df.rename(columns={x: self.convert_date(x) for x in dcs})
            dcs = [self.convert_date(x) for x in dcs]
            # Look up shortest list as some dates are missing sometimes in CSSE
            if shortest_list_dcs is None or len(dcs) < len(shortest_list_dcs):
                shortest_list_dcs = dcs
            # Take the nearest date to config start_date
            nearest_date = self.nearest_date(dcs, by_date)
            df[name] = df[nearest_date]
            # NOTE: Some areas have 0 in last column even if nonzero before
            df = df.rename(columns={x: "{}_{}".format(name, x) for x in dcs})
            dfs.append(df)

        d = dfs.pop()
        for d2 in dfs:
            del d2["Lat"]
            del d2["Long"]
            d = d.merge(d2, on=["Province/State", "Country/Region"], how="outer")
        d["active"] = d["confirmed"] - d["deaths"] - d["recovered"]
        columns_list = ['region']
        for date in shortest_list_dcs:
            d[f"active_{date}"] = d[f"confirmed_{date}"] - d[f"deaths_{date}"] - d[f"recovered_{date}"]
            columns_list.extend([f"{prefix}_{date}" for prefix in ["active", "confirmed", "deaths", "recovered"]])

        self.hist_df = pd.DataFrame(columns=columns_list)
        self.df = d

    def apply_to_regions(self, regions):
        "Add estimates to the regions. Note: adds to existing numbers!"
        d = self.hist_df
        for _i, r in self.df.iterrows():
            province, country = _n(r["Province/State"]), _n(r["Country/Region"])
            if _n(province) in SKIP or _n(country) in SKIP:
                continue
            name = country if province == "nan" else province
            kind = None

            # Special handling of states, also US counties and cities with codes:
            if country in ["us", "china", "canada", "australia"] and province != "nan":
                m = re.search(", (..)\s*$", province)
                if m:
                    name = UNABBREV[m.groups()[0].upper()]
                else:
                    name = province
                if _n(name) not in EXTERNAL_US:
                    kind = "state"

                if _n(name) == "georgia":
                    name = "georgia, us"

            if name in FORCE_KINDS:
                kind = FORCE_KINDS[name]

            regs = regions.find_names(name, kind)
            if len(regs) < 1:
                log.warning(
                    f"CSSE region {name!r} [{kind}, from {country}/{province}] not found in Regions, skipping"
                )
                continue
            if len(regs) > 1:
                log.warning(
                    "CSSE region %r %r matches several Regions: %r, skipping",
                    name,
                    (country, province),
                    regs,
                )
                continue
            reg = regs[0]

            # Accumulation used in US counties/cities etc.
            def app(name, col):
                reg.est.setdefault(name, 0.0)
                reg.est[name] += r[col]

            app("csse_active", "active")
            app("csse_confirmed", "confirmed")
            app("csse_deaths", "deaths")
            app("csse_recovered", "recovered")

            # Solving hongkong city, should be made more robust ?
            if _n(province) == 'hong kong':
                country = 'hong kong'

            # Accumulation of history data for US etc.
            if country in d['region'].values:
                row = d.loc[d["region"] == country].to_dict(orient='records')[0]
            else:
                # Create new row with null values
                row = {x: 0 for x in list(d.columns) if x not in ['region']}
                row['region'] = country

            # Accumulate values
            for name in row.keys():
                if name not in ['region']:
                    row[name] += r[name]

            # Apply accumulated values to dataframe
            if country in d['region'].values:
                idx = d.index[d['region'] == country].tolist()
                # Dataframe aligned wih values
                d.loc[idx] = row.values()
            else:
                # Assign new row into dataframe
                d = d.append(row, ignore_index=True)

            d = d.fillna(0)

        self.hist_df = d.set_index('region')

    def convert_region_names(self, regions):
        " Convert names of region us => united states "
        df = self.hist_df

        for i, r in df.iterrows():
            if i == 'hong kong':
                reg = regions.find_names(i, 'city')
            else:
                reg = regions.find_names(i)
            assert len(reg) != 0
            df = df.rename(index={i: reg[0].key})

        self.hist_df = df

    def save_hist_data(self, output_path):
        " Save the historical data to hdf to output dir "
        self.hist_df.to_hdf(f"{output_path}/{self.HIST_FILE_NAME}",
                            "df",
                            mode="w",
                            format="table",
                            data_columns=True)
