import datetime
import json
import logging
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil import parser

log = logging.getLogger()


class FTPrediction:
    def __init__(self):
        pass

    @classmethod
    def from_ft_node(cls, node):
        pa = node['previousAggregate']
        if not pa:
            return None
        self = cls()
        self.date = parser.isoparse(node['labelOnDate'])
        self.pred_xs = np.array(pa['value']["floatCdf"]['xs'])
        self.pred_ys = np.array(pa['value']["floatCdf"]['ys'])
        p = np.concatenate((self.pred_ys[1:], [1.0])) - self.pred_ys
        self.mean = np.dot(p, self.pred_xs)
        self.subject = node["labelSubject"]
        self.name = re.sub('^@locations/n-', '', self.subject).capitalize()
        return self


class Region:
    def __init__(self, names, pop, ft=None, csse=None, gv_id=None, gv_type=None):
        if isinstance(names, str):
            names = [names]
        self.name = names[0].replace('-', ' ').capitalize()
        self.names = names
        self.pop = pop
        self.sub = []
        self.sup = None
        self.gv_id = gv_id
        self.gv_type = gv_type

class Regions:
    MD_CITIES = Path("data/md_cities.tsv")

    def __init__(self):
        self.regions = {}
        self.names_index = {}
        self._ar('World', 7713)

    def _norm(self, name):
        return name.lower().replace('-', ' ')

    def __getitem__(self, name):
        return self.names_index[self._norm(name)]

    def __contains__(self, name):
        return self._norm(name) in self.names_index

    def add_reg(self, reg):
        self.regions[reg.name] = reg
        for n in reg.names:
            self.names_index[self._norm(n)] = reg

    def _ar(self, names, pop_mils, parent=None, **kwargs):
        r = Region(names, pop_mils * 1e6 if pop_mils is not None else None, **kwargs)
        if parent:
            p = self[parent]
            r.parent = p
            p.sub.append(r)
        self.add_reg(r)
        return r

    def add_md_cities_regions(self):
        df = pd.read_csv(self.MD_CITIES, sep='\t')

        def a(names, parent, gv_id, gv_type):
            if isinstance(names, str):
                names = [names]
            if names[0] not in self:
                self._ar(names, None, parent, gv_id=gv_id, gv_type=gv_type)
            return self[names[0]]

        for idx, row in df.iterrows():
            cont_n = row['Continent name']
            a(cont_n, 'world', row['Continent ID'], 'continent')
            re_n = row['Region name']
            a(re_n, cont_n, row['Region ID'], 'region')
            co_n = row['Country name#']
            a(co_n, re_n, row['Country ID'], 'country')
            ci_n = row['City Name']
            a([ci_n, row['Airport code']], co_n, row['City ID'], 'city')


    def add_csse_regions(self, csse_data):
        for province, country in zip(csse_data["Province/State"], csse_data["Country/Region"]):
            pass

    def add_ft_regions(self):
        self._ar('Africa', 1, 'World')
        self._ar('Egypt', 1, 'Africa')

        self._ar('South America', 1, 'World')

        self._ar('North America', 1, 'World')
        self._ar('Mexico', 1, 'North-america')
        self._ar('Canada', 1, 'North-america')
        self._ar(['United-states-of-america', 'US', 'USA'], 1, 'North-america')
        self._ar('California', 1, 'us')
        self._ar('San-francisco', 1, 'california')
        self._ar('Washington', 1, 'us')
        self._ar('New-york', 1, 'us')

        self._ar(['European-union', 'EU'], 1, 'World')
        self._ar('Germany', 1, 'EU')
        self._ar('Spain', 1, 'EU')
        self._ar('Italy', 1, 'EU')
        self._ar('Belgium', 1, 'EU')
        self._ar('Netherlands', 1, 'EU')
        self._ar('France', 1, 'EU')

        self._ar(['United-kingdon', 'UK'], 'World')
        self._ar('Oxford', 1, 'uk')
        self._ar('London', 1, 'uk')

        self._ar('Asia', 4560, 'World')
        self._ar('China', 1427, 'Asia')
        self._ar('Wuhan', 11, 'Hubei')
        self._ar('Hubei', 58.5, 'China')
        self._ar('Hong-kong', 7.4, 'China')
        self._ar('South-korea', 'Asia')
        self._ar('Japan', 'Asia')
        self._ar('Indonesia', 'Asia')
        self._ar('India', 'Asia')
        self._ar('Singapore', 'Asia')
        self._ar('Middle-east', 1, 'Asia')
        self._ar('Dubai', 1, 'Middle-east')
        self._ar('Iran', 1, 'Middle-east')

        self._ar('Australia', 1, 'World')

        self._ar('Russia', 1, 'World')
        self._ar('Switzerland', 1, 'World')


class Data:
    FORETOLD = Path("data/foretold_data.json")
    CSSE_DIR = Path("data/CSSE-COVID-19/csse_covid_19_data/csse_covid_19_time_series")
    CSSE_CONF = CSSE_DIR / "time_series_19-covid-Confirmed.csv"
    CSSE_REC = CSSE_DIR / "time_series_19-covid-Recovered.csv"
    CSSE_DEAD = CSSE_DIR / "time_series_19-covid-Deaths.csv"

    def __init__(self, time=datetime.datetime.now()):
        self.time = time
        self.csse = self.load_csse()
        self.ft = self.load_ft()

#        self.cities = self.load_gv_cities()

    def load_ft(self):
        d = json.loads(self.FORETOLD.read_text())["data"]["measurables"]['edges']
        fts = {}
        for p in d:
            ft = FTPrediction.from_ft_node(p['node'])
            if ft is None:
                continue
            if ft.name not in fts or ft.date > fts[ft.name].date:
                fts[ft.name] = ft
        return fts

    def load_csse(self):
        dfs = []
        for f, name in [(self.CSSE_CONF, "Confirmed"), (self.CSSE_DEAD, "Deaths"), (self.CSSE_REC, "Recovered")]:
            df = pd.read_csv(f, header=0)
            dcs = list(df.columns)[4:]
            df[name] = df[dcs].max(axis=1)
            for c in dcs:
                del df[c]
            dfs.append(df)
        d = dfs.pop()
        for d2 in dfs:
            del d2['Lat']
            del d2['Long']
            d = d.merge(d2, on=["Province/State", "Country/Region"], how='outer')
        d['Infections'] = d['Confirmed'] - d['Deaths'] - d['Recovered']
        return d

def test():

    logging.basicConfig(level=logging.DEBUG)
    d = Data()
    x = [(f.name) for f in d.ft.values()]
    print(x)

    r = Regions()
    r.add_md_cities_regions()

if __name__ == "__main__":
    test()
