import subprocess
import signal
import sys
import pathlib
import time


CWD = str(pathlib.Path.home()) + '/clairvoyant2'
#start time
def stop_edge():
    print("stop edge")
    eproc = subprocess.Popen(["bash", "run_scripts/stop_edge_bins.sh", "10"], cwd=CWD)
    eproc.communicate()

def start_edge():
    print("start edge")
    eproc = subprocess.Popen(["bash", "run_scripts/start_edge_bins.sh", "10"], cwd=CWD)
    eproc.communicate()

def start_clock():
    print("Start clock server")
    proc = subprocess.Popen(["python3", 'src/clock_runner.py', '-s', '0', '-i', '1'], cwd=CWD)
    return proc

def start_cloud():
    print("start cloud server")
    fh = open("cloudout.txt",'w')
    proc = subprocess.Popen(["python3",'src/cloud_runner.py',\
                           "-a", "0.0.0.0:60050",\
                           "-c", "conf/10node_monacoCloudConfig.json"],\
                          stderr=subprocess.STDOUT,\
                          stdout=fh,\
                          cwd=CWD)
    return proc

cloudproc = start_cloud()
clockproc = start_clock()
start_edge()
time.sleep(5)
print("Ready!")

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    clockproc.terminate()
    cloudproc.terminate()
    stop_edge()
    sys.exit(0) 

signal.signal(signal.SIGINT, signal_handler)
cloudproc.communicate()
