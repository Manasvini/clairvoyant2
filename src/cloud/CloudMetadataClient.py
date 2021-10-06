import logging
import asyncio
import grpc
import time

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_meta_pb2 as clairvoyant_meta_pb2
import genprotos.clairvoyant_meta_pb2_grpc as clairvoyant_meta_pb2_grpc

parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('metadata')
logger.setLevel(logging.DEBUG)

class CloudMetadataClient:
    def __init__(self, address):
        self.address = address

    def processNearestNodesResponse(self, response, route):
        node_dict = {}
        idx = 0
        lastnode = -1

        """
        The following iterates over the response points, and determines \
        the intervals(start,end) of points which had an edge node as neighbor.
        """
        for idx in range(len(response.getNearestNodesResponse.nodes)):
            curInfo = response.getNearestNodesResponse.nodes[idx]
            curnode = curInfo.nodeId

            if lastnode != -1 and curnode != lastnode:
                node_dict[lastnode]["track"] = False
                lastnode = -1

            if curnode:
                if curnode not in node_dict:
                    node_dict[curnode] = {}
                    node_dict[curnode]["track"] = False
                    node_dict[curnode]["idxs"] = []

                if not node_dict[curnode]["track"]:
                    node_dict[curnode]["track"] = True
                    node_dict[curnode]["idxs"].append([idx,-1])

                if node_dict[curnode]["track"]:
                    node_dict[curnode]["idxs"][-1][1] = idx

                lastnode = curnode

                
        idxs = []
        for node, value in node_dict.items():
            idxs.extend(value["idxs"])

        sorted_idxs = list( sorted( idxs, key=lambda x : x[0]) )
        cvNodeInfos = []

        # HACK: to merge idxs for same node in succession
        merged_idxs = []
        lastnode = -1
        for idx in sorted_idxs:
            curnode = response.getNearestNodesResponse.nodes[idx[0]].nodeId
            if lastnode == curnode:
                merged_idxs[-1][1] = idx[1]
            else:
                merged_idxs.append(idx)
            lastnode = curnode
        sorted_idxs = merged_idxs
        # HACK:END

        for idx in sorted_idxs:
            node = response.getNearestNodesResponse.nodes[idx[0]]
            cvNodeInfo = clairvoyant_pb2.NodeInfo()
            cvNodeInfo.node_ip = node.address
            cvNodeInfo.node_id = node.nodeId
            start = idx[0]
            end = idx[1]
            cvNodeInfo.arrival_time = route.points[start].time
            cvNodeInfo.contact_time = route.points[end].time - route.points[start].time
            while start <= end:
                pt = cvNodeInfo.contact_points.add()
                pt.CopyFrom(route.points[start])
                pt.distance = response.getNearestNodesResponse.nodes[start].distance
                start += 1
            cvNodeInfos.append(cvNodeInfo)

        return cvNodeInfos

    #def processNearestNodesResponse(self, response, route):
    #    nodeInfo = clairvoyant_meta_pb2.NodeInfo()
    #    nodeInfo.CopyFrom(response.getNearestNodesResponse.nodes[0])
    #       
    #    cvNodeInfos = []
    #    cvNodeInfo = clairvoyant_pb2.NodeInfo()
    #    cvNodeInfo.node_ip = nodeInfo.address
    #    cvNodeInfo.node_id = nodeInfo.nodeId
    #    pt = cvNodeInfo.contact_points.add()
    #    pt.CopyFrom(route.points[0])
    #    cvNodeInfo.arrival_time = pt.time
    #    cvNodeInfo.contact_time = 0

    #    for i in range(1, len(response.getNearestNodesResponse.nodes)):
    #        curnode = response.getNearestNodesResponse.nodes[i]
    #        pt = clairvoyant_pb2.Coordinate()
    #        pt.CopyFrom(route.points[i])
    #        pt.distance = curnode.distance
    #        
    #        if curnode.nodeId == nodeInfo.nodeId:
    #            cvNodeInfo.contact_time += route.points[i].time - route.points[i-1].time
    #            cvpt = cvNodeInfo.contact_points.add()
    #            cvpt.CopyFrom(pt)
    #        else:
    #            if cvNodeInfo.node_id != '' and cvNodeInfo.node_id != None:
    #                cvNodeInfo.contact_time = cvNodeInfo.contact_points[-1].time - \
    #                        cvNodeInfo.contact_points[0].time
    #                print('node ', cvNodeInfo.node_id, 'contact = ', cvNodeInfo.contact_time, cvNodeInfo.contact_points[0])
    #                cvNodeInfos.append(cvNodeInfo)
    #            cvNodeInfo = clairvoyant_pb2.NodeInfo()
    #            cvNodeInfo.node_ip = curnode.address
    #            cvNodeInfo.node_id = curnode.nodeId
    #            cvNodeInfo.arrival_time = pt.time
    #            cvpt = cvNodeInfo.contact_points.add()
    #            cvpt.CopyFrom(pt)
    #            cvNodeInfo.contact_time = 0
    #            nodeInfo.CopyFrom(curnode)

    #    if cvNodeInfo.node_id != '':
    #        if  len(cvNodeInfos) == 0 or \
    #                (cvNodeInfo.node_id != cvNodeInfos[-1].node_id):
    #            cvNodeInfos.append(cvNodeInfo)

    #    if len(cvNodeInfos) > 5:
    #        import pdb; pdb.set_trace()
    #    return cvNodeInfos
    
    def makeNearestNodesRequest(self, route):
        with grpc.insecure_channel(self.address) as channel:
            stub = clairvoyant_meta_pb2_grpc.MetadataServerStub(channel)
            request = clairvoyant_meta_pb2.Request()
            nearestNodesReq = clairvoyant_meta_pb2.GetNearestNodesRequest()
            for point in route.points:
                position = nearestNodesReq.positions.add()
                position.longitude = point.x
                position.latitude = point.y
            request.getNearestNodesRequest.CopyFrom(nearestNodesReq)
 
            logger.info(f"trajectory point count={len(nearestNodesReq.positions)}")
            response = stub.handleRequest(request)
            nodeInfos = self.processNearestNodesResponse(response, route)

            return nodeInfos

    def processVideoResponse(self, response, video_id):
        segments = []
        for segment in response.getVideoInfoResponse.video.segments:
            cvSegment  = clairvoyant_pb2.Segment()
            cvSegment.segment_id = segment.segmentId
            cvSegment.segment_size = segment.size
            cvSegment.segment_name = segment.segmentId
            segments.append(cvSegment)
        return segments

    def makeGetVideoInfoRequest(self, video_id):
        with grpc.insecure_channel(self.address) as channel:
            stub = clairvoyant_meta_pb2_grpc.MetadataServerStub(channel)
            request = clairvoyant_meta_pb2.Request()
            videoReq = clairvoyant_meta_pb2.GetVideoInfoRequest()
            videoReq.videoId = video_id
            request.getVideoInfoRequest.CopyFrom(videoReq)
            response = stub.handleRequest(request)
            segments = self.processVideoResponse(response, video_id)
            return segments
#if __name__ == '__main__':
#    logging.basicConfig()
#    client = CloudMetadataClient('localhost:50051')
#    route = clairvoyant_pb2.Route()
#    pts = [(7.48379, 43.765967), (7.4837299, 43.765964)]
#    ctr = time.time_ns()/1e9 + 100
#    for p in pts:
#        point = route.points.add()
#        point.x = p[0]
#        point.y = p[1]
#        point.time = ctr
#        ctr += 1
#    asyncio.run(client.makeNearestNodesRequest(route))
#
#    asyncio.run(client.makeGetVideoInfoRequest('v1'))
