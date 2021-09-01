import threading
import time
import copy
import logging

class QueueData:
    def __init__(self, segment, sourceSpeed, source):
        self.segment = segment
        self.timestamp = time.time_ns()/1e6 # millis
        self.sourceSpeed = sourceSpeed
        self.source = source
class EdgeDownloadQueue:
    def __init__(self, timeScale, metadataManager):
        self.timeScale  = timeScale
        self.mutex = threading.Lock()
        self.pending = []
        logging.basicConfig(level=logging.INFO)
        self.metadataManager = metadataManager

    def enqueue(self, segment, sourceSpeed, source):
        dlTime = (segment.segment_size * 8 ) / (sourceSpeed * self.timeScale)
        self.mutex.acquire()
        try:
            self.pending.append(QueueData(segment, sourceSpeed, source))
        finally:
            self.mutex.release()

    def dequeue(self):
        self.mutex.acquire()
        completed = []
        newPending = []
        try:
            now = time.time_ns() / (1e6 * self.timeScale)
            
            for i in range(len(self.pending)):
                qData = self.pending[i]
                dlTime = (((qData.segment.segment_size * 8) /self.timeScale) / (qData.sourceSpeed))/self.timeScale 
                #if qData.timestamp/self.timeScale + dlTime <= now:
                if True:
                    if not self.metadataManager.hasSegment(qData.segment.segment_id):
                        self.metadataManager.addSegment({'segment':qData.segment, 'source_ip':qData.source})
                    completed.append(copy.deepcopy(self.pending[i]))
                    #print('compltedt:', i, 'dl deadline', dlTime + qData.timestamp/self.timeScale, 'now', now)
                
                else:
                    newPending.append(copy.deepcopy(self.pending[i]))
                    #print('pending:', i, 'dl deadline', dlTime + qData.timestamp/self.timeScale, 'now', now)
            self.pending = newPending
            logging.info('now have ' + str(len(self.pending)) + ' in pending list') 
        finally:
            self.mutex.release()
        return completed   
                     
    
