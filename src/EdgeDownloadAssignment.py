import threading
import time
import copy
import logging
class SegmentInfo:
    def __init__(self):
        self.segment = None
        self.source = None
        self.contact_time = None

class EdgeDownloadAssignment:
    def __init__(self, node_id, downloadSources, timeScale):
        self.assignments = {}
        self.downloadSourceSpeeds = downloadSources
        self.mutex = threading.Lock()
        self.timeScale = timeScale
        self.downloadedSegments = {}
        self.node_id = node_id    
    def hasSegment(self, segment_id):
        return segment_id in self.downloadedSegments

    def isDownloadPossible(self, deadline, candidate):
        self.mutex.acquire()
        bytesInProgress = 0 
        now = time.time_ns() / 1e9
        totalTime = 0
        segmentTime = ((candidate.segment.segment_size/self.timeScale) * 8.0) / (self.downloadSourceSpeeds[candidate.source] )
        print(candidate.segment.segment_id, segmentTime)
        try:
            for ip_segment in self.assignments.values():
                if ip_segment.source in self.downloadSourceSpeeds:
                    speed = self.downloadSourceSpeeds[ip_segment.source]
                    segTime = ((ip_segment.segment.segment_size/self.timeScale) * 8.0) / speed
                    totalTime += segTime
                else:
                    raise ValueError('source ' + ip_segment.source + ' not found')
        finally:
            self.mutex.release()
        if (segmentTime + totalTime + now/self.timeScale)  < deadline:
            return True
        return False

    def addSegmentForDownload(self, candidate):
        self.mutex.acquire()
        try:
            if candidate.segment.segment_id not in self.assignments:
                self.assignments[candidate.segment.segment_id] = candidate
                #print('added to dl', candidate.segment.segment_id)
                logging.info('edge node ' + self.node_id+ ' has' + str(len(self.assignments))+ ' in progress')
        finally:
            self.mutex.release()
    
    def removeCompletedSegment(self, segment_id):
        self.mutex.acquire()
        try:
            if segment_id in self.assignments:
                self.downloadedSegments[segment_id] = copy.deepcopy(self.assignments[segment_id])
                self.assignments.pop(segment_id)
        finally:
            self.mutex.release()

