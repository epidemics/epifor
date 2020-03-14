### MILDLY WIP

import json
import logging
import re

import numpy as np
from dateutil import parser

from regions import SKIP, _n

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
        self.subject = node["labelSubject"]
        self.name = _n(re.sub('^@locations/n-', '', self.subject).replace('-', ' '))

        # TODO: verify/test
        # TODO: now this treats it like a discrete distribution with xs vals,
        #       this is fine for ~1000 samples from FT, but may need fixing otherwise
        p = np.concatenate((self.pred_ys[1:], [1.0])) - self.pred_ys
        self.mean = np.dot(p, self.pred_xs)
        self.var = np.dot(p, np.abs(self.pred_xs - self.mean) ** 2)
        return self


class FTData:
    def __init__(self):
        # subject -> [FTPrediction asc by date]
        self.subjects = {}
        # day -> [FTPrediction]
        self.days = {}
        # subject -> FTPrediction
        self.latest = {}
        # All predictions, unsorted
        self.predictions = []
        # entire loaded json file
        self._loaded = None

    def load(self, path):
        with open(path, 'rt') as f:
            self._loaded = json.load(f)
        d = self._loaded["data"]["measurables"]['edges']
        for p in d:
            ft = FTPrediction.from_ft_node(p['node'])
            if ft is not None:
                self.predictions.append(ft)
        self._sort()

    def _sort(self):
        self.subjects, self.days, self.latest = {}, {}, {}
        self.predictions.sort(key=lambda p: p.date)
        for p in self.predictions:
            self.subjects.setdefault(p.subject, []).append(p)
            self.days.setdefault(p.date, []).append(p)
            self.latest[p.subject] = p

    def apply_to_regions(self, regions):
        for p in self.latest.values():
            if _n(p.name) in SKIP:
                continue
            try:
                regs = regions[p.name]
            except KeyError:
                log.warning("Foretold region %r not found in Regions, skipping", p.name)
                continue
            if len(regs) > 1:
                log.warning("Foretold region %r matches several Regions: %r, skipping", p.name, regs)
                continue
            reg = regs[0]
            reg.est['ft_mean'] = p.mean
            reg.est['ft_var'] = p.var

