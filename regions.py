import csv
import datetime
import logging
import sys
import xml.etree.ElementTree as ET

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
        self.extra_csv = None

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
        self.regions = []
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
        self.regions.append(reg)
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
            reg.extra_csv = list(r[8:])
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
            t += reg.extra_csv
            while len(t) > 4 and t[-1] is None:
                t.pop()
            w.writerow(t)
            for i in reg.sub:
                rec(i, ind + 4)
        rec(self['World'][0])

    def root(self):
        r = self['World']
        assert len(r) == 1
        assert r[0].parent is None
        return r[0]

    def fix_min_pops(self):
        """
        Bottom-up: set pop to be at least sum of lower pops.
        """
        def rec(reg):
            sizes = [rec(r) for r in reg.sub]
            ms = max(sum(sizes), 1000)
            reg.pop = max(reg.pop if reg.pop is not None else 0, ms)
            return reg.pop
        rec(self.root())

    def heuristic_set_pops(self, of_parent=0.5, of_sybs=0.5):
        """
        Top-down: set unset sizes to size of mean of syblings present (if >=3) or
        uniform fraction of parent (* of_parent).
        """
        def rec(reg):
            if reg.pop is None:
                pa = reg.parent
                syb_pops = [p.pop for p in pa.sub if p.pop is not None]
                if len(syb_pops) >= 3:
                    reg.pop = np.mean(syb_pops) * of_sybs
                else:
                    reg.pop = pa.pop * of_parent / len(pa.sub)
            for p in reg.sub:
                rec(p)
        rec(self.root())

    def fix_min_est(self, name, minimum=0, keep_nones=False):
        """
        Bottom-up: set est[name] to be at least sum of lower ests, also minimum.
        """
        def rec(reg):
            vs = [rec(r) for r in reg.sub]
            vs = [v for v in vs if v is not None]
            if vs or (reg.est.get(name) is not None) or (not keep_nones):
                e = reg.est.get(name, 0.0)
                mv = max(sum(vs), minimum, e if e is not None else 0.0)
            else:
                mv = None
            reg.est[name] = mv
            return mv
        rec(self.root())

    def hack_fill_downward_with(self, what, src):
        """
        Top-bottom: if est[what] is none, take it from est[src] and distribute down prop to pop
        where est[what] is missing. Hacky, only useful witout world estimate.
        """
        def rec(reg, val=None):
            if reg.est.get(what) is None:
                if val is None:
                    val = reg.est.get(src)
                if val is not None:
                    for r in reg.sub:
                        rec(r, val * r.pop / reg.pop)
                    return
            for r in reg.sub:
                rec(r, val)
    
        rec(self.root())


    def write_est_csv(self, path, kinds=('city', ), cols=('est_active', )):
        def f(x):
            return ("%.3f" % x) if x is not None else None
        def fi(x):
            return str(int(x)) if x is not None else None

        def rec(reg, w):
            if reg.kind in kinds:
                gv_id = reg.gv_id if reg.kind == 'city' else None
                t = [reg.name, reg.kind, fi(reg.pop), f(reg.lat), f(reg.lon), gv_id]
                for c in cols:
                    t.append(fi(reg.est.get(c)))
                w.writerow(t)
            for r in reg.sub:
                rec(r, w)

        with open(path, 'wt') as ff:
            w = csv.writer(ff)
            w.writerow(['name', 'kind', 'pop', 'lat', 'lon', 'gv_id'] + list(cols))
            rec(self.root(), w)

    def update_gleamviz_seeds(self, path, newpath, est='est_active', compartment="Infectious", top=None):
        ET.register_namespace('', 'http://www.gleamviz.org/xmlns/gleamviz_v4_0')
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {'gv': 'http://www.gleamviz.org/xmlns/gleamviz_v4_0'}
        sroots = root.findall('./gv:definition/gv:seeds', ns)
        assert len(sroots) == 1
        sroot = sroots[0]
        sroot.clear()
        regs = []

        def rec(reg):
            e = reg.est.get(est)
            if reg.kind == 'city' and e is not None and e > 1.0:
                regs.append((e, reg))
            for r in reg.sub:
                rec(r)
    
        rec(self.root())
        regs.sort(key=lambda er: er[0], reverse=True)
        for e, reg in regs[:top]:
            ET.SubElement(sroot, 'seed', {'number': str(int(e)), "compartment": compartment, "city": str(reg.gv_id)})

        sdef = root.findall('./gv:definition', ns)[0]
        sdef.attrib['name'] += datetime.datetime.now().strftime("_FTup_%Y-%m-%d_%H:%M:%S") 

        tree.write(newpath)


def run():

    logging.basicConfig(level=logging.DEBUG)

    r = Regions()

    with open('data/regions.csv', 'rt') as f:
        r.read_csv(f)

    r.heuristic_set_pops()
    r.fix_min_pops()

    with open('data/regions_2.csv', 'wt') as f:
        r.write_csv(f)


if __name__ == "__main__":
    run()
