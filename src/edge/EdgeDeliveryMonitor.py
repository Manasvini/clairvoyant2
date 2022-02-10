import schedule
import time
import logging

import grpc
import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc
import genprotos.clock_pb2 as clock_pb2
import genprotos.clock_pb2_grpc as clock_pb2_grpc

parent_logger = logging.getLogger("edge")
logger = parent_logger.getChild("deliverymonitory")
logger.setLevel(logging.WARNING)

class EdgeDeliveryMonitor:
    def __init__(self, timeScale, serverAddress, nodeId, intervalSeconds, metadataManager):
        self.serverAddress = serverAddress
        self.timeScale = timeScale
        self.metadataManager = metadataManager
        self.nodeId = nodeId
        self.intervalSeconds = intervalSeconds

        self.exitThread = False
        self.node_id = nodeId
        self.clockServerAddr = serverAddress.split(':')[0] + ":8383"
        self.cur_time = 0
        self.time_incr = 1
        self.sync_threshold = 5

    def run(self):
        while not self.exitThread:
            self.cur_time += self.time_incr
            time.sleep(0.01)
            if self.cur_time % self.sync_threshold == 0:
                self.cur_time = self.synchronize_time()
            self.makeRequest()


    def synchronize_time(self):
        with grpc.insecure_channel(self.clockServerAddr) as channel:
            stub = clock_pb2_grpc.ClockServerStub(channel)
            request = clock_pb2.SyncRequest()
            request.node_id = self.node_id
            try:
                response = stub.HandleSyncRequest(request, timeout=1) #default 1 second timeout
            except grpc._channel._InactiveRpcError:
                logger.debug('client has not started clock')
                return 0
            if response:
                logger.debug(f"cur_time: {self.cur_time}, received time: {response.cur_time}")
                return response.cur_time
            else:
                logger.warning("No response from Clock Server")

    def makeRequest(self):
        missedSegmentsByRoute = self.metadataManager.getOverdueSegments(self.cur_time)
        if len(missedSegmentsByRoute) == 0:
            #logger.debug("No Segments missed")
            return None
        for route in missedSegmentsByRoute:
            logger.info(f" Route={route} | Missed Segment count={len(missedSegmentsByRoute[route].segments)} | time={self.cur_time}")
            routeInfo = missedSegmentsByRoute[route]
            with grpc.insecure_channel(self.serverAddress) as channel:
                stub = clairvoyant_pb2_grpc.CVServerStub(channel)
                request = clairvoyant_pb2.CVRequest()
                missedDeliveryReq = clairvoyant_pb2.MissedDeliveryRequest()
                for s in routeInfo.segments:
                    cvSeg = missedDeliveryReq.segments.add()
                    cvSeg = routeInfo.segments[s]
                missedDeliveryReq.token_id = route 
                missedDeliveryReq.node_id = self.nodeId
                missedDeliveryReq.timestamp = self.cur_time
                request.misseddeliveryrequest.CopyFrom(missedDeliveryReq)
                response = stub.HandleCVRequest(request)
            self.metadataManager.cleanUpRoute(route)
