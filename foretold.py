import json
import pathlib
import re

import numpy as np
from dateutil import parser


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
        p = np.concatenate((self.pred_ys[1:], [1.0])) - self.pred_ys
        self.mean = np.dot(p, self.pred_xs)
        self.subject = node["labelSubject"]
        self.name = re.sub('^@locations/n-', '', self.subject).replace('-', ' ').capitalize()
        return self


def load_ft(path):
    d = json.loads(pathlib.Path(path).read_text())["data"]["measurables"]['edges']
    fts = {}
    for p in d:
        ft = FTPrediction.from_ft_node(p['node'])
        if ft is None:
            continue
        if ft.name not in fts or ft.date > fts[ft.name].date:
            fts[ft.name] = ft
    return fts
