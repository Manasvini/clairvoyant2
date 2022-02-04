import threading
import time
import copy
import logging

parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('edassignment')
logger.setLevel(logging.DEBUG)

class SegmentInfo:
    def __init__(self):
        self.segment = None
        self.source = None
        self.arrival_time = None
        self.contact_time = None
        self.expected_dlc_time = None
        self.is_last = False

class EdgeDownloadAssignment:
    def __init__(self, node_id, downloadSources, timeScale):
        self.assignments = {}
        self.downloadSourceSpeeds = downloadSources
        self.mutex = threading.Lock()
        self.timeScale = timeScale
        self.downloadedSegments = set()  
        self.node_id = node_id    

    def hasSegment(self, segment_id):
        return segment_id in self.downloadedSegments

    """
    Note: the add function is cloud executive. i.e. doesn't need to talk to edge to know
    about it. This could change to have it ask edge node about it's willingness to download
    segments (potentially more than 1)
    """
    def add(self, candidate, request_timestamp):
        #NOTE: deadline is the arrival time of the vehicle at the candidate

        add_success = False
        self.mutex.acquire()

        #prune stale assignments. TODO: explore if periodically pruning is better
        max_dlc_time = request_timestamp 

        for seg_id in list(self.assignments.keys()):
            seg_info = self.assignments[seg_id]
            if seg_info.expected_dlc_time < request_timestamp:
                self.downloadedSegments.add(seg_id)
                del self.assignments[seg_id]
            else:
                max_dlc_time = max(max_dlc_time, seg_info.expected_dlc_time)

        segmentTime = (candidate.segment.segment_size * 8.0) / self.downloadSourceSpeeds[candidate.source]
        if max_dlc_time + segmentTime < candidate.arrival_time:
            logger.debug("segment {} meets deadline".format(candidate.segment.segment_id))
            candidate.expected_dlc_time = max_dlc_time + segmentTime
            self.assignments[candidate.segment.segment_id] = candidate
            add_success = True

        self.mutex.release()

        return add_success

    def isDownloadPossible(self, deadline, candidate):
        self.mutex.acquire()
        bytesInProgress = 0 
        #TODO: use sumo time to see if download is possible
        now = time.time_ns() / 1e9 #this should refer to when node is free to download
        totalTime = 0
        segmentTime = ((candidate.segment.segment_size) * 8.0) / (self.downloadSourceSpeeds[candidate.source] )
        #print(candidate.segment.segment_id, segmentTime)
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
                logger.info('edge node ' + self.node_id+ ' has' + str(len(self.assignments))+ ' in progress')
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

