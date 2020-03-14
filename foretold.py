### MILDLY WIP

import json
import pathlib
import re

import numpy as np
import pandas as pd
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
        self.pdf = np.concatenate((self.pred_ys[1:], [1.0])) - self.pred_ys
        self.mean = np.dot(self.pdf, self.pred_xs)
        self.subject = node["labelSubject"]
        self.name = re.sub('^@locations/n-', '', self.subject).replace('-', ' ').capitalize()
        return self

    def to_dataframe(self) -> pd.DataFrame:
        """Export as a simple dataframe."""
        return pd.DataFrame({
            "name": self.name,
            "date": self.date,
            "x": self.pred_xs,
            "cdf": self.pred_ys,
            "pdf": self.pdf,
        })


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

    def apply_to_regions(self, rs):
        pass

    def to_dataframe(self) -> pd.DataFrame:
        """Export as a dataframe containing all the data.
        
        See FTPrediction.to_dataframe for columns.
        """
        return pd.concat(
            prediction.to_dataframe() for prediction in self.predictions
        )

