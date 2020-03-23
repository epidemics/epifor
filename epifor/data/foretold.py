### MILDLY WIP

import json
import logging
import re

import numpy as np
import pandas as pd
from dateutil import parser

from ..common import SKIP, _n

log = logging.getLogger("epifor")


class FTPrediction:
    def __init__(self):
        pass

    @classmethod
    def from_ft_node(cls, node):
        pa = node["previousAggregate"]
        if not pa:
            return None
        self = cls()
        self.date = parser.isoparse(node["labelOnDate"])

        self.subject = node["labelSubject"]
        self.name = _n(re.sub("^@locations/n-", "", self.subject).replace("-", " "))

        # TODO: verify/test
        # TODO: now this treats it like a discrete distribution with xs vals,
        #       this is fine for ~1000 samples from FT, but may need fixing otherwise
        self.pred_xs = np.array(pa["value"]["floatCdf"]["xs"])
        self.pred_ys = np.array(pa["value"]["floatCdf"]["ys"])
        self.pdf = np.concatenate((self.pred_ys[1:], [1.0])) - self.pred_ys
        self.mean = np.dot(self.pdf, self.pred_xs)
        self.var = np.dot(self.pdf, np.abs(self.pred_xs - self.mean) ** 2)
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """Export as a simple dataframe."""
        return pd.DataFrame(
            {
                "name": self.name,
                "date": self.date,
                "x": self.pred_xs,
                "cdf": self.pred_ys,
                "pdf": self.pdf,
            }
        )


SELECT_KINDS = {
    "washington": "city",
    "new york": "city",
    "hong kong": "city",
    "georgia": "state",
}


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

    def last_before(self, date):
        res = {}
        for sl in self.subjects.values():
            last = None
            for p in sl:
                if p.date <= date and (last is None or p.date > last.date):
                    last = p
            if last:
                res[p.subject] = last
        return res

    def load(self, path):
        with open(path, "rt") as f:
            self._loaded = json.load(f)
        d = self._loaded["data"]["measurables"]["edges"]
        for p in d:
            ft = FTPrediction.from_ft_node(p["node"])
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

    def to_dataframe(self) -> pd.DataFrame:
        """Export as a dataframe containing all the data.
        
        See FTPrediction.to_dataframe for columns.
        """
        return pd.concat(prediction.to_dataframe() for prediction in self.predictions)

    def apply_to_regions(self, regions, before=None):
        if before:
            d = self.last_before(before)
        else:
            d = self.latest
        dlist = [
            i.strftime("%Y-%m-%d") for i in set([r.date.date() for r in d.values()])
        ]
        log.info(
            "Using foretold {} predictions from days {}".format(
                len(d), ", ".join(dlist)
            )
        )
        for p in d.values():
            if _n(p.name) in SKIP:
                continue
            regs = regions.find_names(p.name, kinds=SELECT_KINDS.get(_n(p.name)))
            if len(regs) < 1:
                log.warning("Foretold region %r not found in Regions, skipping", p.name)
                continue
            if len(regs) > 1:
                log.warning(
                    "Foretold region %r matches several Regions: %r, skipping",
                    p.name,
                    regs,
                )
                continue
            reg = regs[0]
            reg.est["ft_mean"] = p.mean
            reg.est["ft_var"] = p.var

    def propagate_down(self, regions):
        def rec(reg):
            # Prefer ft_mean for estimate, or passed-down one
            est0 = reg.est.setdefault("est_active", None)
            est = reg.est.get("ft_mean", est0)
            if est is not None:

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

        rec(regions.root)
