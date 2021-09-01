

from threading import Thread, Event
import csv, json, argparse
import signal, sys
import logging
import random
import requests


if __name__ == "__main__":
    from os import path
    sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from shared.EdgeNetworkModel import EdgeNetworkModel

logging.basicConfig()
logger = logging.getLogger("monitoring")
#logger.setLevel(logging.WARNING)


class MonitoringClient(Thread):
    """
    Needs to send model updates, and connected client information(?). 
    More stuff can be sent based on what's needed.
    Currently sends model updates.

    """
    def __init__(self, model_file, interval, address, node_id):
        self.model_dict = self.parse_model_file(model_file)
        self.interval = interval
        self.url = 'http://{}'.format(address)
        self.stopped = Event()
        self.node_id = node_id
        Thread.__init__(self)
        

    def parse_model_file(self, model_file):
        model_dict = {} # dist -> throughput, std dev
        with open(model_file) as fh:
            reader = csv.reader(fh, delimiter=',')
            for row in reader:
                model_dict[row[0]] = {"mean":float(row[1]), "sdev":float(row[2])}

        return model_dict


        
    def run(self):
        while not self.stopped.wait(self.interval):
            dict_to_send = {}
            for key,value in self.model_dict.items():
                dict_to_send[key] = value['mean'] + random.uniform(-value['sdev'], value['sdev'])

            payload = {}
            payload['nodeid'] = self.node_id
            payload['model'] = dict_to_send

            r = requests.post(self.url, json=payload)
            logger.debug("POST response: {}".format(r.status_code))
            logger.debug("Run mon every {} seconds".format(self.interval))

            

    def stop(self):
        self.stopped.set()

def service_shutdown(signal, frame):
    logger.warning("Aborting service")
    raise Exception

if __name__ == "__main__":
    
    #logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)
    parser = argparse.ArgumentParser(description="Run Monitoring Client") 
    parser.add_argument(
        "-a",
        "--address",
        default="localhost:8192",
        help="Specify the IP:Port on which the server listens",
    )
    parser.add_argument(
        "-t",
        "--interval",
        type=int,
        default=5,
        help="Monitoring interval (in seconds)",
    )
    parser.add_argument(
        "-m",
        "--modelfile",
        required=True,
        help="Fullpath filename for Model",
    )

    args = parser.parse_args()

    modelfile = path.abspath(args.modelfile)
    logger.debug("Modelfile : {}".format(modelfile))
    mon_client = MonitoringClient(modelfile, args.interval, args.address)
    mon_client.start()
    try:
        mon_client.join()
    except Exception:
        mon_client.stop()
        logging.shutdown()

