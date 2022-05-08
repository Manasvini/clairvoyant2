import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_style('darkgrid')

from edge_logs_parser import parse_logs, get_edge_number

def _parse_events(root_folder):
    cache_events = parse_logs(root_folder)

    first_insert = {}
    first_access = {}
    accesses = {}
    last_access = {}
    retention = {}

    for edge_node_file in cache_events:
        edge_node = get_edge_number(edge_node_file)
        print(f"processing for retention time {edge_node}")

        if len(cache_events[edge_node_file]) == 0:
            continue

        first_insert[edge_node] = {}
        first_access[edge_node] = {}
        accesses[edge_node] = {}
        last_access[edge_node] = {}
        retention[edge_node] = {}

        for txn in cache_events[edge_node_file]:
            entries = txn.split(",")
            
            segment = entries[0]
            txn_type = int(entries[2])
            txn_time = int(entries[3])

            if (txn_type == 0) and ( segment not in first_insert[edge_node] ):
                first_insert[edge_node][segment] = txn_time

            if (txn_type == 1):
                if segment not in first_access[edge_node]:
                    first_access[edge_node][segment] = txn_time
                    accesses[edge_node][segment] = 1
                    last_access[edge_node][segment] = txn_time
                    retention[edge_node][segment] = 0
                else:
                    accesses[edge_node][segment] = accesses[edge_node][segment] + 1
                    last_access[edge_node][segment] = txn_time
                    retention[edge_node][segment] = last_access[edge_node][segment] - first_access[edge_node][segment] 
    
    return first_insert, first_access, accesses, last_access, retention

def plot_retention_metrics(root_folder, filename):
    first_insert, first_access, accesses, last_access, retention= _parse_events(root_folder)
    retentiondf = pd.DataFrame.from_dict(retention, orient='index')
    accessesdf = pd.DataFrame.from_dict(accesses, orient='index')

    sns.boxplot(data=retentiondf.T, order=range(1, 11))
    plt.xlabel("Edge node")
    plt.ylabel("Retention time (s)")
    plt.title(f"Retention time per node for {filename}")
    plt.savefig(f'./plots/{filename}_retention.png')
    plt.clf()
