import datetime
import getpass
import json
import socket

from ..regions import Region


def _e(o):
    "Filter to reformat objects before serialization"
    if isinstance(o, datetime.datetime):
        return o.astimezone().isoformat()
    if isinstance(o, datetime.date):
        return o.isoformat()
    return o


def _fs(obj, *attrs, _n=True, **kws):
    "Collect a dict of `{a: obj.a}` for `attrs` and `{k: v} for `kws`"
    r = {}
    for k in attrs:
        x = _e(obj.__getattribute__(k))
        if x is not None or _n:
            r[k] = x
    for k, v in kws.items():
        x = _e(v)
        if x is not None or _n:
            r[k] = x
    return r


class ExportDoc:
    def __init__(self, comment=None):
        self.created = datetime.datetime.now().astimezone()
        self.created_by = f"{getpass.getuser()}@{socket.gethostname()}"
        self.comment = comment
        self.regions = {}

    def to_json(self, toweb=False):
        return _fs(self, "created", "created_by", "comment", _n=True,
            regions={k: a.to_json(toweb=toweb) for k, a in self.regions.items()})

    @classmethod
    def from_json(cls, data):
        pass  # TODO

    def __getitem__(self, o):
        if isinstance(o, str):
            return self.regions[o]
        if isinstance(o, Region):
            return self.regions[o.key]
        else:
            raise TypeError(f"Indexing with type {type(o)} unsupported: {o!r}")

    def add_region(self, region):
        assert isinstance(region, Region)
        er = ExportRegion(region)
        self.regions[region.key] = er
        return er


class ExportRegion:
    def __init__(self, region):
        assert isinstance(region, Region)
        self.region = region
        self.data = {}  # {name: anything}

    def __getattr__(self, name):
        return self.region.__getattribute__(name)

    def to_json(self, toweb=False):
        return _fs(self, "kind", "lat", "lon", _n=False,
            name=self.name.capitalize(),
            population=self.pop, gleam_id=self.gv_id, data=self.data)

    @classmethod
    def from_json(cls, data):
        pass  # TODO
