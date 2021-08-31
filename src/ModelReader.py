import pandas as pd
import numpy as np
from sortedcontainers import SortedDict
import random
class Model:
    def __init__(self, filename):
        self.model = SortedDict()
        with open(filename) as fh:
            lines = fh.readlines()
            for l in lines:
                vals = l.strip().split(',')
                self.model[int(vals[0])] = {'mean': float(vals[1]), 'stddev':float(vals[2])}

    def get_download_speed(self, distance):
        keys = list(self.model.irange(minimum=distance))
        if len(keys) > 0:
            mean = self.model[keys[0]]['mean']
            stddev = self.model[keys[0]]['stddev']
            return mean +  random.uniform(-stddev, stddev)
        return 0
