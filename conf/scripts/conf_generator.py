from argparse import ArgumentParser
import json, os, csv
import pandas as pd

parser = ArgumentParser()
parser.add_argument('-n', '--num-config', type=int, default=1, help='Number of configs to generate')
parser.add_argument('-t', '--template', type=str, required=True, help='template file')
args = parser.parse_args()

def get_repo_root():
    cwd = os.getcwd()
    repo_basename = 'clairvoyant2'
    tokens = cwd.split(repo_basename)
    repo_root = tokens[0] + repo_basename
    return repo_root

repo_root = get_repo_root()
out_dir = f'{repo_root}/conf/scripts/gen_confs'
print(out_dir)
os.system(f'rm -rf {out_dir}')
os.system(f'mkdir -p {out_dir}')

modelmapfile = repo_root + '/models/model_map.csv'

df = pd.read_csv(modelmapfile, header=None)

try:
    with open(args.template, 'r') as fh:
        obj = json.loads(fh.read())
    for i in range(args.num_config):
        outfile = os.path.join(out_dir, f'edgeConfig{i}.json')
        with open(outfile, 'w') as fw:
            obj['nodeId'] = "node_{}".format(i)
            obj['modelFile'] = f"../../models/{df[1][i]}" #bad idea to use relative paths
            fw.write(json.dumps(obj, indent=2))
except Exception as e:
    print(e.trace())
    print('Incorrrect template file')
