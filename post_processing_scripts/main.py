from cache_size_plots import cache_size_plot, cumulative_plot

all_times0, all_sizes0 = cache_size_plot("../clairvoyant2_logs/1userbase_used/0/all_logs", "0")
all_times1, all_sizes1 = cache_size_plot("../clairvoyant2_logs/1userbase_used/5/all_logs", "5")
cumulative_plot([all_times0, all_times1], [all_sizes0, all_sizes1], ["0", "5"], "0 vs 50% procastination")
