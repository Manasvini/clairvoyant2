#!/usr/bin/python3

import json
import subprocess
import sys
import time

def read_config(filename):
    with open(filename) as fh:
        conf = json.load(fh)
    return conf

def start_cloud(conf, repopulate_db):
    numEdgeNodes = conf['numEdgeNodes']
    cloudConfig = conf['cloudConfig']
    edgePos = conf['edgePositions']
    numVideos = conf["numUsers"] * 2 + 1
    segmentFile = conf['segmentFile']
    result = subprocess.run(['ssh', conf['cloudServerName'], \
                            'cd clairvoyant2 && bash run_scripts/start_cloud_services.sh ' +\
                             str(numEdgeNodes) + ' ' + \
                             cloudConfig + ' ' + \
                             edgePos + ' ' +\
                             str(numVideos) + ' ' +\
                             segmentFile + ' ' \
                             + repopulate_db], \
                             shell=False, \
                             check=False)
    print('cloud success=', result.returncode) 

def stop_edge(conf):
    numEdgeNodes = conf['numEdgeNodes']
    machinePrefix = conf['machinePrefix']
    result = subprocess.run(['bash', 'run_scripts/kill-edge-go-svrs.sh',\
                            str(numEdgeNodes), str(machinePrefix)],\
                            shell=False, \
                            check=False)

def start_edge(conf):
    numEdgeNodes = conf['numEdgeNodes']
    machinePrefix = conf['machinePrefix']
    result = subprocess.run(['bash', 'run_scripts/start-edge-go-svrs.sh',\
                            str(numEdgeNodes), str(machinePrefix)],\
                            shell=False, \
                            check=False)
    print('edge success=', result.returncode)

def gather_results(conf, localResultDir):
    resultDir = conf['edgeResultDir']
    numEdgeNodes = conf['numEdgeNodes']
    machinePrefix = conf['machinePrefix']
    
    result = subprocess.run(['scp', '-r', 'cvuser@' + machinePrefix + '0:' +  conf['outputDir'] ,  localResultDir  ])  
    for i in range(numEdgeNodes):
        result = subprocess.run(['scp', '-r', 'cvuser@' + machinePrefix + str(i+1) + ':' + resultDir,  localResultDir])
   
def start_clients(conf):
    numClients = conf["numUsers"]
    numVideos = conf['numUsers'] * 2 
    if conf['bench2'] == 'yes':
        numVideos = 1
    print('numVideos =', numVideos, conf['bench2'])
    clientTrajectories = conf['trajectoriesDir']
    edgeInfo = conf['edgeInfoFile']
    outputFile = conf['outputDir'] + "/" + str(numClients) + 'users' + str(conf['numEdgeNodes']) + 'nodes' + str(round(time.time() * 1000)) + '.csv'
    segmentFile = conf['segmentFile']
    cloudServer = conf['cloudServerName']
    bench2 = conf['bench2']
    result = subprocess.run(['ssh', cloudServer, ' export PATH=$PATH:/usr/local/go/bin && cd clairvoyant2/src/clientrunner_go &&  go run . ' +\
                            '-log_dir=\".\"'+\
                            ' -t ' + clientTrajectories + \
                            ' -i ' + str(numVideos) + \
                            ' -n ' + str(numClients) + \
                            ' -o ' + outputFile +\
                            ' -e ' + edgeInfo + \
                            ' -f ' + segmentFile +\
                            ' -b ' + bench2], \
                            shell=False,\
                            check=False)
    print('client success=', result.returncode)

def main():
    conf = read_config(sys.argv[1])
    resultDir = sys.argv[2]
    #example conf script in eval folder 10node_conf.json
    num_trials = conf['numTrials']
    start = time.time()
    repopulate_db = 'yes'
    for i in range(num_trials):
        start_cloud(conf, repopulate_db)
        if repopulate_db == 'yes':
            repopulate_db = 'no'
        start_edge(conf)
        time.sleep(10)
        start_clients(conf)
        gather_results(conf, resultDir)
    end = time.time()
    print(num_trials, " trials took ", (end-start), " seconds")
    stop_edge(conf)
if __name__=='__main__':
    main()