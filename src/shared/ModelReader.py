import pandas as pd
import numpy as np
import random
import bisect 

class Model:
    def __init__(self, filename):
        self.model = {}
        self.dists = []
        with open(filename) as fh:
            lines = fh.readlines()
            for l in lines:
                vals = l.strip().split(',')
                self.model[int(vals[0])] = {'mean': float(vals[1]), 'stddev':float(vals[2])}
                self.dists.append(int(vals[0]))
        self.dists = sorted(self.dists)

    def get_download_speed(self, distance):
        idx = bisect.bisect_left(self.dists, distance)
        dist = self.dists[min(idx, len(self.dists)-1)]
        mean = self.model[dist]['mean']
        stddev = self.model[dist]['stddev']
        stdtdev = 0
        #return mean +  random.uniform(-stddev, stddev)
        return mean

    def get_model_dist(self, distance):
        idx = bisect.bisect_left(self.dists, distance)

        if idx > len(self.dists) - 1:
            return self.dists[len(self.dists)-1]

        if idx != 0:
            if abs(distance - self.dists[idx]) < abs(distance - self.dists[idx-1]):
                return self.dists[idx]
            else:
                return self.dists[idx-1]
        else:
            return self.dists[idx]
            
