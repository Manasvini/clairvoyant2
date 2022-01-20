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
logger.setLevel(logging.WARNING)

class CVCloudServer(clairvoyant_pb2_grpc.CVServerServicer):
    def __init__(self, filename):
        self.configDict = {}
        with open(filename) as fh:
            self.configDict = json.load(fh)
        logger.info('cloud config = {}'.format(json.dumps(self.configDict, indent=2)))
        self.metaClient = CloudMetadataClient(self.configDict['metaServerAddress'])

        # BEGIN Config File simplification: Simplified config, but minimal code change
        # TODO: eliminate this when go-ify cloud
        nodeIds = [node["id"] for node in self.configDict["edgeNodes"]]
        nodeDaemonIps = [node["ip"] + ":" + node["edgeDaemon"] for node in self.configDict["edgeNodes"]]
        nodeMap = {node["id"]:node for node in self.configDict["edgeNodes"]}
        downloadSourcesOldFormat = {}
        for node in self.configDict["edgeNodes"]:
            with open(self.configDict["downloadSourceFile"]) as fh:
                newSources = json.load(fh)

                perNodeDict = {}
                for rec in sources:
                    if rec["src_id"] == "default":
                        key=self.configDict["defaultSource"]
                    else:
                        node = nodeMap[rec["src_id"]]
                        key=node["ip"] + ":" + node["contentServer"]
                        
                    perNodeDict[key] = rec["bandwidth"]
                downloadSourcesOldFormat[node["id"]] = perNodeDict
        # END Config File simplification: Simplified config, but minimal code change

        self.mmWaveModels = self.getModels(nodeIds)
        mode = None
        if 'mode' in self.configDict:
            mode=self.configDict['mode']

        
        self.dlManager = DownloadManager(nodeIds,
                downloadSourcesOldFormat,
                self.configDict['timeScale'],
                self.mmWaveModels, 
                DownloadDispatcher(nodeDaemonIps, None),
                mode)

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
        logger.debug(f"nodes_len={len(nodeInfos)}")
        token = int(time.time_ns()/1e6)
                
        logger.info(f"token={token}, num_candidate_nodes={len(nodeInfos)}, video={videoRequest.video_id}, num_segments={len(segments)}")
        supposed_playback_start = videoRequest.route.points[0].time
        results = self.dlManager.handleVideoRequest(token, supposed_playback_start,\
                segments, nodeInfos, videoRequest.timestamp)
        urls = []
        #assigned_segments = set()

        #for node in assignments:
        #    http_node_ip = self.configDict['httpAddress'][node]

        #    for segment in assignments[node]:
        #        urls.append('http://' + http_node_ip + '/' + segment.segment.segment_id)
        #        assigned_segments.add(segment.segment.segment_id)

        #for s in segments:
        #    if s.segment_id not in assigned_segments:
        #        urls.append(self.configDict['defaultSource'] + '/' + s.segment_id)

        for segment in segments:
            urls.append(self.configDict['defaultSource'] + segment.segment_id)

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
