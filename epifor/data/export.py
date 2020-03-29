import datetime
import getpass
import json
import socket

from ..common import _fs
from ..regions import Region


class ExportDoc:
    def __init__(self, comment=None):
        self.created = datetime.datetime.now().astimezone()
        self.created_by = f"{getpass.getuser()}@{socket.gethostname()}"
        self.comment = comment
        self.regions = {}

    def to_json(self, toweb=False):
        return _fs(
            self,
            "created",
            "created_by",
            "comment",
            _n=True,
            regions={k: a.to_json(toweb=toweb) for k, a in self.regions.items()},
        )

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
        assert isinstance(self.region, Region)
        return getattr(self.region, name)

    def to_json(self, toweb=False):
        return _fs(
            self,
            "kind",
            "lat",
            "lon",
            "name",
            "population",
            "gleam_id",
            "data",
            "iso_alpha_3",
            "max_percentage_of_infected_to_fill_icu_beds",
            _n=False,
        )

    @classmethod
    def from_json(cls, data):
        pass  # TODO
