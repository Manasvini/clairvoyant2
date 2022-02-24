import time
import logging
import bisect
import asyncio
import os
import csv
import random

from enum import Enum

from cloud.EdgeDownloadAssignment import EdgeDownloadAssignment, SegmentInfo
from shared.EdgeNetworkModel import EdgeNetworkModel
from cloud.DownloadDispatcher import DownloadDispatcher
import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

from threading import Thread, Lock


parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('downloadmgr')
logger.setLevel(logging.INFO)

class Bench2Mode(str, Enum):
    NOCACHE = "nocache"             # everything from cdn
    LOCAL = "local"                 # reusing cache for local routes
    ALL2ALL = "all2all"             # use cache of every node in system
    CUR_ROUTE_NBR = "curRouteNbr"   # only use cache of all nodes on cur route, theoretically not 
                                    # possible, since you can't know what are nodes, 
                                    # until you finish atomic "add" 
    ALL_ROUTE_NBR = "allRouteNbr"   # use cache of every node of all routes going through cur node

class BookKeepingMode(str, Enum):
    '''NOTE: both these approaches to bookkeeping by the cloud are best effort. After all, an edge node A could evict a segment JUST after the cloud has informed another edge node B that B could fetch that exact segment from A's cache. This will happen with either policy, so the bookkeeping is just an optimization in the face of the vagaries of caching'''
    TRACKING = 'tracking'           # Cloud tracks evictions happening at the edge
    RECENT   = 'recent'             # Cloud only keeps track of the most recent assignment which it knows from an edge node's commitment to downloading the segment
   
class Oracle:
    def __init__(self, mode):
        self.mode = mode
        self.mutex = Lock() #for controlling state of segment_map and node_nbr_map
        self.segment_map = {} #seg_id -> node_id_set
        self.node_nbr_map = {} #node_id -> set of node neighbors so far

    def update(self, node_id, response):
        if len(response.segment_ids) == 0:
            logger.debug("No evictions. nothing to do")
            return

        logger.debug("Received evicted segments. Updating State")
        self.mutex.acquire()
        for seg_id in response.segment_ids:
            self.remove(node_id, seg_id)
        self.mutex.release()

    def remove(self, node_id, seg_id):
        if seg_id in self.segment_map:
            self.segment_map[seg_id].remove(node_id)

    def set_seg_source(self, node_id, seg_id):
        self.mutex.acquire()
        logger.debug(f"Updated source for segment {seg_id} to {node_id}")
        self.segment_map[seg_id] = set([node_id])
        self.mutex.release()

    def findOptimalSourceNode(self, seg_id, node_id, neighbors):
        self.mutex.acquire()
        src_node = None
        #logger.info(neighbors)
        #logger.info(f"oracle: {seg_id}, {node_id}")
        # set initializations
        
        if seg_id not in self.segment_map:
            self.segment_map[seg_id] = set()

        if node_id not in self.node_nbr_map:
            self.node_nbr_map[node_id] = set()
       
        # main logic
        if node_id in self.segment_map[seg_id]:
            logger.info(f"assumed {seg_id} to exist in local cache of {node_id}")
            src_node = node_id

        elif self.mode == Bench2Mode.LOCAL:
            src_node = node_id

        elif self.mode == Bench2Mode.ALL2ALL:
            if self.segment_map[seg_id]:
                src_nodes = self.segment_map[seg_id]
                #logger.info(f"all2all segids={src_nodes}")
                if len(src_nodes)> 1:
                    src_node = random.choice(list(src_nodes))
                else:
                    src_node = list(src_nodes)[0]
        elif self.mode == Bench2Mode.CUR_ROUTE_NBR:
            src_nodes = []
            for node in neighbors:
                if node in self.segment_map[seg_id]:
                    src_nodes.append(node)
            if src_nodes:
                src_node = random.choice(src_nodes)
                
        elif self.mode == Bench2Mode.ALL_ROUTE_NBR:
            self.node_nbr_map[node_id].update(neighbors)
            src_nodes = []
            for node in self.node_nbr_map[node_id]:
                if node in self.segment_map[seg_id]:
                    src_nodes.append(node)
            if src_nodes:
                src_node = random.choice(src_nodes)

        if src_node:
            logger.info("found a non cloud src={} for node={}".format(src_node, node_id))

        self.segment_map[seg_id].add(node_id)
        self.mutex.release()
        return src_node
    

