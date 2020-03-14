### HEAVILY WIP

import csv
import datetime
import json
import logging
import math
import os
import pickle
import re
import subprocess
import sys
from math import pi
from pathlib import Path

import numpy as np
import pandas as pd
import unidecode

log = logging.getLogger()

class CSSEData:

    def __init__(self):
        self.df = None

    def load(self, pattern):
        dfs = []
        for name in ["Confirmed", "Deaths", "Recovered"]:
            df = pd.read_csv(pattern.format(name), header=0)
            dcs = list(df.columns)[4:]
            # NOTE: Some areas have 0 in last column even if nonzero before
            df[name] = df[dcs].max(axis=1)
            for c in dcs:
                del df[c]
            dfs.append(df)
        d = dfs.pop()
        for d2 in dfs:
            del d2['Lat']
            del d2['Long']
            d = d.merge(d2, on=["Province/State", "Country/Region"], how='outer')
        d['Infections'] = d['Confirmed'] - d['Deaths'] - d['Recovered']
        self.df = d

    def apply_to_regions(self, regions):
        pass
