from argparse import ArgumentParser
import json, os

parser = ArgumentParser()
parser.add_argument('-n', '--num-config', type=int, default=1, help='Number of configs to generate')
parser.add_argument('-t', '--template', type=str, required=True, help='template file')
parser.add_argument('-p', 'gen-path', required=True, help='path to generated files')
args = parser.parse_args()


try:
    with open(args.template, 'r') as fh:
        obj = json.loads(fh.read())
    for i in range(args.num_config):
        outfile = os.path.join(args.gen_path, 'edgeConf{}.json'.format(i))
        with open(outfile, 'w') as fw:
            obj['nodeId'] = "node_{}".format(i)
            fw.write(json.dumps(obj))
except Exception as e:
    print(e.trace())
    print('Incorrrect template file')
