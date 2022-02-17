# Benchmark 2

## Goal
What is the cache size and configuration needed to reasonably reduce backhaul bandwidth?

## Simplifying assumptions
1. Assume All-to-All connections between all edge nodes
2. A workload of 100 users which maybe overlapping or non overlapping w.r.t to journey start & end.
3. The workload requests video from at least a set of `2*num_users` based on some popularity distribution (currently zipfian)

## Control knobs
1. Cache configurations: LRU, LFU
2. Cache sizes: TBD (explore starting with arbitrarily large size and decreasing them in reasonable sizes)

## Expectation
1. track backhaul bandwidth & cache evictions
2. Evictions should correlate with higher backhaul bandwidth utilization as we *vary* the cache configuration.
