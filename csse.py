### HEAVILY WIP

import logging
import re

import numpy as np
import pandas as pd

from common import SKIP, _n, UNABBREV

log = logging.getLogger()

class CSSEData:

    def __init__(self):
        self.df = None

    def load(self, pattern):
        dfs = []
        for name in ["Confirmed", "Deaths", "Recovered"]:
            df = pd.read_csv(pattern.format(name), header=0)
            dcs = list(df.columns)[4:]
            # NOTE: Some areas have 0 in last column even if nonzero before
            df[name] = df[dcs].max(axis=1)
            for c in dcs:
                del df[c]
            dfs.append(df)
        d = dfs.pop()
        for d2 in dfs:
            del d2['Lat']
            del d2['Long']
            d = d.merge(d2, on=["Province/State", "Country/Region"], how='outer')
        d['Active'] = d['Confirmed'] - d['Deaths'] - d['Recovered']
        self.df = d

    def apply_to_regions(self, regions):
        "Add estimates to the regions. Note: adds to existing numbers!"
        for _i, r in self.df.iterrows():
            province, country = _n(r['Province/State']), _n(r['Country/Region'])
            if _n(province) in SKIP or _n(country) in SKIP:
                continue
            name = country if province == 'nan' else province
            kind = None

            # Special handling of states, also US counties and cities with codes:
            if country in ['us', 'china', 'canada', 'australia'] and province != 'nan':
                m = re.search(', (..)\s*$', province)
                if m:
                    name = UNABBREV[m.groups()[0].upper()]
                else:
                    name = province
                kind = "state"

            regs = regions.get(name, kind)
            if len(regs) < 1:
                log.warning("CSSE region %r %r not found in Regions, skipping", name, (country, province))
                continue
            if len(regs) > 1:
                log.warning("CSSE region %r %r matches several Regions: %r, skipping", name, (country, province), regs)
                continue
            reg = regs[0]

            # Accumulation used in US counties/cities etc.
            def app(name, col):
                reg.est.setdefault(name, 0.0)
                reg.est[name] += r[col]
            app('csse_active', 'Active')
            app('csse_confirmed', 'Confirmed')
            app('csse_deaths', 'Deaths')
            app('csse_recovered', 'Recovered')
