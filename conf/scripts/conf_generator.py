from argparse import ArgumentParser
import json, os, csv
import pandas as pd

parser = ArgumentParser()
parser.add_argument('-n', '--num-config', type=int, default=1, help='Number of configs to generate')
parser.add_argument('-t', '--template', type=str, required=True, help='template file')
parser.add_argument('-p', '--gen-path', required=True, help='path to generated files')
args = parser.parse_args()

modelmapfile='../models/model_map.csv'
df = pd.read_csv(modelmapfile, header=None)

try:
    with open(args.template, 'r') as fh:
        obj = json.loads(fh.read())
    for i in range(args.num_config):
        outfile = os.path.join(args.gen_path, 'edgeConfig{}.json'.format(i))
        with open(outfile, 'w') as fw:
            obj['nodeId'] = "node_{}".format(i)
            obj['modelFile'] = f"../../models/{df[1][i]}"
            obj['serverAddress'] = "192.168.160.21:60050"
            obj['monServerAddress'] = "192.168.160.21:8192"
            obj["contentServerAddress"] = "0.0.0.0:8000"
            obj["contentServerMaxClients"] = 2
            obj["edgeServerAddress"] = "0.0.0.0:50056"
            obj["cacheSize"] = 100000000000
            obj["cacheType"] = "lru"
            obj["clockServerAddr"] = "192.168.160.21:8383"
            fw.write(json.dumps(obj, indent=2))
except Exception as e:
    print(e.trace())
    print('Incorrrect template file')