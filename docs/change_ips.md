# Making setup work on different cosmos machines

## Prequisites
This assumes, you have an 8 core vm which runs your cloud, client, metadata service & the redis cluster. You then have 'n' 2 core vms which are your edge nodes.

You need to create a sshconfig file for quick access to the machines. Sample ssh config can be found in `conf/scripts/sshconfig`. These for the cosmos vms. Keys for the same are in the shared directory on cosmos `/epl-shared/clairvoyant/sshkeys/`. Note, you may have to create your own copy of these private key files to overcome permission issues.

We first need a file in `clairvoyant2/conf/ipinfo.csv` (ensure file is under that path) which has a mapping between `node_id` and IP address.Example file (meant for cosmos cv2 group of vms) can be found in `clairvoyant2/conf/ipinfo.csv`

1. run `python3 change_ips.py` 
2. This changes the ips in:
    1. `conf/10node_monacoCloudConfig.json`
    2. `conf/scripts/gen_confs/edgeConfig*.json`
    3. `conf/edgeConfig.json` (so that it's available to the edge config generator script)
    4. `conf/download_source_info.json`
    5. `src/clientrunner_go/input/microbenchmark/bench2/*.csv`
3. New configs are generated (1. - 4.) are generated within `conf/scripts/tmp/`. New config for 5. is created under a separate `tmp/` directory in the source directory.


## Other changes that went with the commit.
1. cv2 set of machines do not have the go runtime. Therefore, `edge_go` binary is built once, copied to all edge nodes. Scripts are updated to execute the binary instead of using `go run .` command.
2. Also committed the overlapping `1x.zip` routes under eval/microbenchmark/bench2/users/10nodes/1kusers/overlapped/set1. each set mapping is defined under `overlapped/setmap.info`

