import logging
import numpy as np

from .common import _fs, _n, yaml

log = logging.getLogger(__name__)


class Region:
    def __init__(
        self,
        names,
        *,
        key=None,
        population=None,
        gleam_id=None,
        kind=None,
        lat=None,
        lon=None,
        iana=None,
        iso_alpha_3=None,
        max_percentage_of_infected_to_fill_icu_beds=None,
    ):
        if isinstance(names, str):
            names = [names]
        if key is None:
            key = _n(names[0])

        self.names = names
        self.key = key

        self.population = population
        self.gleam_id = gleam_id
        self.kind = kind
        self.lat = lat
        self.lon = lon
        self.iana = iana
        self.iso_alpha_3 = iso_alpha_3
        self.max_percentage_of_infected_to_fill_icu_beds = None

        # Hierarchy, root.parent=None
        self.sub = []
        self.parent = None

        # Estimate variables dict
        self.est = {}

    def __eq__(self, other):
        if not isinstance(other, Region):
            return False
        for k in ["key", "kind"]:  ## TODO
            if getattr(self, k) != getattr(other, k):
                return False
        skey = lambda r: r.key
        for r1, r2 in zip(sorted(self.sub, key=skey), sorted(other.sub, key=skey)):
            if r1 != r2:
                return False
        return True

    def __repr__(self):
        return f"<Region {self.name!r} [{self.key}, {self.kind}] ({self.parent})>"

    def __str__(self):
        return self.name

    @property
    def pop(self):
        return self.population

    @property
    def name(self):
        return self.names[0]

    def to_json_rec(self, nones=False):
        s = [s.to_json_rec(nones=nones) for s in self.sub] if self.sub else None
        return _fs(
            self,
            "key",
            "names",
            "kind",
            "population",
            "lat",
            "lon",
            "gleam_id",
            "iana",
            "iso_alpha_3",
            "max_percentage_of_infected_to_fill_icu_beds",
            _n=nones,
            subregions=s,
        )

    @classmethod
    def _from_yaml(cls, regions, y, parent=None):
        subs = y.pop("subregions", list())
        names = y.pop("names")
        r = cls(names, **y)
        regions.add_region(r, parent)
        for y2 in subs:
            Region._from_yaml(regions, y2, parent=r)
        return r


