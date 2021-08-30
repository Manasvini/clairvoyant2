class EdgeNetworkModel:

    def __init__(self):
        self.node_id = None
        self.nw_dict = {} # {dist: throughput (bps) }
        self.timestamp = None # indication of how recent it is.
        self.mutex = None # lock it before updating nw_dict

    def update(self): #uses the mutex for proper nw_dict update
        pass

    def get(self): #uses the mutex for getting proper nw_dict
        print('got')
        return {10:500000000}



