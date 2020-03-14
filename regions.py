import csv
import datetime
import logging
import sys

import numpy as np
import pandas as pd

from common import _n


log = logging.getLogger()


class Region:
    def __init__(self, names, *, pop=None, gv_id=None, kind=None, lat=None, lon=None, iana=None):
        if isinstance(names, str):
            names = [names]
        names = [_n(n) for n in names]
        self.names = names

        self.pop = pop
        self.gv_id = gv_id
        self.kind = kind
        self.lat = lat
        self.lon = lon
        self.iana = iana

        # Hierarchy, root=None
        self.sub = []
        self.parent = None

        # Estimate variables dict
        self.est = {}

    def __repr__(self):
        p = " ({})".format(self.parent.name) if self.parent else ""
        return "<Region {!r}{} [{}]>".format(self.name, p, self.kind)

    @property
    def name(self):
        return self.names[0]


class Regions:

    def __init__(self):
        self.regions = {}
        self.names_index = {}

    def __getitem__(self, name):
        "Returns a tuple of regions! (Even if there is only one)"
        return tuple(self.names_index[_n(name)])

    def get(self, name, kinds=None):
        if isinstance(kinds, str):
            kinds = (kinds, )
        try:
            t = self.names_index[_n(name)]
        except KeyError:
            return ()
        if kinds is not None:
            t = (p for p in t if p.kind in kinds)
        return tuple(t)

    def __contains__(self, name):
        return _n(name) in self.names_index

    def add_reg(self, reg, parent=None):
        assert isinstance(reg, Region)
        self.regions[reg.name] = reg
        for n in reg.names:
            self.names_index.setdefault(_n(n), list()).append(reg)
        if parent:
            assert isinstance(parent, Region)
            assert reg.parent is None
            reg.parent = parent
            parent.sub.append(reg)

    def load(self, path):
        with open(path, 'rt') as f:
            self.read_csv(f)

    def read_csv(self, file):
        w = csv.reader(file)
        h = next(w)
        assert h == ['indent', 'names', 'kind', 'pop_mil', 'lat', 'lon', 'iana', 'gv_id']
        stack = [None]
        indent = 0
        last = None

        def a(x, sc=1.0):
            return float(x) * sc if (x is not None and x.strip() != "") else None

        for r in w:
            i = len(r[0])
            assert i % 4 == 0
            r = r + ([None] * (len(h) - len(r)))
            reg = Region(r[1].split('|'), kind=r[2], pop=a(r[3], 1e6), lat=a(r[4]), lon=a(r[5]), iana=r[6], gv_id=r[7])
            if i < indent:
                for _ in range((indent - i) // 4):
                    stack.pop()
            elif i > indent:
                assert i == indent + 4
                stack.append(last)
            else:  # i == ident
                pass
            #print("Add %r under %r" % (reg, stack[-1]))
            self.add_reg(reg, parent=stack[-1])
            last = reg
            indent = i

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
        rec(self['World'][0])


def run():

    logging.basicConfig(level=logging.DEBUG)

    r = Regions()

    with open('data/regions.csv', 'rt') as f:
        r.read_csv(f)

    with open('data/regions_2.csv', 'wt') as f:
        r.write_csv(f)


if __name__ == "__main__":
    run()
