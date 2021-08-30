import sys
import os
import asyncio
import grpc
import logging

import clairvoyant_pb2
import clairvoyant_pb2_grpc

from ModelReader import Model
import json
from argparse import ArgumentParser
import time

from CloudMetadataClient import CloudMetadataClient
from DownloadManager import DownloadManager
from EdgeNetworkModel import EdgeNetworkModel
from DownloadDispatcher import DownloadDispatcher
from monitoring.server import MonitoringServer

from threading import Thread

class CVCloudServer(clairvoyant_pb2_grpc.EdgeServerServicer):
    def __init__(self, filename, mmWaveModels):
        self.configDict = {}
        with open(filename) as fh:
            self.configDict = json.load(fh)
        print('got config', self.configDict)
        self.metaClient = CloudMetadataClient(self.configDict['metaServerAddress'])
        self.dlManager = DownloadManager(self.configDict['nodeIds'], self.configDict['downloadSources'], self.configDict['timeScale'], mmWaveModels, DownloadDispatcher(self.configDict['nodeIps'], None))
        monServer = MonitoringServer(address=self.configDict['monServerAddress'], port=self.configDict['monServerPort'],\
                edge_model_dict=mmWaveModels)
        self.monServerThread = Thread(target=monServer.run)
        self.monServerThread.start()
        
        
    def checkDownloadSchedule(self, segments, contact_points):
        #return {segment.segment_id: segment for segment in segments}        
        pass

    def handleVideoRequest(self, videoRequest):
        nodeInfos = self.metaClient.makeNearestNodesRequest(videoRequest.route)
        segments = self.metaClient.makeGetVideoInfoRequest(videoRequest.video_id)
        token = int(time.time_ns()/1e6)
        print('token = ', token, 'num node infos', len(nodeInfos), 'num segments = ', len(segments))
        assignments = self.dlManager.handleVideoRequest(token, segments, nodeInfos)
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
            logging.info('got dl update request from '+ request.downloadcompleterequest.node_id +  ' for' + str(len(request.downloadcompleterequest.segment_ids)) + ' segments')
            self.dlManager.updateDownloads(request.downloadcompleterequest.node_id, request.downloadcompleterequest.segment_ids)
            statusReply = clairvoyant_pb2.StatusReply()
            statusReply.status = 'Updated'
            reply.status.CopyFrom(statusReply)
        
        elif request.HasField('misseddeliveryrequest'):
            logging.info('got missed delivery for token', request.misseddeliveryrequest.token_id)
            newAssignment = self.dlManager.handleMissedDelivery(request.misseddeliveryrequest.token_id, request.misseddeliveryrequest.node_id, request.misseddeliveryrequest.segments)
            statusReply = clairvoyant_pb2.StatusReply()
            statusReply.status = 'Updated'
            reply.status.CopyFrom(statusReply)
        return reply

    def shutdown(self): #TODO: this is probably not called when CloudServer is destroyed. Make sure we clean up server
        monServer.shutdown()
        monServerThread.join()

async def serve(address, cvServer) -> None:
    server = grpc.aio.server()
    clairvoyant_pb2_grpc.add_CVServerServicer_to_server(cvServer, server)
    #listen_addr = '[::]:50056'
    server.add_insecure_port(address)
    try:
        await server.start()
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await server.stop(0)
        
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', type=str, help='config file')
    parser.add_argument('-a', '--address', dest='address', type=str, help='config file')
    args = parser.parse_args()
    return args

def create_cv_server(filename):
    cvServer = CVCloudServer(filename, {'node_0':EdgeNetworkModel('node_0')})
    return cvServer

def main():
    args = parse_args()
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    cvServer = create_cv_server(args.config) 
    asyncio.run(serve(args.address, cvServer))

if __name__=='__main__':
    main()
