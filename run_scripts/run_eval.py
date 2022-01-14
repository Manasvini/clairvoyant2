#!/usr/bin/python3

import json
import subprocess
import sys
import time

def read_config(filename):
    with open(filename) as fh:
        conf = json.load(fh)
    return conf

def start_cloud(conf):
    numEdgeNodes = conf['numEdgeNodes']
    cloudConfig = conf['cloudConfig']
    edgePos = conf['edgePositions']
    numVideos = conf["numUsers"] * 2 + 1
    segmentFile = conf['segmentFile']
    result = subprocess.run(['ssh', conf['cloudServerName'], \
                            'cd clairvoyant2 && bash run_scripts/start_cloud_services.sh ' +\
                             str(numEdgeNodes) + ' ' + cloudConfig + ' ' + edgePos + ' ' + str(numVideos) + ' ' + segmentFile], \
                             shell=False, \
                             check=False)
    print('cloud success=', result.returncode) 

def start_edge(conf):
    numEdgeNodes = conf['numEdgeNodes']
    machinePrefix = conf['machinePrefix']
    result = subprocess.run(['bash', 'run_scripts/start-edge-svrs.sh',\
                            str(numEdgeNodes), str(machinePrefix)],\
                            shell=False, \
                            check=False)
    print('edge success=', result.returncode)

def start_clients(conf):
    numClients = conf["numUsers"]
    numVideos = conf['numUsers'] * 2 
    clientTrajectories = conf['trajectoriesDir']
    edgeInfo = conf['edgeInfoFile']
    outputFile = conf['outputDir'] + "/" + str(numClients) + 'users' + str(conf['numEdgeNodes']) + 'nodes' + str(round(time.time() * 1000)) + '.csv'
    segmentFile = conf['segmentFile']
    cloudServer = conf['cloudServerName']
    result = subprocess.run(['ssh', cloudServer, ' export PATH=$PATH:/usr/local/go/bin && cd clairvoyant2/src/clientrunner_go && go run . ' +\
                            '-log_dir=\".\"'+\
                            ' -t ' + clientTrajectories + \
                            ' -i ' + str(numVideos) + \
                            ' -n ' + str(numClients) + \
                            ' -o ' + outputFile +\
                            ' -e ' + edgeInfo + \
                            ' -f ' + segmentFile], \
                            shell=False,\
                            check=False)
    print('client success=', result.returncode)

def main():
    conf = read_config(sys.argv[1])
    #example conf script in eval folder 10node_conf.json
    num_trials = conf['numTrials']
    start = time.time()
    for i in range(num_trials):
        start_cloud(conf)
        start_edge(conf)
        time.sleep(10)
        start_clients(conf)
    end = time.time()
    print(num_trials, " trials took ", (end-start), " seconds")

if __name__=='__main__':
    main()
