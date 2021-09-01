import schedule
import time
import grpc
import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

import logging
class EdgeDownloadMonitor:
    def __init__(self, timeScale, queueManager, serverAddress, nodeId, intervalSeconds):
        self.serverAddress = serverAddress
        self.timeScale = timeScale
        self.queueManager = queueManager
        self.nodeId = nodeId
        self.intervalSeconds = intervalSeconds
        logging.basicConfig(level=logging.INFO)
        logging.info("inited")
        print('finished init dl mon')
    def run(self):
        schedule.every(self.intervalSeconds).seconds.do(self.makeRequest)
        while True:
            schedule.run_pending()
            time.sleep(0.05)

    def makeRequest(self):
        logging.info('making dl mon request')
        completedData = self.queueManager.dequeue()
        segment_ids = [seg.segment.segment_id for seg in completedData]
        #print('finisged' + str(len(segment_ids)))
        if len(segment_ids) == 0:
            return None
        with grpc.insecure_channel(self.serverAddress) as channel:
            stub = clairvoyant_pb2_grpc.CVServerStub(channel)
            request = clairvoyant_pb2.CVRequest()
            dlCompleteReq = clairvoyant_pb2.DownloadCompleteRequest()
            dlCompleteReq.segment_ids.extend(segment_ids)
            dlCompleteReq.node_id = self.nodeId
            request.downloadcompleterequest.CopyFrom(dlCompleteReq)
            response = stub.HandleCVRequest(request)
            print('dl mon got response', response, ' for ', len(segment_ids), ' segments')
