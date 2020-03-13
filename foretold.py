import re
from dateutil import parser
import numpy as np

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
