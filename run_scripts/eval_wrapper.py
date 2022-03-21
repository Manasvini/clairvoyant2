import json
import os
import subprocess
import sys
CACHE_SIZES = [1, 5, 10, 20, 50, 100]
CACHE_POLICIES = ['lru']
NUM_USERS = ['1kusers']
PREFETCH_POLICIES = ['all2all']
def update_edge_config(cache_size, cache_policy):
    edge_config = None
    with open('conf/edgeConfig.json') as fh:
        edge_config = json.load(fh)
        edge_config['cacheType'] = cache_policy
        edge_config['cacheSize'] = int(cache_size * 1000 * 1000 * 1000) #GB
        fh.close()
    with open('conf/edgeConfig.json', 'w') as fh:
        json.dump(edge_config, fh, indent=4)

def do_eval(cache_size, cache_policy, num_users, prefetch, eval_conf_file, testname):
    update_edge_config(cache_size, cache_policy)
    print(['python3',\
                    'run_scripts/run_eval.py',\
                     eval_conf_file, \
                    'results/' + testname + '/' + str(cache_size) + 'gig_' + str(cache_policy) + '_' + prefetch  + '/' + num_users])

    result = subprocess.run(['python3',\
                    'run_scripts/run_eval.py',\
                     eval_conf_file, \
                    'results/' + testname + '/' + str(cache_size) + 'gig_' + str(cache_policy) + '_' + prefetch  + '/' + num_users ])
    print('eval returned ' , result)

if __name__ == '__main__':
    eval_conf_file = sys.argv[1]
    testname = sys.argv[2]
    for cs in CACHE_SIZES:
        for cp in CACHE_POLICIES:
            for n in NUM_USERS:
                for pp in PREFETCH_POLICIES:
                    do_eval(cs, cp, n, pp, eval_conf_file, testname)
