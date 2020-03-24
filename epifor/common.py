import datetime
import logging
import math
import sys

import subprocess
import jsonobject
import unidecode
from ruamel.yaml import YAML

log = logging.getLogger("epifor")

## A faster yaml implementation
yaml = YAML(typ="safe")  # default, if not specfied, is 'rt' (round-trip)
yaml.default_flow_style = False
yaml.sort_keys = False
yaml.indent = 4


def die(msg):
    log.fatal(msg)
    sys.exit(1)


def run_command(cmd):
    "Run external command and die on any error."
    cmd = list(cmd)
    log.debug(f"Running {cmd!r} ...")
    try:
        r = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        die(f"Error running {cmd!r}:\n{e}")
    if r.returncode != 0:
        die(f"Running {cmd!r} returned {r.returncode}")  # ":\n{r.stderr}\n{r.stdout}")


def _n(s):
    return unidecode.unidecode(str(s)).replace("-", " ").lower()


def _ncol(df, *cols):
    for col in cols:
        df[col] = df[col].map(_n)


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
        x = _e(getattr(obj, k))
        if x is not None or _n:
            r[k] = x
    for k, v in kws.items():
        x = _e(v)
        if x is not None or _n:
            r[k] = x
    return r


def geo_dist(lat1, lat2, dlong):
    R = 6373.0
    lat1, lat2, dlong = (
        lat1 * math.pi / 180,
        lat2 * math.pi / 180,
        dlong * math.pi / 180,
    )
    a = (
        math.sin((lat1 - lat2) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlong / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * R


class IgnoredProperty(jsonobject.JsonProperty):
    "Helper class to ignore object property with jsonobject."

    def __init__(self, typecheck=None):
        super().__init__()
        self.typecheck = typecheck

    def to_json(self, _value):
        raise NotImplementedError()

    def to_python(self, _value):
        raise NotImplementedError()

    def ip_check_type(self, obj):
        if self.typecheck is not None and not isinstance(obj, self.typecheck):
            raise TypeError(
                f"{self.__class__.__name__} expects value of type {self.typecheck}, got {obj!r}"
            )

    def wrap(self, value):
        self.ip_check_type(value)
        return value

    def unwrap(self, value):
        self.ip_check_type(value)
        return value, value

    def exclude(self, _value):
        return True


SKIP = [
    "holy see",
    "liechtenstein",
    "andorra",
    "san marino",
    "north macedonia",
    "from diamond princess",
    "cruise ship",
    "saint barthelemy",
    "gibraltar",
    "faroe islands",
    "channel islands",
    "st martin",
    "diamond princess",
    "grand princess",
]


UNABBREV = {
    "AB": "Alberta",
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AZ": "Arizona",
    "BC": "British Columbia",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": ["District of Columbia", "washington, d.c."],
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MB": "Manitoba",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MS": "Mississippi",
    "MT": "Montana",
    "NB": "New Brunswick",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NL": "Newfoundland and Labrador",
    "NM": "New Mexico",
    "NS": "Nova Scotia",
    "NT": "Northwest Territories",
    "NU": "Nunavut",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "ON": "Ontario",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "PE": "Prince Edward Island",
    "QC": "Quebec",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "SK": "Saskatchewan",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
    "YT": "Yukon",
}
