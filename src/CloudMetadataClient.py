import logging
import asyncio
import grpc
import time

import clairvoyant_pb2
import clairvoyant_meta_pb2
import clairvoyant_meta_pb2_grpc

class CloudMetadataClient:
    def __init__(self, address):
        self.address = address

    def processNearestNodesResponse(self, response, route):
        nodeInfo = clairvoyant_meta_pb2.NodeInfo()
        nodeInfo.CopyFrom(response.getNearestNodesResponse.nodes[0])
           
        cvNodeInfos = []
        cvNodeInfo = clairvoyant_pb2.NodeInfo()
        cvNodeInfo.node_ip = nodeInfo.address
        cvNodeInfo.node_id = nodeInfo.nodeId
        pt = cvNodeInfo.contact_points.add()
        pt.CopyFrom(route.points[0])
        cvNodeInfo.arrival_time = pt.time
        cvNodeInfo.contact_time = 0
        for i in range(1, len(response.getNearestNodesResponse.nodes)):
            curnode = response.getNearestNodesResponse.nodes[i]
            pt = clairvoyant_pb2.Coordinate()
            pt.CopyFrom(route.points[i])
            pt.distance = curnode.distance

            if curnode.nodeId == nodeInfo.nodeId:
                cvNodeInfo.contact_time += route.points[i].time - route.points[i-1].time
                cvpt = cvNodeInfo.contact_points.add()
                cvpt.CopyFrom(pt)
                print('copied 1 pt')
            else:
                if cvNodeInfo.nodeId != '' and cvNodeInfo.nodeId != None:
                    cvNodeInfos.append(cvNodeInfo)
                cvNodeInfo = clairvoyant_pb2.NodeInfo()
                cvNodeInfo.node_ip = curnode.address
                cvNodeInfo.node_id = curnode.nodeId
                cvNodeInfo.arrival_time = pt.time
                cvpt = cvNodeInfo.contact_points.add()
                cvpt.CopyFrom(pt)
                cvNodeInfo.contact_time = 0
                nodeInfo.CopyFrom(curnode)
        if (len(cvNodeInfos) > 0 and cvNodeInfo.node_id != cvNodeInfos[-1].node_id) or (cvNodeInfo.node_id != '' and len(cvNodeInfos) == 0):
            cvNodeInfos.append(cvNodeInfo)
        return cvNodeInfos
    
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
 
            print('request has ', len(nearestNodesReq.positions), ' points')
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
