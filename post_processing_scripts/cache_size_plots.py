from os import system
import sys
import matplotlib.pyplot as plt

from edge_logs_parser import parse_logs, get_edge_number


def _plot_all(all_times, all_sizes, plotname, plotfilename):
    with plt.style.context('ggplot'):
        for key in all_times:
            plt.plot(all_times[key], all_sizes[key], label=get_edge_number(key))

        plt.legend()
        plt.title(f"Sizes vs Time plot {plotname}")
        plt.xlabel('Time')
        plt.ylabel('Size')
        plt.savefig(f"./{plotfilename}.png")
        plt.clf()


def _get_time_size_map(entries):
    min_time = 0
    max_time = 0
    time_size_map = {}

    for entry in entries:
        splits = entry.split(",")
        time, size = int(splits[-2]), int(splits[-1])/10e6

        if time > max_time:
            max_time = time
        
        if time < min_time:
            min_time = time

        time_size_map[time] = size

    return min_time, max_time, time_size_map

def _get_times_sizes(min_time, max_time, time_size_map):
    times = []
    sizes = []

    old_size = 0

    for i in range(min_time, max_time + 1):
        times.append(i)

        if i in time_size_map:
            sizes.append(time_size_map[i])
            old_size = time_size_map[i]
        else:
            sizes.append(old_size)

    return times, sizes

def _fix_system_end_time(all_times, all_sizes, system_max_time):
    for key in all_times:
        start = all_times[key][-1]
        val = all_sizes[key][-1]

        for i in range(start, system_max_time + 1):
            all_times[key].append(i)
            all_sizes[key].append(val)

def _parse_events(root_folder):
    cache_events = parse_logs(root_folder)

    all_times = {}
    all_sizes = {}

    system_max_time = 0

    for key in cache_events:
        print(f"processing {key}")

        if len(cache_events[key]) == 0:
            continue

        min_time, max_time, time_size_map = _get_time_size_map(cache_events[key])

        if system_max_time < max_time:
            system_max_time = max_time

        times, sizes = _get_times_sizes(min_time, max_time, time_size_map)

        all_times[key] = times
        all_sizes[key] = sizes

    _fix_system_end_time(all_times, all_sizes, system_max_time)

    return all_times, all_sizes

def cache_size_plot(folder_name, plotname):
    parsed_all_times, parsed_all_sizes = _parse_events(folder_name)
    _plot_all(parsed_all_times, parsed_all_sizes, folder_name, plotname)
