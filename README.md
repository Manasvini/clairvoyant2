## Dependencies  
Install github.com/Manasvini/clairvoyantedge-metadata. The parent directory should be common for this repo and clairvoyantedge-metadata.  
### Running the code

> Check the configuration eval/conf/10node_conf.json
 
Then run the following in the cosmos staging from the project root.

```shell
python3 run_scripts/run_eval.py eval/conf/10node_conf.json ../result_dir
```

Check the logs (.csv and .csv.edge) in the output directory mentioned in the configuration file.

### VM set change

Set 1: 192.168.160.22
set 2: 192.168.160.42

Make ip changes to the following

10nodes_monacoCloudConfig.json
clientrunner_go/input/*.csv
run_scripts/start_cloud_services.sh

### Benchmark 2 run instructions

1. Start redis
2. Add the right 10 edge nodes to redis. Path for edge nodes: `clairvoyant2/eval/enode_positions/microbenchmark/bench2/m2_node_positions/10nodes_random.csv`
3. Start metadata server: `bash clairvoyantedge-metadata/scripts/start_meta_svr.sh`
4. Load videos: 
```
~/clairvoyantedge-metadata/scripts$ bash video_creator.sh ../build/metadata/scripts/data-uploader 80 ../../clairvoyant2/eval/videos/bbb_2ksegs.csv 
```
5. Make sure both cloud and edge config is appropriate.
6. Run the `clairvoyant2/run_scripts/startall.py` to run the system except clientrunner:
    1. Starts cloud
    2. Starts clock server 
    3. Starts Edge:
        1. Builds Edge binaries
        2. Copies Edge binaries to 10 edge nodes
        3. Run the binary
7. Once "Ready!" appears on the console, you can start the clientrunner.
8. To run clientrunner:
```bash
~/clairvoyant2/src/clientrunner_go$ go run . -logtostderr=1 \
                                             -t ../../eval/enode_positions/microbenchmark/bench2/30users_new/ \
                                             -i 1 -n 10 \
                                             -e input/bench2_10nodes.csv \
                                             -f ../../eval/videos/bbb_2ksegs.csv \
                                             -o result.txt 2>&1 | tee test.out
```
9. Once clientrunner completes, you cat exit the the 'startall.py' script using ^C.
10. Hitting ^C should generate the results file per edge on every edge.

### TODO
1. clientrunner exits early for benchmark2 purposes. Make this behavior config driven.
2. Aggregate results from edge
3. Currently tested with mode=All2All & cache=lru. Need to test for all cases.

