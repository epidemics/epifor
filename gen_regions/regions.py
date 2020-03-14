import csv
import datetime
import json
import logging
import math
import os
import pickle
import re
import subprocess
import sys
from math import pi
from pathlib import Path

import numpy as np
import pandas as pd
import unidecode

from data import *
from foretold import *

log = logging.getLogger()


def _n(s):
    return unidecode.unidecode(str(s)).replace('-', ' ').lower()


def _ncol(df, *cols):
    for col in cols:
        df[col] = df[col].map(_n)

def geo_dist(lat1, lat2, dlong):
    R = 6373.0
    lat1, lat2, dlong = lat1 * pi / 180, lat2 * pi / 180, dlong * pi / 180
    a = math.sin((lat1 - lat2) / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlong / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * R



class Region:
    def __init__(self, names,  pop=None, abbrev=None, gv_id=None, kind=None, lat=None, lon=None, iana=None):
        if isinstance(names, str):
            names = [names]
        names = [_n(n) for n in names]
        self.name = names[0]
        self.names = names
        self.pop = pop
        self.gv_id = gv_id
        self.kind = kind
        self.inf_csse = None
        self.inf_ft = None
        self.lat = lat
        self.lon = lon
        self.iana = iana
        self.abbrev = abbrev
        self.admin = None

        self.sub = []
        self.parent = None

class Regions:

    def __init__(self):
        self.regions = {}
        self.names_index = {}
        self._ar('World', 7713)

    def __getitem__(self, name):
        return self.names_index[_n(name)]

    def __contains__(self, name):
        return _n(name) in self.names_index

    def add_reg(self, reg):
        self.regions[reg.name] = reg
        for n in reg.names:
            self.names_index[_n(n)] = reg

    def _ar(self, names, pop_mils=None, parent=None, **kwargs):
        r = Region(names, pop_mils * 1e6 if pop_mils is not None else None, **kwargs)
        if parent:
            assert isinstance(parent, Region)
            r.parent = parent
            parent.sub.append(r)
        self.add_reg(r)
        return r

    def alias(self, name, *aliases):
        r = self[name]
        for n in aliases:
            r.names.append(_n(n))
            self.names_index[_n(n)] = r

    def add_md_cities_regions(self):
        df = pd.read_csv(MD_CITIES, sep='\t')
        _ncol(df, "Continent name", "Region name", "Country name", "City Name")

        def a(names, parent, gv_id, t, **kw):
            if isinstance(names, str):
                names = [names]
            if names[0] not in self:
                self._ar(names, None, self[parent], kind=t, gv_id=gv_id, **kw)
            else:
                if t == 'city':
                    print("Duplicate in MD:", names[0])
            return self[names[0]]

        for _idx, row in df.iterrows():
            cont_n = row['Continent name']
            a(cont_n, 'world', row['Continent ID'], 'continent')
            re_n = row['Region name']
            a(re_n, cont_n, row['Region ID'], 'region')
            co_n = row['Country name']
            a(co_n, re_n, row['Country ID'], 'country')
            ci_n = row['City Name']
            a(ci_n, co_n, row['City ID'], 'city', iana=row['Airport code'])

        for x in ALIASES:
            self.alias(*x)

    def add_states(self):
        for c, ss in STATES.items():
            for s, a in ss:
                self._ar(s, parent=self[c], abbrev=a, kind='state')

    def apply_airport_coords_db(self):
        "Dataase invomplete, do not use"
        t = AIRPORTDB.read_text()
        d = {}
        for l in t.splitlines():
            r = l.strip().split(':')
            if r[1] != 'N/A' and r[-1] != '0.000':
                d[r[1]] = (float(r[-2]), float(r[-1]))
        for r in self.regions.values():
            if r.iana in d:
                r.lat, r.lon = d[r.iana]

    def apply_airport_coords(self):
        df = pd.read_csv(AIRPORTS)
        d = {}
        for _i, row in df.iterrows():
            d[row[4]] = (float(row[6]), float(row[7]))
        for r in self.regions.values():
            if r.iana in d:
                r.lat, r.lon = d[r.iana]

    def sizes_to_cities(self):
        ## WIP
        df = pd.read_csv(CITY_SIZES)
        _ncol(df, 'City', 'Country or Area')
        df = df[df['Value'].notna()]
        df = df.groupby(['City']).agg({'Value': max})
        for reg in self.regions.values():
            if reg.kind == 'city':
                try:
                    r = df.loc[_n(reg.name)]
                    reg.pop = float(r['Value'].lower())
                except KeyError:
                    pass

    def sizes_and_admin_to_cities2(self):
        def s(x):
            return re.sub('\s*\([a-zA-Z ]*\)\s*$', '', _n(x.replace('’', '')))
        df = pd.read_csv(CITY_SIZES_W, header=0)
        df = df[df['population'].notna()]
        #df = df[df['population'] > 10000]
        df['city_ascii'] = df['city_ascii'].map(s)
        _ncol(df, 'country', 'admin_name', 'city_ascii')
        df = df.sort_values('population', ascending=False).groupby('city_ascii', as_index=False).first()
        df = df.set_index('city_ascii')        
#        df = df.groupby(df.index).agg({'population': max})
        for reg in self.regions.values():
            if reg.kind == 'city':
                try:
                    r = df.loc[_n(reg.name)]
                    if isinstance(r['population'], float):
                        if r['country'] in reg.parent.names:
                            reg.pop = float(r['population'])
                            reg.admin = r['admin_name']
                        else:
                            print("Mismatch in country:", reg.name, r['country'], reg.parent.names)
                    else:
                        print('Duplicate cities in s2c2', reg.name, r['population'])
                except KeyError:
                    #print('City not found in s2c2', reg.name)
                    pass

    def add_csse_regions(self, csse_data):
        ## WIP
        for _i, row in csse_data.iterrows():
            province, country = row['Province/State'], row['Country/Region']
            if _n(province) in DROP or _n(country) in DROP:
                continue
            if str(province) == 'nan':
                r = self[country]
            else:
                lat, lon = row['Lat'], row['Long']
                if country in ['US', 'Canada', 'China', 'Australia']:
                    m = re.search(', (..)\s*$', province)
                    if m:
                        r = self[UNABBREV[m.groups()[0]]]
                    else:
                        r = self[province]
                else:
                    print("Extra Countre+Province:", country, province)
                #     if province in self:
                #         r = self[province]
                #     else:
                #         r = self._ar(province, None, self[country], lat=lat, lon=lon, kind='state')
                # if country not in ['US', 'Canada', 'Australia', 'China']:
                #     print(country, province)

            if r.inf_csse is None:
                r.inf_csse = 0.0
            r.inf_csse += row['Infections']

    def restructure(self):
        for c in ['US', 'Canada', 'Australia', 'China']:
            self.rehang_to_states('city', self[c])

    def rehang_to_states(self, kind, parent):
        rehang = []
        states = {}
        for r in parent.sub:
            if r.kind == kind:
                rehang.append(r)
            else:
                states[_n(r.name)] = r
        for r in rehang:
            if r.admin is not None: # and r.name not in SKIP_REHANG:
                self.rehang(r, states[_n(r.admin)])

    def rehang(self, what, under):
        assert isinstance(what, Region)
        assert isinstance(under, Region)
        p = what.parent
        p.sub.remove(what)
        what.parent = under
        under.sub.append(what)

    def add_ft_regions(self, ftps):
        self._ar(['European union', 'EU'], 512, self['Europe'])
        self['Middle east'].pop = 371e6
        for s in EU_STATES:
            self.rehang(self[s], self['EU'])
        self.rehang(self['Egypt'], self['Middle east'])

        for ft in ftps.values():
            if _n(ft.name) in DROP:
                continue
            try:
                r = self[ft.name]
            except KeyError:
                print("FT Error", ft.name)
            if r.inf_ft is None:
                r.inf_ft = 0.0
            r.inf_ft += ft.mean

    def write_csv(self, file=sys.stdout):
        w = csv.writer(file)
        w.writerow(['indent', 'names', 'kind', 'pop_mil', 'lat', 'lon', 'iana', 'gv_id'])
        def f(x, mult=1.0):
            return ("%.3f" % (x * mult)) if x is not None else None
        def rec(reg, ind=0):
            id = reg.gv_id if reg.kind == 'city' else None
            t = [' ' * ind, "|".join(reg.names), reg.kind, f(reg.pop, 1e-6), f(reg.lat), f(reg.lon), reg.iana, id]
            while len(t) > 4 and t[-1] is None:
                t.pop()
            w.writerow(t)
            for i in reg.sub:
                rec(i, ind + 4)
        rec(self['World'])


    def tree(self):
        def rec(reg, ind=0):
            print(f"{' ' * ind} {reg.name} [{reg.kind}]")
            for i in reg.sub:
                rec(i, ind + 2)
        rec(self['World'])


class Data:

    def __init__(self, time=datetime.datetime.now()):
        self.time = time
        self.csse = self.load_csse()
        self.ft = self.load_ft()

#        self.cities = self.load_gv_cities()

    def load_ft(self):
        d = json.loads(FORETOLD.read_text())["data"]["measurables"]['edges']
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
        for f, name in [(CSSE_CONF, "Confirmed"), (CSSE_DEAD, "Deaths"), (CSSE_REC, "Recovered")]:
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

    r = Regions()
    r.add_md_cities_regions()
    r.apply_airport_coords()
    r.add_states()
    r.add_csse_regions(d.load_csse())
    r.add_ft_regions(d.ft)
    r.sizes_and_admin_to_cities2()
    r.restructure()

    #r.tree()
    with open('data/regions.csv', 'wt') as f:
        r.write_csv(f)

    

if __name__ == "__main__":
    test()
