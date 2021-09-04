import time
import logging
import bisect
import asyncio

from cloud.EdgeDownloadAssignment import EdgeDownloadAssignment, SegmentInfo
from shared.EdgeNetworkModel import EdgeNetworkModel
from cloud.DownloadDispatcher import DownloadDispatcher
import genprotos.clairvoyant_pb2 as clairvoyant_pb2


logger = logging.getLogger("cloud")
logger.setLevel(logging.DEBUG)

class DownloadManager:
    def __init__(self, node_ids, downloadSources, timeScale, mmWaveModels, dispatcher):
        self.downloadSources = downloadSources
        self.mmWaveModels = mmWaveModels
        self.edgeNodeAssignments = {node_id: EdgeDownloadAssignment(node_id, downloadSources[node_id], timeScale) for node_id in node_ids}
        self.dispatcher = dispatcher    
        self.routeInfos = {}
        self.phase3 = True
        
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
            print('dist idx = ', distance_idx, 'distances len', len(distances))
            distance = distances[min(distance_idx, len(distances)-1)]
            dlSpeed = dl_map[distance]
            totalBits += (point.time * dlSpeed)

        return totalBits / (contact_time)

    def getDownloadBytes(self, node_id, contact_points):
        #TODO: This function should account for overlap with another route
        # using the node at the same time

        model = self.mmWaveModels[node_id]
        dl_map = model.get()
        if model is None:
            logger.warning('Empty Model!')
        distances = sorted(list(dl_map.keys()))
        totalBits = 0

        last_distance = -1
        time_of_last_distance = 0

        num_points = 0
        for point in contact_points:
            logger.debug(f" node: {node_id} | contact point: ({point.x},{point.y}) | point dist: {point.distance}")
            num_points += 1
            distance_idx = bisect.bisect_left(distances, point.distance)
            distance = distances[min(distance_idx, len(distances)-1)]
            if num_points == 1:
                last_distance = distance
                time_of_last_distance = point.time
            if distance != last_distance:
                point_contact_time = point.time - time_of_last_distance
                if point_contact_time == 1:
                    bits = dl_map[last_distance]
                else:
                    bits = (dl_map[last_distance]*point_contact_time)
                totalBits += bits
                logger.debug(f"Accumulate for dist={last_distance}, time={point_contact_time},speed={dl_map[last_distance]} bits={bits}")
                time_of_last_distance = point.time
                last_distance = distance

        if num_points:
            bits = dl_map[last_distance]
            totalBits += bits
            logger.debug(f"Accumulate for dist={last_distance}, time={point_contact_time},speed={dl_map[last_distance]} bits={bits}")
        else:
            logger.error("No contact points on node: {}".format(node_id))
        return totalBits / 8


    #def assignDownload(self, node_id, deadline, segment, source):
    #    source = self.findOptimalSource(node_id)
    #    candidate = SegmentInfo()
    #    candidate.segment = segment
    #    candidate.source = source
    #    if self.edgeNodeAssignments[node_id].isDownloadPossible(deadline, candidate):
    #        self.edgeNodeAssignments[node_id].addSegmentForDownload(candidate)
    #        return True
    #    return False



    def getDownloadAssignment(self, segments, nodeInfos, token_id, request_timestamp):
        segmentIdx = 0

        if nodeInfos == None:
            logger.error("nodeInfos is empty")
            return assignments
        # we do this to handle same nodes from cropping up later in the route
        node_set = set([node.node_id for node in nodeInfos])
        assignments = {node_id:[] for node_id in node_set if node_id in self.mmWaveModels}


        #required for phase3
        self.routeInfos[token_id] = []

        for node in nodeInfos:
            if node.node_id not in self.mmWaveModels:
                logger.debug("Node: {} - Model does not exist".format(node.node_id))
                continue

            if segmentIdx == len(segments):
                break

            maxAvailDlBytes = self.getDownloadBytes(node.node_id, node.contact_points) 
            logger.debug("Max avaliable bytes: {} | Node: {}".format(maxAvailDlBytes, node.node_id))

            assignedNode = False
            while segmentIdx < len(segments):
                
                if maxAvailDlBytes < segments[segmentIdx].segment_size:
                    logger.debug("Not enough bytes available to deliver")
                    break

                source = self.findOptimalSource(node.node_id)

                candidate = SegmentInfo()
                candidate.segment = segments[segmentIdx]
                candidate.source = source
                candidate.arrival_time = node.arrival_time
                candidate.contact_time = node.contact_time

                if self.edgeNodeAssignments[node.node_id].add(candidate, request_timestamp):
                    assignments[node.node_id].append(candidate)
                    maxAvailDlBytes -= segments[segmentIdx].segment_size
                    assignedNode = True
                else:
                    logger.debug("assignments aborted at segment {}, node={}"\
                            .format(segments[segmentIdx], node.node_id))
                    break
                segmentIdx += 1

            if assignedNode:
                self.routeInfos[token_id].append(node)

        if not self.phase3:
            self.routeInfos[token_id] = None
        else:
            logger.info(f"routeInfos is tracking token={token_id}")

        logger.debug('Assignments:')
        for node,value in assignments.items():
            logger.debug("node:{}, num_segments:{}".format(node,  len(value)))

        return assignments


    def sendAssignments(self, assignments, token_id):
        
        for node_id in assignments:
            segments = [candidate.segment for candidate in assignments[node_id]]
            sources = {candidate.segment.segment_id: \
                    candidate.source for candidate in assignments[node_id]}
                
            if len(segments) == 0:
                continue
            response = self.dispatcher.makeRequest(token_id, node_id, segments, sources,\
                    assignments[node_id][0].arrival_time, assignments[node_id][0].contact_time) 
          
    # For phase 3
    def handleMissedDelivery(self, token_id, node_id, segments, request_timestamp):
        if token_id not in self.routeInfos:
            logger.warning(f"route={token_id} not found!")
            return

        nodeInfos = self.routeInfos[token_id]
        next_node_idx = 0
        for node in nodeInfos:
            next_node_idx += 1
            if node.node_id == node_id:
                break

        if next_node_idx >= len(nodeInfos):
            logger.info(f" route={token_id} - Received MissedDelivery notification from last node")
            del self.routeInfos[token_id]
            return

        # Forward segments to next node alone
        segment_idx = 0
        new_assignments = {node.node_id:[] for node in nodeInfos[next_node_idx:]}

        node = nodeInfos[next_node_idx]
        while segment_idx < len(segments):
            candidate = SegmentInfo()
            candidate.segment = segments[segment_idx]
            candidate.source = source
            candidate.arrival_time = node.arrival_time
            candidate.contact_time = node.contact_time

            if self.edgeNodeAssignments[node.node_id].add(candidate, request_timestamp):
                new_assignments[node.node_id].append(candidate)
            else:
                logger.debug(f"phase3 - node={node.node_id}, segment_idx={segment_idx} failed")
                break
            segment_idx += 1

        if segment_idx < len(segments):
            logger.warning(f"phase3 - no assignments for {len(segments)-segment_idx} segments")

        self.sendAssignments(assignments, token_id)

    def handleVideoRequest(self, token_id, segments, nodeInfos, request_timestamp):
        assignments = self.getDownloadAssignment(segments, nodeInfos, token_id, request_timestamp)
        if assignments is None:
            raise ValueError('assignments is none')
        self.sendAssignments(assignments, token_id)
        return assignments
  
     
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
