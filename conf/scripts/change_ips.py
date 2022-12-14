import json
import csv
import sys
import re
import pandas as pd

import os
def get_repo_root():
    cwd = os.getcwd()
    repo_basename = 'clairvoyant2'
    tokens = cwd.split(repo_basename)
    repo_root = tokens[0] + repo_basename
    return repo_root

repo_root = get_repo_root()
os.system(f'rm -rf {repo_root}/conf/scripts/tmp')
os.system(f'mkdir -p {repo_root}/conf/scripts/tmp/edge')
os.chdir(f'{repo_root}/conf')
out_dir=f'{repo_root}/conf/scripts/tmp'


# change the ips in the following configs
ipFile=sys.argv[1]
ipInfo = {}
with open(ipFile) as fh:
    csvreader = csv.reader(fh, delimiter=',')
    hdr=next(csvreader)
    for row in csvreader:
        ipInfo[row[0]] = row[1]



# download_source_info.json
with open('download_source_info.json') as fh:
    data = json.loads(fh.read())
    for entry in data:
        entry["src_ip"] = ipInfo[entry["src_id"]] + ":8000"

    with open(f'{out_dir}/download_source_info.json','w') as fw:
        fw.write(json.dumps(data, indent=2))
    

# 10node_monacoCloudConfig.json
with open('10node_monacoCloudConfig.json') as fh:
    data = json.loads(fh.read())
    for entry in data["edgeNodes"]:
        entry['ip'] = ipInfo[entry['id']]

    with open(f'{out_dir}/10node_monacoCloudConfig.json','w') as fw:
        fw.write(json.dumps(data, indent=2))


# edge/edgeConfig*.json
edgeconfigs = os.listdir('edge')
for cfg in edgeconfigs:
    if cfg.startswith('.'):
        continue
    fname = 'edge/{}'.format(cfg)
    with open(fname) as fh:
        m = re.search('edgeConfig(.*)\.json', cfg)
        key = "node_" + m.group(1)
        data = json.loads(fh.read())
        data["serverAddress"] = ipInfo["cloud"] + ":60050"
        data["monServerAddress"] = ipInfo["cloud"] + ":8192"
        data["clockServerAddr"] = ipInfo["cloud"] + ":8383"

        with open(f'{out_dir}/edge/'+cfg,'w') as fw:
            fw.write(json.dumps(data, indent=2))

# edgeConfig.json
with open('edgeConfig.json') as fh:
    data = json.loads(fh.read())
    data["serverAddress"] = ipInfo["cloud"] + ":60050"
    data["monServerAddress"] = ipInfo["cloud"] + ":8192"
    data["clockServerAddr"] = ipInfo["cloud"] + ":8383"

    with open(f'{out_dir}/edgeConfig.json','w') as fw:
        fw.write(json.dumps(data, indent=2))

# clienrunner/input/microbenchmark/bench2
def update_ips_in_clientrunner(src, dest):
    files = os.listdir(src)
    for f in files:
        if 'model' in f or (not os.path.isfile(os.path.join(src, f))) or (f.startswith('.') or f.startswith('tmp')):
            continue
        fname = src + f
        df = pd.read_csv(fname)
        for i in range(len(df)):
            nodeid= df.iloc[i]['id']
            df.at[i,'ip'] = ipInfo[nodeid]
        df.to_csv(dest+f, index=False)
    
srcs = [repo_root + '/src/clientrunner_go/input/microbenchmark/bench2/', repo_root + '/src/clientrunner_go/input/scale/']
for src in srcs:
    dest = src + '/tmp/'
    os.system(f'rm -rf {dest}')
    os.system(f'mkdir -p {dest}')

    update_ips_in_clientrunner(src, dest)
            
