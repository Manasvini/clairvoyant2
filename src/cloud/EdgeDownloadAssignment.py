import threading
import time
import copy
import logging

parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('edassignment')
logger.setLevel(logging.INFO)

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
        self.max_dlc_time = 0
    def hasSegment(self, segment_id):
        return segment_id in self.downloadedSegments

    """
    Note: the add function is cloud executive. i.e. doesn't need to talk to edge to know
    about it. This could change to have it ask edge node about its willingness to download
    segments (potentially more than 1)
    """
    def add(self, candidate, request_timestamp):
        #NOTE: deadline is the arrival time of the vehicle at the candidate

        add_success = False
        self.mutex.acquire()

        #prune stale assignments. TODO: explore if periodically pruning is better
        #max_dlc_time = request_timestamp
        if self.max_dlc_time == None:
            # HACK: sets earliest time to first request's time - 100 (that's what clientrunner is doing)
            # TODO should be querying clock instead
            self.max_dlc_time = request_timestamp - 100
        max_dlc_time = self.max_dlc_time

        for seg_id in list(self.assignments.keys()):
            seg_info = self.assignments[seg_id]
            if seg_info.expected_dlc_time < request_timestamp:
                self.downloadedSegments.add(seg_id)
                del self.assignments[seg_id]
            else:
                max_dlc_time = max(max_dlc_time, seg_info.expected_dlc_time)

        segmentTime = (candidate.segment.segment_size * 8.0) / self.downloadSourceSpeeds[candidate.source]
        if max_dlc_time + segmentTime < candidate.arrival_time:
            logger.debug("segment {} meets deadline {}. Will complete by {}".format(candidate.segment.segment_id, candidate.arrival_time, max_dlc_time+segmentTime))
            candidate.expected_dlc_time = max_dlc_time + segmentTime
            self.assignments[candidate.segment.segment_id] = candidate
            add_success = True
            self.max_dlc_time = max_dlc_time + segmentTime
        self.mutex.release()

        return add_success

    def isDownloadPossible(self, deadline, candidates):
        self.mutex.acquire()
        latest_start_time = 0 
        possibleCandidates = []
        for seg_id in list(self.assignments.keys()):
            seg_info = self.assignments[seg_id]
            if seg_info.expected_dlc_time < deadline:
                 latest_start_time = max(latest_start_time, seg_info.expected_dlc_time)
        
        for candidate in candidates:
            segmentTime = (candidate.segment.segment_size * 8.0) / self.downloadSourceSpeeds[candidate.source]
            if latest_start_time + segmentTime < candidate.arrival_time:
                logger.debug(f'segment {candidate.segment.segment_id} will download by {latest_start_time + segmentTime}')
                possibleCandidates.append(candidate)
                latest_start_time += segmentTime
            else:
                break
        self.mutex.release()
        return possibleCandidates

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

