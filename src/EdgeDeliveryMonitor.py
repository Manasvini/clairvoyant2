import schedule
import time
import grpc
import clairvoyant_pb2_grpc
import clairvoyant_pb2
class EdgeDeliveryMonitor:
    def __init__(self, timeScale, serverAddress, nodeId, intervalSeconds, metadataManager):
        self.serverAddress = serverAddress
        self.timeScale = timeScale
        self.metadataManager = metadataManager
        self.nodeId = nodeId
        self.intervalSeconds = intervalSeconds

    def run(self):
        schedule.every(self.intervalSeconds).seconds.do(self.makeRequest)

        while True:
            schedule.run_pending()
            time.sleep(1)

    def makeRequest(self):
        missedSegmentsByRoute = self.metadataManager.getOverdueSegments()
        print('run delivery mon')
        if len(missedSegmentsByRoute) == 0:
            return None
        for route in missedSegmentsByRoute:
            print('route', route, ' has missed ', len(missedSegmentsByRoute[route].segments), 'segments')
            routeInfo = missedSegmentsByRoute[route]
            with grpc.insecure_channel(self.serverAddress) as channel:
                stub = clairvoyant_pb2_grpc.CVServerStub(channel)
                request = clairvoyant_pb2.CVRequest()
                missedDeliveryReq = clairvoyant_pb2.MissedDeliveryRequest()
                for s in routeInfo.segments:
                    cvSeg = missedDeliveryReq.segments.add()
                    #clairvoyant_pb2.Segment()
                    cvSeg = routeInfo.segments[s]
                    #cvSeg.segment_name = routeInfo.segments[s]['segment_name']
                    #cvSeg.segment_size = routeInfo.segments[s]
                
                #missedDeliveryReq.segments.extend([routeInfo.segments.values()])
                missedDeliveryReq.token_id = route 
                missedDeliveryReq.node_id = self.nodeId
                request.misseddeliveryrequest.CopyFrom(missedDeliveryReq)
                response = stub.HandleCVRequest(request)
                for route in missedSegmentsByRoute:
                    for seg_id in missedSegmentsByRoute[route].segments:
                        self.metadataManager.updateDeliveryForRoute(route, seg_id)
            self.metadataManager.cleanUpRoute(route)
