from threading import Lock
class EdgeNetworkModel:

    def __init__(self, node_id):
        self.node_id = node_id
        self.nw_dict = {} # {dist: throughput (bps) }
        self.timestamp = None # indication of how recent it is.
        self.mutex = Lock() # lock it before updating nw_dict

    def update(self, model_dict, ts): #uses the mutex for proper nw_dict update
        self.mutex.acquire()
        for key,value in model_dict.items():
            self.nw_dict[key] = value
        self.timestamp = ts
        self.mutex.release()


    def get(self): #uses the mutex for getting proper nw_dict
        tmp_dict = {}
        self.mutex.acquire()
        for key,value in self.nw_dict.items():
            tmp_dict[key] = self.nw_dict[key]

        self.mutex.release()
        return tmp_dict



