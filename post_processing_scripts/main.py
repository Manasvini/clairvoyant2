from cache_size_plots import cache_size_plot, cumulative_plot
from retention_time_plots import plot_retention_metrics

# _parse_events("../clairvoyant2_logs/procastination_bugfix/100-1-5/all_logs")

all_times = []
all_sizes = []
# folders = ["100-1-0", "100-1-5", "10-1-0", "10-1-5", "100-10-0", "100-10-5"]
folders = ["1-0", "1-5"]

for i in folders:
    folder = f"../clairvoyant2_logs/procastination_15mps/{i}/all_logs"
    # _1, _2 = cache_size_plot(f"../clairvoyant2_logs/procastination_bugfix/{i}/all_logs", i)
    _1, _2 = cache_size_plot(folder, i)
    all_times.append(_1)
    all_sizes.append(_2)

    plot_retention_metrics(folder, i)

cumulative_plot(all_times, all_sizes, folders, "0% vs 50% procastination")