class DownloadManager:
    def __init__(self, 
            node_ids, 
            downloadSources, 
            timeScale,
            mmWaveModels, 
            nodeDaemonIps, 
            nodeDownloadIps, 
            defaultSource,
            shareMode,
            bookKeeping,
            phase3):
        self.defaultSource = defaultSource
        self.downloadSources = downloadSources
        self.mmWaveModels = mmWaveModels
        self.edgeNodeAssignments = {node_id: EdgeDownloadAssignment(node_id, downloadSources[node_id], timeScale) for node_id in node_ids}
        self.nodeDownloadIps = nodeDownloadIps
        if shareMode:
            self.shareMode = shareMode
        else:
            self.shareMode = Bench2Mode.NOCACHE
        self.oracle = Oracle(shareMode)
        
        self.routeInfos = {}
        self.phase3 = phase3
        self.max_client_per_node = 2
        self.bookKeeping = bookKeeping
        self.node_segcount_map = {}

        dispatcherCb = None
        # if we keep track of evictions at the edge node, the edge node, on each request will respond with a list of segments it has evicted so that the oracle can appropriately update its view of the edge
        if self.bookKeeping == BookKeepingMode.TRACKING:
            dispatcherCb = self.oracle.update     
        
        self.dispatcher = DownloadDispatcher(nodeDaemonIps, dispatcherCb)
        
        filename = f'/home/cvuser/clairvoyant2/results/bench2/{self.shareMode}_results.csv'
        with open(filename, 'w') as fh:
            csvwriter = csv.writer(fh, delimiter=',')
            csvwriter.writerow(['user_id', 'cdn', 'edge', 'local'])
        

    def get_model_dist(self, dists, distance):
        logger.debug("{}, {}, {}".format(dists, distance, type(distance)))
        idx = bisect.bisect_left(dists, distance)
        logger.debug('distance={} idx={} pts={}'.format(distance, idx, len(dists)))
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
        #print(dl_map)
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
                    logger.debug(f"Node {curnode.node_id} serving {route}")
                    if count >= self.max_client_per_node:
                        logger.debug(f"scheduled max={count} clients. Can not use node")
                        return True

        return False




    def getDownloadBytes(self, node):
        #TODO: This function should account for overlap with another route
        # using the node at the same time

        node_id = node.node_id
        contact_points = node.contact_points
        model = self.mmWaveModels[node_id]
        logger.debug("num models={}".format(len(self.mmWaveModels)))
        dl_map = model.get()
        if model is None:
            logger.warning('Empty Model!')
        distances = sorted(list(dl_map.keys()))
        logger.debug(node.node_id, dl_map)
        totalBits = 0

        last_distance = -1
        time_of_last_distance = 0

        num_points = 0
        point_contact_time = 0

        #if node_id == 'node_5':
        #    import pdb; pdb.set_trace()
        bits = 0
        for point in contact_points:
            logger.debug(f" node: {node_id} | contact point: ({point.x},{point.y}) | point dist: {point.distance}, time={point.time}")
            num_points += 1
            distance = self.get_model_dist(distances, point.distance)

            if num_points == 1:
                last_distance = distance
                time_of_last_distance = point.time
            if point.time == time_of_last_distance:
                continue
            if distance != last_distance or point.time != time_of_last_distance:
                point_contact_time = point.time - time_of_last_distance
                #if point_contact_time == 0:
                #    bits = dl_map[last_distance]
                if point_contact_time > 0:
                    bits = (dl_map[last_distance]*point_contact_time)
                    totalBits += bits
                    logger.debug(f"Accumulate for dist={last_distance}, time={point.time},speed={dl_map[last_distance]} bits={bits}")
                time_of_last_distance = point.time
                last_distance = distance

        if num_points:
            bits = dl_map[last_distance]
            totalBits += bits
            logger.debug(f"Accumulate for dist={last_distance}, time={point_contact_time},speed={dl_map[last_distance]} bits={bits}")
        else:
            logger.error("No contact points on node: {}".format(node_id))
        logger.info(f"For node {node_id} total {totalBits/8} bytes can be downloaded")
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
            tentativeCandidates = []
            while segmentIdx < len(segments):
                
                if maxAvailDlBytes < segments[segmentIdx].segment_size:
                    logger.debug(f"Not enough bytes available to deliver, sum of segments={sum_of_seg_sizes}")
                    break

                candidate = SegmentInfo()
                candidate.segment = segments[segmentIdx]
                candidate.source = self.defaultSource
                src_node = self.oracle.findOptimalSourceNode(candidate.segment.segment_id, node.node_id,\
                                                          [node.node_id for node in effectiveNodeInfos])

                if src_node:
                    #import pdb; pdb.set_trace()
                    logger.info(f"source for segment {candidate.segment.segment_id} is {src_node}")
                    candidate.source = self.nodeDownloadIps[src_node]
        
                candidate.arrival_time = node.arrival_time
                candidate.contact_time = node.contact_time
                tentativeCandidates.append(candidate)
                maxAvailDlBytes -= segments[segmentIdx].segment_size 
                sum_of_seg_sizes += segments[segmentIdx].segment_size
                segmentIdx += 1
            if len(tentativeCandidates) == 0:
                continue
            # tentativeCandidates refers to the max no. of segments an edge node can deliver to the user within the user's contact time period. 
            #We still need to check the edge node's schedule to see if it has enogh bandwidth to download that many segments. 
            #If the backhaul links are busy, the edge node may not potentially be able to download all the tentative segments. This is reflected in possibleCandidates. Thus len(possibleCandidates) <= len(tentativeCandidates)  
            possibleCandidates = self.edgeNodeAssignments[node.node_id].isDownloadPossible(node.arrival_time, tentativeCandidates)
            logger.info(f"segmentIdx={segmentIdx} node id={node.node_id} can accept possibly {len(possibleCandidates)} out of {len(tentativeCandidates)} segments")
            if len(possibleCandidates) > 0:
                cur_assignments = {node.node_id:possibleCandidates}
                logger.info(f"sent assignments to node {node.node_id} for token {token_id}")

                # We send the assignments to the edge node and wait for its response. An edge node has limited storage and it could still be holding segments for other users who have not yet arrived, so it might not be able to make enough space for all the len(possibleCandidates) segments. 
                # So len(response.segment_ids) <= len(possibleCandidates)
                # When we update the oracle, we do so ONLY with the segments that the edge node has committed to downloading. 
                responses = self.sendAssignments(cur_assignments, token_id)
                logger.info(f"Got {len(responses)} responses, {len(responses[0].segment_ids)} accepted from node {node.node_id}")
                edgeAssignments = []
                if len(responses) > 0:
                    response = responses[0]
                    numAssignedSegments = len(response.segment_ids)
                    logger.debug(f"node id = {node.node_id} accepted {numAssignedSegments}, segmentIdx is at {segmentIdx}")
                    if numAssignedSegments > 0:
                        for i in range(numAssignedSegments):
                            
                            if self.edgeNodeAssignments[node.node_id].add(possibleCandidates[i], request_timestamp):
                                assignments[node.node_id].append(possibleCandidates[i])

                                # if we maintain record of only the most recent segment owner, we need to update the oracle with this info
                                if self.bookKeeping == BookKeepingMode.RECENT:
                                    self.oracle.set_seg_source(node.node_id, response.segment_ids[i])
                            else:
                                logger.warn(f"i= {i} edge and cloud states drifting. Node {node.node_id} accepted more segments than cloud is believing it to be able to handle")
                        segmentIdx -= (len(tentativeCandidates) - numAssignedSegments)
                        edgeAssignments = possibleCandidates[:numAssignedSegments]
                        logger.info(f"token = {token_id}, node={node.node_id} segmentidx= {segmentIdx}")
                    else:
                        segmentIdx -=len(tentativeCandidates)
                else:
                    segmentIdx -= len(tentativeCandidates)
                if len(edgeAssignments) > 0:
                    assignments[node.node_id] = edgeAssignments
                    self.routeInfos[token_id].append(node)
                #    assignedNode = True
                #else:
                #    logger.debug("assignments aborted at segment {}, node={}"\
                # 
            #if assignedNode:
            #    self.routeInfos[token_id].append(node)


        logger.info('Assignments:')
        for nodeInfo in self.routeInfos[token_id]:
            node = nodeInfo.node_id
            logger.info("arrival={}, node:{}, num_segments:{}".format(nodeInfo.arrival_time, node,  len(assignments[node])))

        logger.info(f"routeInfos is tracking token={token_id}")

        #NOTE: simple matter of replacing findOptimalSource with this
        #result["assignments"] = self.updateDownloadSources(token_id, assignments)
        result["assignments"] = assignments
        return result



    def updateDownloadSources(self, token_id, assignment_info_dict):
        """
        purely from benchmark 2 perspective, this will output what segmemts are downloaded
        from where.
        """
        if self.shareMode == Bench2Mode.NOCACHE:
            return

        filename = f'/home/cvuser/clairvoyant2/results/bench2/{self.shareMode}_results.csv'
        assignments = {k:v for k,v in assignment_info_dict.items() if len(v)}
        debug = open(f'debug_{self.shareMode}','a')

        default_src = 'http://ftp.itec.aau.at/DASHDataset2014/'
        src_node = None

        with open(filename, 'a') as fh:
            csvwriter = csv.writer(fh, delimiter=',')
            cdn = 0
            edge = 0
            local = 0
            for node_id, seg_info_list in assignments.items():

                for seg_info in seg_info_list:
                    seg_id = seg_info.segment.segment_id
                    
                    if seg_id not in self.segment_map:
                        self.segment_map[seg_id] = set()

                    if node_id in self.segment_map[seg_id]:
                        # NOTE: don't do anything if segment is available locally
                        local += seg_info.segment.segment_size
                        edge += seg_info.segment.segment_size

                    elif self.shareMode == Bench2Mode.ALL2ALL:
                        if self.segment_map[seg_id]:
                            edge += seg_info.segment.segment_size
                            src_nodes = self.segment_map[seg_id]
                            src_node = random.choice(src_nodes)
                        else:
                            cdn += seg_info.segment.segment_size

                    elif self.shareMode == Bench2Mode.CUR_ROUTE_NBR:
                        if self.segment_map[seg_id]:
                            src_nodes = []
                            for node in list(assignments.keys()):
                                if node in self.segment_map[seg_id]:
                                    src_nodes.append(node)
                            if src_nodes:
                                edge += seg_info.segment.segment_size
                                src_node = random.choice(src_nodes)
                            else:
                                cdn += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    elif self.shareMode == Bench2Mode.ALL_ROUTE_NBR:
                        if node_id not in self.node_nbr_map:
                            self.node_nbr_map[node_id] = set()

                        self.node_nbr_map[node_id].update(assignments.keys())

                        if self.segment_map[seg_id]:
                            src_nodes = []
                            for node in self.node_nbr_map[node_id]:
                                if node in self.segment_map[seg_id]:
                                    src_nodes.append(node)
                            if src_nodes:
                                edge += seg_info.segment.segment_size
                                src_node = random.choice(src_nodes)
                            else:
                                cdn += seg_info.segment.segment_size
                        else:
                            cdn += seg_info.segment.segment_size

                    # In all cases you end up having the segment on the node
                    self.segment_map[seg_id].add(node_id)

                    if node_id not in self.node_segcount_map:
                        self.node_segcount_map[node_id] = set()
                    self.node_segcount_map[node_id].add(seg_id)
                    
                    #update candidate sources
                    if src_node:
                        seg_info.source = self.nodeDownloadIps[src_node]
                    else:
                        seg_info.source = default_src

            csvwriter.writerow([token_id, cdn, edge, local])
            out_dict = {k.split('_')[1]:len(v) for k,v in self.node_segcount_map.items()}
            ak = [k.split('_')[1] for k in assignments.keys()]
            debug.write(f"{str(out_dict)}, {ak}\n")

        return assignments



    def sendAssignments(self, assignments, token_id):
        responses = [] 
        for node_id in assignments:
            segments = [candidate.segment for candidate in assignments[node_id]]
            sources = {candidate.segment.segment_id: \
                    candidate.source for candidate in assignments[node_id]}
                
            if len(segments) == 0:
                continue
            response = self.dispatcher.makeRequest(token_id, node_id, segments, sources,\
                    assignments[node_id][0].arrival_time, assignments[node_id][0].contact_time) 
            responses.append(response)
        return responses
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
        # not sure why this was being done. Replace with line "new_assignments = {node.node_id:[]}'
        # new_assignments = {node.node_id:[] for node in nodeInfos[next_node_idx:]}
        node = nodeInfos[next_node_idx]
        new_assignments = {node.node_id:[]}

        while segment_idx < len(segments):
            candidate = SegmentInfo()
            candidate.segment = segments[segment_idx]
            candidate.source = self.nodeDownloadIps[node_id]
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
        #import pdb; pdb.set_trace()
        #self.sendAssignments(assignments, token_id)
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
