import csv
import datetime
import logging
import sys

from .common import _n, _fs

log = logging.getLogger("fttogv.regions")


class Region:
    def __init__(self, names, *, key=None, population=None, gleam_id=None, kind=None, lat=None, lon=None, iana=None):
        if isinstance(names, str):
            names = [names]
        if key is None:
            key = _n(names[0])

        self.name = names[0]
        self.names = names
        self.key = key

        self.population = population
        self.gleam_id = gleam_id
        self.kind = kind
        self.lat = lat
        self.lon = lon
        self.iana = iana

        # Hierarchy, root.parent=None
        self.sub = []
        self.parent = None

        # Estimate variables dict
        self.est = {}

    def __repr__(self):
        return f"<Region {self.name!r} [{self.key}, {self.kind}] ({self.parent})>"

    def __str__(self):
        return self.name

    @property
    def pop(self):
        return self.population

    def to_json_rec(self, nones=False):
        s = [s.to_json_rec(nones=nones) for s in self.sub] if self.sub else None
        return _fs(self, "key", "names", "kind", "population", "lat", "lon",
             "gleam_id", "iana", _n=nones,
            subregions=s)


class Regions:

    def __init__(self):
        # key: Region
        self.key_index = {}
        # _n(name): [Region]
        self.all_names_index = {}
        self.root = None

    def __getitem__(self, key):
        "Returns a single Region by key"
        return self.key_index[key]

    @property
    def regions(self):
        return self.key_index.values()

    def find_names(self, name, kinds=None):
        if isinstance(kinds, str):
            kinds = (kinds, )
        try:
            t = self.all_names_index[_n(name)]
        except KeyError:
            return ()
        if kinds is not None:
            t = (p for p in t if p.kind in kinds)
        return tuple(t)

    def __contains__(self, key):
        if isinstance(key, Region):
            key = key.key
        return key.key in self.key_index

    def add_region(self, reg, parent):
        assert isinstance(reg, Region)
        assert reg.key
        if reg.key in self.key_index:
            raise Exception(f"Region {reg!r}'s key already indexed as {self[reg.key]!r}")
        self.key_index[reg.key] = reg
        for n in reg.names:
            self.all_names_index.setdefault(_n(n), list()).append(reg)
        if parent is not None:
            assert isinstance(parent, Region)
            assert reg.parent is None
            reg.parent = parent
            parent.sub.append(reg)
        else:
            assert self.root is None
            self.root = reg

    def load_csv(self, path):
        with open(path, 'rt') as f:
            self.read_csv(f)

    def read_csv(self, file):
        w = csv.reader(file)
        h = next(w)
        assert h == ['indent', 'names', 'kind', 'pop_mil', 'lat', 'lon', 'iana', 'gv_id']
        stack = [None]
        indent = 0
        last = None

        def a(x, sc=1.0, t=float):
            return t(float(x) * sc) if (x is not None and x.strip() != "") else None
        def b(x):
            return int(x) if x is not None else None

        for r in w:
            i = len(r[0])
            assert i % 4 == 0
            r = r + ([None] * (len(h) - len(r)))
            reg = Region(r[1].split('|'), kind=r[2], population=a(r[3], 1e6, int), lat=a(r[4]), lon=a(r[5]), iana=r[6], gleam_id=b(r[7]))
            if i < indent:
                for _ in range((indent - i) // 4):
                    stack.pop()
            elif i > indent:
                assert i == indent + 4
                stack.append(last)
            else:  # i == ident
                pass
            #print("Add %r under %r" % (reg, stack[-1]))
            self.add_region(reg, parent=stack[-1])
            last = reg
            indent = i

    def write_csv(self, file=sys.stdout):
        w = csv.writer(file)
        w.writerow(['indent', 'names', 'kind', 'pop_mil', 'lat', 'lon', 'iana', 'gv_id'])
        def f(x, mult=1.0):
            return ("%.3f" % (x * mult)) if x is not None else None
        def rec(reg, ind=0):
            id = reg.gv_id if reg.kind == 'city' else None
            t = [' ' * ind, "|".join(reg.names), reg.kind, f(reg.population, 1e-6), f(reg.lat), f(reg.lon), reg.iana, id]
            t += reg.extra_csv
            while len(t) > 4 and t[-1] is None:
                t.pop()
            w.writerow(t)
            for i in reg.sub:
                rec(i, ind + 4)
        rec(self.root)

    def print_tree(self, file=sys.stdout, kinds=('region', 'continent', 'world')):
        def rec(reg, ind=0, parentpop=None):
            if parentpop:
                pp = " ({:.2f}%)".format(100.0 * reg.pop / parentpop)
            else:
                pp = ""
            if reg.kind in kinds:
                file.write("{}{} [{}] pop={}M{}\n".format(" " * ind, reg.name, reg.kind, reg.pop / 1e6, pp))
            for i in reg.sub:
                rec(i, ind + 4, reg.pop)
        rec(self.root)

    def fix_min_pops(self):
        """
        Bottom-up: set pop to be at least sum of lower pops, for consistency.
        """
        def rec(reg):
            sizes = [rec(r) for r in reg.sub]
            ms = max(sum(sizes), 1000)
            reg.population = max(reg.population if reg.population is not None else 0, ms)
            return reg.pop
        rec(self.root)

    def heuristic_set_pops(self, of_parent=1.0):
        """
        Top-down: set unset children pops to min of:
        * uniform fraction of remaining population from parent
        * smallest known size (the unknown cities tend to be the smallest ones)
        """
        def rec(reg):
            assert reg.pop is not None
            popless = [r for r in reg.sub if r.pop is None]
            if popless:
                syb_pops = [r.pop for r in reg.sub if r.pop is not None]
                pop_est = (reg.pop - sum(syb_pops)) / len(popless)
                pop_est = max(min([pop_est] + syb_pops), 0)
            for r in popless:
                r.population = int(pop_est)
            subpops = sum(r.pop for r in reg.sub)                
            if subpops > reg.pop * 1.3:
                log.warning("Pop inconsistency at {!r}: {} vs {} total in subs".format(reg, reg.pop, subpops))
#            assert sum(r.pop for r in reg.sub) <= reg.pop * 1.1
            for r in reg.sub:
                rec(r)

        rec(self.root)

    def fix_min_est(self, name, minimum=0, keep_nones=False):
        """
        Bottom-up: set est[name] to be at least sum of lower ests, and at least minimum.
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
        rec(self.root)

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
    
        rec(self.root)


    def write_est_csv(self, path, kinds=('city', ), cols=('est_active', )):
        def f(x):
            return ("%.3f" % x) if x is not None else None
        def fi(x):
            return str(int(x)) if x is not None else None

        def rec(reg, w):
            if (kinds is None) or (reg.kind in kinds):
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
            rec(self.root, w)
        log.info("Written region estimates CSV to {!r}".format(path))

    def check_missing_estimates(self, name):
        miss_c = []
        for r in self.regions:
            if r.est.get(name) is None and r.kind == "city":
                miss_c.append(r)
        log.info("Cities missing {} estmate: {} (total pop {:.3f} milion)".format(name, len(miss_c), sum(r.pop for r in miss_c) / 1e6))
        log.debug("-- full list of cities with no {} estimate: {}".format(name, [r.name for r in miss_c]))


def run():

    logging.basicConfig(level=logging.DEBUG)

    r = Regions()

    with open('data/regions.csv', 'rt') as f:
        r.read_csv(f)

    r.heuristic_set_pops()
    r.fix_min_pops()

    if 0:
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.width = 80
        yaml.indent = 4
        yaml.compact_seq_map = True
        yaml.compact_seq_seq = True
        yaml.compact(True, True)
        yaml.preserve_quotes = True
    else:
        import yaml

    with open('data/regions_2.yaml', 'wt') as f:
        yaml.dump(r.root.to_json_rec(nones=False), f, default_flow_style=True, sort_keys=False, indent=4, width=80)


if __name__ == "__main__":
    run()
