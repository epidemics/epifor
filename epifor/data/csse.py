### HEAVILY WIP

import logging
import re
import datetime

import numpy as np
import pandas as pd

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

    @staticmethod
    def convert_date(string):
        try:
            return datetime.datetime.strptime(string, "%m/%d/%Y").strftime("%Y%m%d")
        except ValueError:
            return datetime.datetime.strptime(string, "%m/%d/%y").strftime("%Y%m%d")

    @staticmethod
    def nearest_date(items, pivot):
        items = [datetime.datetime.strptime(x, "%Y%m%d") for x in items]
        pivot = datetime.datetime.strptime(pivot, "%Y%m%d")
        return min(items, key=lambda x: abs(x - pivot)).strftime("%Y%m%d")

    def load(self, pattern, by_date, output_dir):
        dfs = []
        shortest_list_dcs = None
        by_date = by_date.strftime("%Y%m%d")
        for name in ["confirmed", "deaths", "recovered"]:
            df = pd.read_csv(pattern.format(name), header=0)
            dcs = list(df.columns)[4:]
            # Rename columns to US format
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

        for date in shortest_list_dcs:
            d[f"active_{date}"] = d[f"confirmed_{date}"] - d[f"deaths_{date}"] - d[f"recovered_{date}"]

        # d_to_store = d.rename(columns={'Province/State': 'State', 'Country/Region': 'Region'})
        # del d_to_store["Lat"]
        # del d_to_store["Long"]
        # d_to_store['Region'] = d_to_store['Region'].apply(lambda x: x.lower())
        # d_to_store.to_hdf(f'{output_dir}/csse_history_data.h5', 'df', mode='w', format='table', data_columns=True)

        self.df = d

    def apply_to_regions(self, regions):
        "Add estimates to the regions. Note: adds to existing numbers!"
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
            # reg.est_hist = {}

            # Accumulation used in US counties/cities etc.
            def app(name, col):
                reg.est.setdefault(name, 0.0)
                reg.est[name] += r[col]
                # reg.est_hist[name] = r.filter(regex='.*{}_.*'.format(col), axis=0)

            app("csse_active", "active")
            app("csse_confirmed", "confirmed")
            app("csse_deaths", "deaths")
            app("csse_recovered", "recovered")
