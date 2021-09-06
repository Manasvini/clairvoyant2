import sys
import os
import grpc
import logging

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

from shared.ModelReader import Model
import json
import time

from cloud.CloudMetadataClient import CloudMetadataClient
from cloud.DownloadManager import DownloadManager
from shared.EdgeNetworkModel import EdgeNetworkModel
from cloud.DownloadDispatcher import DownloadDispatcher
from monitoring.server import MonitoringServer

from threading import Thread

logging.basicConfig()
logger = logging.getLogger("cloud")
logger.setLevel(logging.INFO)

class CVCloudServer(clairvoyant_pb2_grpc.CVServerServicer):
    def __init__(self, filename):
        self.configDict = {}
        with open(filename) as fh:
            self.configDict = json.load(fh)
        logger.info('cloud config = {}'.format(json.dumps(self.configDict, indent=2)))
        self.metaClient = CloudMetadataClient(self.configDict['metaServerAddress'])
        self.mmWaveModels = self.getModels(self.configDict['nodeIds'])
        self.dlManager = DownloadManager(self.configDict['nodeIds'], \
                self.configDict['downloadSources'], self.configDict['timeScale'],\
                self.mmWaveModels, DownloadDispatcher(self.configDict['nodeIps'], None))

        monServer = MonitoringServer(address=self.configDict['monServerAddress'], \
                port=self.configDict['monServerPort'], edge_model_dict=self.mmWaveModels)

        self.monServerThread = Thread(target=monServer.run)
        self.monServerThread.start()
        
    def getModels(self, nodeids):
        return {nodeid : EdgeNetworkModel(nodeid) for nodeid in nodeids}
        
    def checkDownloadSchedule(self, segments, contact_points):
        #return {segment.segment_id: segment for segment in segments}        
        pass

    def handleVideoRequest(self, videoRequest):
        nodeInfos = self.metaClient.makeNearestNodesRequest(videoRequest.route)
        segments = self.metaClient.makeGetVideoInfoRequest(videoRequest.video_id)
        token = int(time.time_ns()/1e6)
        logger.info(f"token={token}, num_candidate_nodes={len(nodeInfos)}, num_segments={len(segments)}")
        assignments = self.dlManager.handleVideoRequest(token, segments, nodeInfos, videoRequest.timestamp)
        urls = []
        assigned_segments = set()
        for node in assignments:
            http_node_ip = self.configDict['httpAddress'][node]

            for segment in assignments[node]:
                urls.append('http://' + http_node_ip + '/' + segment.segment.segment_id)
                assigned_segments.add(segment.segment.segment_id)

        for s in segments:
            if s.segment_id not in assigned_segments:
                urls.append(self.configDict['defaultSource'] + '/' + s.segment_id)
        print('num urls = ', len(urls), token)
        return urls, token

    async def HandleCVRequest(
                self, request: clairvoyant_pb2.CVRequest, 
                context: grpc.aio.ServicerContext) -> clairvoyant_pb2.CVReply:
        reply = clairvoyant_pb2.CVReply()
        if request.HasField('videorequest'):
            urls, token = self.handleVideoRequest(request.videorequest)
            videoReply = clairvoyant_pb2.VideoReply()
            videoReply.token_id = token
            videoReply.urls.extend(urls)
            reply.videoreply.CopyFrom(videoReply)
            return reply 
        elif request.HasField('downloadcompleterequest'):
            logger.info('got dl update request from '+ request.downloadcompleterequest.node_id +  ' for' + str(len(request.downloadcompleterequest.segment_ids)) + ' segments')
            self.dlManager.updateDownloads(request.downloadcompleterequest.node_id, request.downloadcompleterequest.segment_ids)
            statusReply = clairvoyant_pb2.StatusReply()
            statusReply.status = 'Updated'
            reply.status.CopyFrom(statusReply)
        
        elif request.HasField('misseddeliveryrequest'):
            logger.debug(f"missed delivery for token={request.misseddeliveryrequest.token_id}")
            newAssignment = self.dlManager.handleMissedDelivery(request.misseddeliveryrequest.token_id,
                    request.misseddeliveryrequest.node_id, request.misseddeliveryrequest.segments, 
                    request.misseddeliveryrequest.timestamp)
            statusReply = clairvoyant_pb2.StatusReply()
            statusReply.status = 'Updated'
            reply.status.CopyFrom(statusReply)
        return reply

    def shutdown(self): 
        # TODO: this is probably not called when CloudServer is destroyed. 
        # Make sure we clean up server.
        monServer.shutdown()
        monServerThread.join()

async def serve(address, cvServer) -> None:
    server = grpc.aio.server()
    clairvoyant_pb2_grpc.add_CVServerServicer_to_server(cvServer, server)
    server.add_insecure_port(address)
    await server.start()
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await cvServer.shutdown()
        await server.stop(0)
