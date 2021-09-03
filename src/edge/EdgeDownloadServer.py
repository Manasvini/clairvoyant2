import sys
import os
import logging
import threading
import json

import grpc
import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

from edge.EdgeMetadataManager import EdgeMetadataManager
from edge.EdgeDownloadQueue import EdgeDownloadQueue
from edge.EdgeDownloadMonitor import EdgeDownloadMonitor
from edge.EdgeDeliveryMonitor import EdgeDeliveryMonitor
from shared.ModelReader import Model
from monitoring.client import MonitoringClient

class EdgeDownloadServer(clairvoyant_pb2_grpc.EdgeServerServicer):
    def __init__(self, filename):
        self.configDict = {}
        with open(filename) as fh:
            self.configDict = json.load(fh)
        print('got config', self.configDict)
        self.metadataManager = EdgeMetadataManager(self.configDict['redisHost'], \
                self.configDict['redisPort'], 
                self.configDict['missedDeliveryThreshold'],
                self.configDict['timeScale'],
                self.configDict['nodeId'])
        self.metadataManager.startRedisSubscription()
        print('started subs')
        self.model = Model(self.configDict['modelFile'])
        self.monClient = MonitoringClient(self.configDict['modelFile'], self.configDict['monInterval'], \
                self.configDict['monServerAddress'], self.configDict['nodeId'])
        self.monClient.start()

        #self.queueManager = EdgeDownloadQueue(self.configDict['timeScale'], self.metadataManager)
        #self.downloadMonitor = EdgeDownloadMonitor(self.configDict['timeScale'], self.queueManager, self.configDict['serverAddress'], self.configDict['nodeId'], self.configDict['intervalSeconds'])
        #self.queueTracker = threading.Thread(target=self.downloadMonitor.run)
        #self.queueTracker.start()
       
        self.deliveryMon = EdgeDeliveryMonitor(self.configDict['timeScale'], self.configDict['serverAddress'], self.configDict['nodeId'], self.configDict['intervalSeconds'], self.metadataManager)
        self.deliveryThread = threading.Thread(target=self.deliveryMon.run)
        self.deliveryThread.start()

    def checkDownloadSchedule(self, segments, contact_points):
        """
        Purpose: return segments which require downloading
        """
        return {segment.segment_id: segment for segment in segments}        

    async def HandleDownloadRequest(
                self, request: clairvoyant_pb2.DownloadRequest, 
                context: grpc.aio.ServicerContext) -> clairvoyant_pb2.DownloadReply:
        
        print('token = ', request.token_id,'num segments',  len(request.segments))
        committed_segments = self.checkDownloadSchedule(request.segments, request.contact_points)
        reply = clairvoyant_pb2.DownloadReply()
        reply.token_id = request.token_id
        
        #for segment in request.segments:
        #    if segment.segment_id not in committed_segments:
        #        continue
        #    segmentInfo = {}
        #    #segmentInfo['segment']  =segment
        #    #segmentInfo['source_ip'] = request.segment_sources[segment.segment_id]
        #    #self.metadataManager.addSegment(segmentInfo)
        #    sourceSpeed = self.configDict['downloadSources'][request.segment_sources[segment.segment_id]]
        #    self.queueManager.enqueue(segment, sourceSpeed, request.segment_sources[segment.segment_id])
        #    #segment_id = reply.segment_ids.add(sefmen)
        #    #segment_id = segment.segment_id
        reply.segment_ids.extend(committed_segments.keys())
        print('req ', request.token_id, ' has arrival', request.arrival_time)
        self.metadataManager.addRoute(request.token_id, request.arrival_time, request.contact_time, list(committed_segments.values()))
        print('responding to server with ' + str(len(reply.segment_ids)) + ' segments')        
        return reply

    def shutdown(self):
        self.metadataManager.shutdown()
        #self.queueTracker.join()
        self.monClient.stop()
        monClient.join()

async def serve(dlServer, listen_addr) -> None:
    server = grpc.aio.server()
    clairvoyant_pb2_grpc.add_EdgeServerServicer_to_server(dlServer, server)
    server.add_insecure_port(listen_addr)
    logging.info('starting server on %s', listen_addr)
    await server.start()
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await dlServer.shutdown()
        await server.stop(0)

