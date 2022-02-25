from functools import cache
import sys
from os import listdir
from os.path import isfile, join

import pandas as pd

def parseCacheEvents(val, nodeId, cacheEvents, index, eventEnum):
    val = val[1:]
    val = val.split(',')
    cacheEvents.append({
        "Index": index,
        "NodeId": nodeId,
        "SegmentId": val[0],
        "RouteId": int(val[1]),
        "EventType": eventEnum[int(val[2])],
        "Time": int(val[3])
    })

def parseLogs(folder):
    cacheEvents = []
    eventEnum = ['PushEvent', "TouchEvent", "EvictableEvent", "PopEvent"]
    index = 1

    print(f"Iterating over all files in {folder}")
    for f in listdir(folder):
        if not isfile(join(folder, f)):
            continue
        if "edge_go" not in str(f):
            continue
        print(f"Parsing {f}")

        nodeId = int(str(f)[7:-5])
        
        for line in open(join(folder, f), 'r').readlines():
            splits = line.split("[extended_utilites]")
            
            if len(splits) <= 1:
                continue
            
            splits = splits[1].split("]")
            if "cache_event" in splits[0]:
                parseCacheEvents(splits[1], nodeId, cacheEvents, index, eventEnum)

            index = index + 1

    return pd.DataFrame(data=cacheEvents)


def __main__():
    assert(len(sys.argv) == 2)
    folder = sys.argv[1]

    df = parseLogs(folder)
    df.to_csv("cache_events.csv", index=False)

__main__()