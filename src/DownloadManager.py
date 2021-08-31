import asyncio
from EdgeDownloadAssignment import EdgeDownloadAssignment, SegmentInfo
import bisect
from EdgeNetworkModel import EdgeNetworkModel
import logging
import clairvoyant_pb2
from DownloadDispatcher import DownloadDispatcher
import time
class DownloadManager:
    def __init__(self, node_ids, downloadSources, timeScale, mmWaveModels, dispatcher):
        self.downloadSources = downloadSources
        self.mmWaveModels = mmWaveModels
        self.edgeNodeAssignments = {node_id: EdgeDownloadAssignment(node_id, downloadSources[node_id], timeScale) for node_id in node_ids}
        self.timeScale = timeScale
        self.dispatcher = dispatcher    
        logging.basicConfig(level=logging.INFO)
        self.routeInfos = {}
        
    def findOptimalSource(self, node_id):
        return 'http://ftp.itec.aau.at/DASHDataset2014'

    def getMeanDownloadSpeed(self, node_id, contact_points, contact_time):
        model = self.mmWaveModels[node_id]
        dl_map = model.get()
        if model is None:
            print('model is None')
        print(dl_map)
        distances = sorted(list(dl_map.keys()))
        totalBits = 0

        for point in contact_points:
            distance_idx = bisect.bisect_left(distances, point.distance)
            print('dust idx = ', distance_idx, 'distances len', len(distances))
            distance = distances[min(distance_idx, len(distances)-1)]
            dlSpeed = dl_map[distance]
            totalBits += (point.time * dlSpeed) / (self.timeScale )

        return totalBits / (contact_time)

    def assignDownload(self, node_id, deadline, segment, source):
        source = self.findOptimalSource(node_id)
        candidate = SegmentInfo()
        candidate.segment = segment
        candidate.source = source
        if self.edgeNodeAssignments[node_id].isDownloadPossible(deadline, candidate):
            self.edgeNodeAssignments[node_id].addSegmentForDownload(candidate)
            return True
        return False


    def getDownloadAssignment(self, segments, nodeInfos, token_id):
        segmentIdx = 0
        assignments = {}
        if nodeInfos == None:
            print('nodeInfos is empty')
            return assignments
        self.routeInfos[token_id] = nodeInfos
        print('got token ', token_id)
        for node in nodeInfos:
            if node.node_id not in self.mmWaveModels:
                continue
            if segmentIdx == len(segments):
                break
            dlSpeed = self.getMeanDownloadSpeed(node.node_id, node.contact_points, node.contact_time)
            availableContactTime = node.contact_time
            assignments[node.node_id] = []
            print(node.node_id, availableContactTime, node.arrival_time)
            for i in range(segmentIdx, len(segments)):
                segmentIdx = i
                if availableContactTime <= 0:
                    break
                source = self.findOptimalSource(node.node_id)
                if self.edgeNodeAssignments[node.node_id].hasSegment(segments[segmentIdx].segment_id) or self.assignDownload(node.node_id, node.arrival_time + node.contact_time, segments[segmentIdx], source):
                    candidate = SegmentInfo()
                    candidate.segment = segments[segmentIdx]
                    candidate.source = source
                    candidate.arrival_time = node.arrival_time
                    assignments[node.node_id].append(candidate)
                    availableContactTime -= (segments[segmentIdx].segment_size * 8 )/ (dlSpeed  * self.timeScale)
                    #print('seg', segmentIdx, ' contact left', availableContactTime, 'seg id ', segments[segmentIdx].segment_id)
                else:
                    logging.info('assigned ' + str(len(assignments[node.node_id])) + ' segments to ' + node.node_id)
                    break
            return assignments

    def sendAssignments(self, assignments, token_id):
        
        for node_id in assignments:
            segments = [candidate.segment for candidate in assignments[node_id]]
            sources = {candidate.segment.segment_id: candidate.source for candidate in assignments[node_id]}
                
            if len(segments) == 0:
                continue
            response = self.dispatcher.makeRequest(token_id, node_id, segments, sources, assignments[node_id][0].arrival_time) 
          
    def handleMissedDelivery(self, token_id, node_id, segments):
        if token_id not in self.routeInfos:
            print('no such route ', token_id)
        nodeInfos = self.routeInfos[token_id]
        idx = 0
        for node in nodeInfos:
            if node.node_id == node_id:
                break
            idx += 1
        if len(nodeInfos) > idx + 1 and nodeInfos[idx+1].node_id in self.mmWaveModels:
            nodeInfo = nodeInfos[idx+1]
            assignments = self.getDownloadAssignment(segments, [nodeInfo], token_id)
            self.sendAssignments(assignments, token_id)

    def handleVideoRequest(self, token_id, segments, nodeInfos):
        assignments = self.getDownloadAssignment(segments, nodeInfos, token_id)
        print(assignments)
        self.sendAssignments(assignments, token_id)
        return assignments
        #for node_id in assignments:
        #    segments = [candidate.segment for candidate in assignments[node_id]]
        #    sources = {candidate.segment.segment_id: candidate.source for candidate in assignments[node_id]}
        #        
        #    if len(segments) == 0:
        #        continue
        #    response = self.dispatcher.makeRequest(token_id, node_id, segments, sources) 
        #return assignments
  
     
    def updateDownloads(self, node_id, segment_ids):
        for segment in segment_ids:
            self.edgeNodeAssignments[node_id].removeCompletedSegment(segment)

           
#if __name__ == '__main__':
#    logging.basicConfig()
#    #segment_sources = {'1':'0.0.0.0:8000'}
#    dispatcher = DownloadDispatcher({'0':'0.0.0.0:50056'}, None)
#    segments = []
#    nodeInfo = clairvoyant_pb2.NodeInfo()
#    nodeInfo.node_id = '0'
#    nodeInfo.node_ip = '0.0.0.0:50056'
#    nodeInfo.arrival_time = time.time_ns() / 1e9 + 100
#    nodeInfo.contact_time = 3
#    for i in range(3):
#        point = nodeInfo.contact_points.add()
#        point.distance = 10
#        point.time = 1
#    nodeInfos = [nodeInfo]
#    for i  in range(2):
#        segment = clairvoyant_pb2.Segment()
#        segment.segment_id = str(i)
#        segment.segment_size = int(1e9)
#        segment.segment_name = '1'
#        segments.append(segment)
#    dlManager = DownloadManager(['0'], { '0':{'http://ftp.itec.aau.at/DASHDataset2014':100000000}}, 10,  {'0':EdgeNetworkModel()}, dispatcher) 
#    dlManager.handleVideoRequest(1, segments, nodeInfos)