class Regions:
    def __init__(self):
        # key: Region
        self.key_index = {}
        # _n(name): [Region]
        self.all_names_index = {}
        self.root = None

    @classmethod
    def load_from_yaml(cls, path):
        s = cls()
        with open(path, "rt") as f:
            s.read_yaml(f)
        return s

    def __getitem__(self, key):
        "Returns a single Region by key"
        return self.key_index[key]

    def __contains__(self, key):
        if isinstance(key, Region):
            key = key.key
        return key in self.key_index

    @property
    def regions(self):
        return self.key_index.values()

    def find_names(self, name, kinds=None):
        if isinstance(kinds, str):
            kinds = (kinds,)
        try:
            t = self.all_names_index[_n(name)]
        except KeyError:
            return ()
        if kinds is not None:
            t = (p for p in t if p.kind in kinds)
        return tuple(t)

    def add_region(self, reg, parent):
        assert isinstance(reg, Region)
        assert reg.key
        if reg.key in self.key_index:
            raise Exception(
                f"Region {reg!r}'s key already indexed as {self[reg.key]!r}"
            )
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

    def write_yaml(self, stream):
        yaml.dump(self.root.to_json_rec(nones=False), stream)

    def read_yaml(self, stream):
        y = yaml.load(stream)
        l0 = len(self.key_index)
        assert isinstance(y, dict)
        assert y.get("key") == "earth"
        Region._from_yaml(self, y, parent=None)
        for r in self.regions:
            if r.kind == "country" and (r.population is None or r.population == 0):
                log.warning(f"Country {r!r} is missing population")
        log.info(f"Read {len(self.key_index) - l0} regions")

    def fix_min_pops(self):
        """
        Bottom-up: set pop to be at least sum of lower pops, for consistency.
        """

        def rec(reg):
            sizes = [rec(r) for r in reg.sub]
            ms = max(sum(sizes), 1000)
            reg.population = max(
                reg.population if reg.population is not None else 0, ms
            )
            return reg.pop

        rec(self.root)

    def check_missing_estimates(self, name):
        """Find cities that do not have any value for given estimate."""
        miss_c = []
        for r in self.regions:
            if r.est.get(name) is None and r.kind == "city":
                miss_c.append(r)
        log.info(
            "Cities missing {} estmate: {} (total pop {:.3f} milion)".format(
                name, len(miss_c), sum(r.pop for r in miss_c) / 1e6
            )
        )
        log.debug(
            "-- full list of cities with no {} estimate: {}".format(
                name, [r.name for r in miss_c]
            )
        )

    ############## Heuristic and estimation algorithms ############################

    def heuristic_set_pops(self):
        """
        Top-down: set unset children populations to min of:
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
                log.warning(
                    "Pop inconsistency at {!r}: {} vs {} total in subs".format(
                        reg, reg.pop, subpops
                    )
                )
            #            assert sum(r.pop for r in reg.sub) <= reg.pop * 1.1
            for r in reg.sub:
                rec(r)

        rec(self.root)

    def fix_min_est(self, name, minimum_from=None, minimum_mult=1.0, keep_nones=False):
        """
        Bottom-up: set est[name] to be at least sum of lower ests, and at least minimum.
        """

        def rec(reg):
            if minimum_from is not None:
                mfv = reg.est.get(minimum_from)
                if mfv is not None:
                    namev = reg.est.get(name, 0.0)
                    if namev < mfv * minimum_mult:
                        reg.est[name] = mfv * minimum_mult

            vs = [rec(r) for r in reg.sub]
            vs = [v for v in vs if v is not None]
            if vs or (reg.est.get(name) is not None) or (not keep_nones):
                e = reg.est.get(name, 0.0)
                mv = max(sum(vs), e if e is not None else 0.0)
            else:
                mv = None
            reg.est[name] = mv
            return mv

        rec(self.root)

    def propagate_down(self):
        """
        A rater hacky way to propagate `ft_mean` estimates down to city level.
        """
        def rec(reg):
            # Prefer ft_mean for estimate, or passed-down one
            est0 = reg.est.setdefault("est_active", None)
            est = reg.est.get("ft_mean", est0)
            if est is not None:
                reg.est["est_active"] = est
                # Children stats
                pops = np.array([r.pop for r in reg.sub], dtype=float)
                csses = np.array(
                    [r.est.get("csse_active") for r in reg.sub], dtype=float
                )
                fts = np.array([r.est.get("ft_mean") for r in reg.sub], dtype=float)
                # Part confirmed
                csse_ps = csses / pops

                # Mean infection rate in children with infos
                _pss = []
                for i, _p in enumerate(reg.sub):
                    if (not np.isnan(csse_ps[i])) and np.isnan(fts[i]):
                        _pss.append(csse_ps[i])
                if not _pss:
                    _pss = [0.01]  # any value just to make uniform est.
                mean_pss = max(np.mean(_pss), 0.0)
                # Set remaining csses (or all if none are set)
                for i, p in enumerate(reg.sub):
                    if np.isnan(csses[i]):
                        csses[i] = p.pop * mean_pss

                # After substracting any child estimates, what remains?
                rem_est = est - np.nansum(fts)
                # TODO: if this happens, do something more correct (take variance into account)
                if rem_est < 0.0:
                    log.warning(
                        "Node {!r}: rem_est={} (from node estimate {} and sum of child FTs {}), clipped to 0.0".format(
                            reg, rem_est, est, np.nansum(fts)
                        )
                    )
                    rem_est = 0.0

                # Set est_active
                csse_ftnan_sum = max(np.sum(csses, where=np.isnan(fts)), 0.0)
                for i, p in enumerate(reg.sub):
                    if np.isnan(fts[i]):
                        p.est["est_active"] = rem_est * csses[i] / csse_ftnan_sum

            if reg.est["est_active"] is None and reg.est.get("csse_active") is not None:
                log.debug(
                    "Node {!r}: Setting est_active={:.1f} [Prev none] from CSSE".format(
                        reg, reg.est["csse_active"]
                    )
                )
                reg.est["est_active"] = reg.est["csse_active"]

            if (
                reg.est["est_active"] is not None
                and reg.est.get("csse_active") is not None
            ):
                if reg.est["est_active"] < reg.est.get("csse_active"):
                    log.debug(
                        "Node {!r}: Setting est_active={:.1f} [Prev {:.3f}, smaller] from CSSE".format(
                            reg, reg.est["csse_active"], reg.est["est_active"]
                        )
                    )
                    reg.est["est_active"] = reg.est["csse_active"]

            for p in reg.sub:
                rec(p)

        rec(self.root)
