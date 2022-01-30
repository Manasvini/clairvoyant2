import time
import logging
import bisect
import asyncio
import os
import csv

from enum import Enum

from cloud.EdgeDownloadAssignment import EdgeDownloadAssignment, SegmentInfo
from shared.EdgeNetworkModel import EdgeNetworkModel
from cloud.DownloadDispatcher import DownloadDispatcher
import genprotos.clairvoyant_pb2 as clairvoyant_pb2


parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('downloadmgr')
logger.setLevel(logging.WARNING)

class Bench2Mode(str, Enum):
    NOCACHE = "nocache"             # everything from cdn
    LOCAL = "local"                 # reusing cache for local routes
    ALL2ALL = "all2all"             # use cache of every node in system
    CUR_ROUTE_NBR = "curRouteNbr"   # only use cache of all nodes on cur route, theoretically not 
                                    # possible, since you can't know what are nodes, 
                                    # until you finish atomic "add" 
    ALL_ROUTE_NBR = "allRouteNbr"   # use cache of every node of all routes going through cur node
    

class DownloadManager:
    def __init__(self, 
            node_ids, 
            downloadSources, 
            timeScale,
            mmWaveModels, 
            dispatcher, 
            mode):
        self.downloadSources = downloadSources
        self.mmWaveModels = mmWaveModels
        self.edgeNodeAssignments = {node_id: EdgeDownloadAssignment(node_id, downloadSources[node_id], timeScale) for node_id in node_ids}
        self.dispatcher = dispatcher    
        self.routeInfos = {}
        self.phase3 = True
        self.max_client_per_node = 2

        self.segment_map = {} #seg_id -> node_id_set
        self.node_nbr_map = {} #node_id -> set of node neighbors so far
        if mode:
            self.mode = mode
        else:
            self.mode = Bench2Mode.NOCACHE
        self.node_segcount_map = {}

        filename = f'/home/cvuser/clairvoyant2/results/bench2/{self.mode}_results.csv'
        with open(filename, 'w') as fh:
            csvwriter = csv.writer(fh, delimiter=',')
            csvwriter.writerow(['user_id', 'cdn', 'edge', 'local'])
        
    def findOptimalSource(self, segment_id, node_id, neighbors=None):
        return 'http://ftp.itec.aau.at/DASHDataset2014'

    def get_model_dist(self, dists, distance):
        print(dists, distance, type(distance))
        idx = bisect.bisect_left(dists, distance)
        logger.info('distance = %s idx = %s pts=%s', distance, idx, len(dists))
        if idx > len(dists) - 1:
            return dists[len(dists)-1]

        if idx != 0:
            if abs(distance - dists[idx]) < abs(distance - dists[idx-1]):
                return dists[idx]
            else:
                return dists[idx-1]
        else:
            return dists[idx]

    def getMeanDownloadSpeed(self, node_id, contact_points, contact_time):
        model = self.mmWaveModels[node_id]
        dl_map = model.get()
        if model is None:
            print('model is None')
        print(dl_map)
        distances = sorted(list(dl_map.keys()))
        totalBits = 0

        for point in contact_points:

            distance = self.get_model_dist(distances, point.distance)

            dlSpeed = dl_map[distance]
            totalBits += (point.time * dlSpeed)

        return totalBits / (contact_time)

        
    def has_overlap(self, curnode):
        #find overlapping routes
        overlap_route_node_infos = []
        count = 0
        for route, nodes in self.routeInfos.items():
            for node in nodes:
                end_time = node.arrival_time + node.contact_time
                start_time = node.arrival_time
                if curnode.arrival_time < end_time and \
                        (curnode.arrival_time + curnode.contact_time) > start_time:
                    count += 1
                    if count >= self.max_client_per_node:
                        logger.debug("scheduled max={count} clients. Can not use node")
                        return True

        return False




    def getDownloadBytes(self, node):
        #TODO: This function should account for overlap with another route
        # using the node at the same time

        node_id = node.node_id
        contact_points = node.contact_points
        model = self.mmWaveModels[node_id]
        logger.info("num models= %s ", len(self.mmWaveModels))
        dl_map = model.get()
        if model is None:
            logger.warning('Empty Model!')
        distances = sorted(list(dl_map.keys()))
        print(node.node_id, dl_map)
        totalBits = 0

        last_distance = -1
        time_of_last_distance = 0

        num_points = 0
        point_contact_time = 0

        #if node_id == 'node_5':
        #    import pdb; pdb.set_trace()

        for point in contact_points:
            logger.debug(f" node: {node_id} | contact point: ({point.x},{point.y}) | point dist: {point.distance}")
            num_points += 1
            distance = self.get_model_dist(distances, point.distance)

            if num_points == 1:
                last_distance = distance
                time_of_last_distance = point.time
            if distance != last_distance:
                point_contact_time = point.time - time_of_last_distance
                if point_contact_time == 0:
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

    def getDownloadAssignment(self, supposed_playback_start, segments, nodeInfos, token_id, request_timestamp):
        segmentIdx = 0

        if nodeInfos == None:
            logger.error("nodeInfos is empty")
            return assignments
        # we do this to handle same nodes from cropping up later in the route
        node_set = set([node.node_id for node in nodeInfos])
        assignments = {node_id:[] for node_id in node_set if node_id in self.mmWaveModels}
        

        self.routeInfos[token_id] = []

        effectiveNodeInfos = []
        for node in nodeInfos:
            if not self.has_overlap(node):
                effectiveNodeInfos.append(node)

        result = {}
        result["order"] = effectiveNodeInfos


        #advance segmentIdx to sufficiently close to supposed playback

        for node in effectiveNodeInfos:
            if node.node_id not in self.mmWaveModels:
                logger.debug("Node: {} - Model does not exist".format(node.node_id))
                continue

            if segmentIdx == len(segments):
                break

            # close approximation of assigning segments closer to playback
            playback = int(node.arrival_time - supposed_playback_start)
            if segmentIdx < playback:
                segmentIdx = playback
                logger.debug(f"node={node.node_id}, playback={supposed_playback_start}, arrival={node.arrival_time}, segidx={segmentIdx}")

            
            maxAvailDlBytes = self.getDownloadBytes(node) 
            logger.debug("Max avaliable bytes: {} | Node: {}".format(maxAvailDlBytes, node.node_id))

            assignedNode = False
            logger.debug(f"segmentIdx={segmentIdx}")
            sum_of_seg_sizes = 0
            while segmentIdx < len(segments):
                
                if maxAvailDlBytes < segments[segmentIdx].segment_size:
                    logger.debug(f"Not enough bytes available to deliver, sum of segments={sum_of_seg_sizes}")
                    break

                candidate = SegmentInfo()
                candidate.segment = segments[segmentIdx]
                candidate.source = self.findOptimalSource(candidate.segment.segment_id, node.node_id)
                candidate.arrival_time = node.arrival_time
                candidate.contact_time = node.contact_time

                if self.edgeNodeAssignments[node.node_id].add(candidate, request_timestamp):
                    assignments[node.node_id].append(candidate)
                    maxAvailDlBytes -= segments[segmentIdx].segment_size
                    sum_of_seg_sizes += segments[segmentIdx].segment_size
                    assignedNode = True
                else:
                    logger.debug("assignments aborted at segment {}, node={}"\
                            .format(segments[segmentIdx], node.node_id))
                    break
                segmentIdx += 1

            if assignedNode:
                self.routeInfos[token_id].append(node)


        logger.debug('Assignments:')
        for nodeInfo in self.routeInfos[token_id]:
            node = nodeInfo.node_id
            logger.debug("arrival={}, node:{}, num_segments:{}".format(nodeInfo.arrival_time, node,  len(assignments[node])))

        logger.info(f"routeInfos is tracking token={token_id}")

        #NOTE: simple matter of replacing findOptimalSource with this
        self.updateDownloadSources(token_id, assignments)

        result["assignments"] = assignments

        return result

    def updateDownloadSources(self, token_id, assignment_info_list):
        """
        purely from benchmark 2 perspective, this will output what segmemts are downloaded
        from where.
        """
        if self.mode == Bench2Mode.NOCACHE:
            return

        filename = f'/home/cvuser/clairvoyant2/results/bench2/{self.mode}_results.csv'

        assignments = {k:v for k,v in assignment_info_list.items() if len(v)}

        debug = open(f'debug_{self.mode}','a')

        with open(filename, 'a') as fh:
            csvwriter = csv.writer(fh, delimiter=',')
            cdn = 0
            edge = 0
            local = 0
            for node_id, seg_info_list in assignments.items():

                for seg_info in seg_info_list:
                    seg_id = seg_info.segment.segment_id
                    if seg_id in self.segment_map and node_id in self.segment_map[seg_id]:
                        local += seg_info.segment.segment_size
                    if self.mode == Bench2Mode.LOCAL:
                        if (seg_id in self.segment_map and
                                node_id in self.segment_map[seg_id]):
                            edge += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    elif self.mode == Bench2Mode.ALL2ALL:
                        if seg_id in self.segment_map:
                            edge += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    elif self.mode == Bench2Mode.CUR_ROUTE_NBR:
                        if seg_id in self.segment_map:
                            found_nbr = False
                            for node in list(assignments.keys()):
                                if node in self.segment_map[seg_id]:
                                    edge += seg_info.segment.segment_size
                                    found_nbr = True
                                    break

                            if not found_nbr:
                                cdn += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    elif self.mode == Bench2Mode.ALL_ROUTE_NBR:
                        if node_id not in self.node_nbr_map:
                            self.node_nbr_map[node_id] = set()
                        self.node_nbr_map[node_id].update(assignments.keys())

                        if seg_id in self.segment_map:
                            found_nbr = False

                            for node in self.node_nbr_map[node_id]:
                                if node in self.segment_map[seg_id]:
                                    edge += seg_info.segment.segment_size
                                    found_nbr = True
                                    break

                            if not found_nbr:
                                cdn += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    # In all cases you end up having the segment on the node
                    if seg_id not in self.segment_map:
                        self.segment_map[seg_id] = set()
                    self.segment_map[seg_id].add(node_id)

                    if node_id not in self.node_segcount_map:
                        self.node_segcount_map[node_id] = set()
                    self.node_segcount_map[node_id].add(seg_id)

            csvwriter.writerow([token_id, cdn, edge, local])
            out_dict = {k.split('_')[1]:len(v) for k,v in self.node_segcount_map.items()}
            ak = [k.split('_')[1] for k in assignments.keys()]
            debug.write(f"{str(out_dict)}, {ak}\n")



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
            logger.debug(f"route={token_id},  count={len(segments)} - MissedDelivery notification from last node")
            #TODO: clean up routeInfos on last segment notification
            return

        # Forward segments to next node alone
        segment_idx = 0
        new_assignments = {node.node_id:[] for node in nodeInfos[next_node_idx:]}

        node = nodeInfos[next_node_idx]
        while segment_idx < len(segments):
            candidate = SegmentInfo()
            candidate.segment = segments[segment_idx]
            candidate.source = self.findOptimalSource(candidate.segment.segment_id, node.node_id)
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

        self.sendAssignments(new_assignments, token_id)

    def handleVideoRequest(self, token_id, supposed_playback_start, segments, nodeInfos, request_timestamp):
        result = self.getDownloadAssignment(supposed_playback_start, segments, nodeInfos, token_id, request_timestamp)
        assignments = result["assignments"]
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
