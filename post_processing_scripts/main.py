from statistics import mean

import pandas as pd
import pickle

from cache_size_plots import cache_size_plot, cumulative_plot, stats_plot
from retention_time_plots import plot_retention_metrics
from edge_logs_parser import get_edge_number

# _parse_events("../clairvoyant2_logs/procastination_bugfix/100-1-5/all_logs")

all_times = []
all_sizes = []
# folders = ["100-1-0", "100-1-5", "10-1-0", "10-1-5", "100-10-0", "100-10-5"]
folders = ["1-0", "1-5", "10-0", "10-5", "100-0", "100-5", "200-0", "200-5"]

stats = {}

for i in folders:
    folder = f"../clairvoyant2_logs/procastination_15mps/{i}/all_logs"
    # _1, _2 = cache_size_plot(f"../clairvoyant2_logs/procastination_bugfix/{i}/all_logs", i)
    _1, _2 = cache_size_plot(folder, i)
    all_times.append(_1)
    all_sizes.append(_2)

    stats[i] = {}
    for j in _2:
        stats[i][get_edge_number(j)] = {
            'Max Cache Size': max(_2[j]),
            'Mean Cache Size': mean(_2[j])
        }

    plot_retention_metrics(folder, i)

cumulative_plot(all_times, all_sizes, folders, "0% vs 50% procastination")
stats_plot(stats, all_sizes, folders)
