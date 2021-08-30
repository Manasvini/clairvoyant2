import sys
import os
import asyncio
import grpc
import logging
import threading

import clairvoyant_pb2
import clairvoyant_pb2_grpc

from EdgeMetadataManager import EdgeMetadataManager
from ModelReader import Model
import json
from argparse import ArgumentParser
from EdgeDownloadQueue import EdgeDownloadQueue
from EdgeDownloadMonitor import EdgeDownloadMonitor

class EdgeDownloadServer(clairvoyant_pb2_grpc.EdgeServerServicer):
    def __init__(self, filename):
        self.configDict = {}
        with open(filename) as fh:
            self.configDict = json.load(fh)
        print('got config', self.configDict)
        self.metadataManager = EdgeMetadataManager(self.configDict['redisHost'], self.configDict['redisPort'], self.configDict['missedDeliveryThreshold'], self.configDict['timeScale'])
        self.metadataManager.startRedisSubscription()
        print('started subs')
        self.model = Model(self.configDict["modelFile"])

        self.queueManager = EdgeDownloadQueue(self.configDict['timeScale'], self.metadataManager)
        self.downloadMonitor = EdgeDownloadMonitor(self.configDict['timeScale'], self.queueManager, self.configDict['serverAddress'], self.configDict['nodeId'], self.configDict['intervalSeconds'])
        self.queueTracker = threading.Thread(target=self.downloadMonitor.run)
        self.queueTracker.start()
        
    def checkDownloadSchedule(self, segments, contact_points):
        return {segment.segment_id: segment for segment in segments}        

    async def HandleDownloadRequest(
                self, request: clairvoyant_pb2.DownloadRequest, 
                context: grpc.aio.ServicerContext) -> clairvoyant_pb2.DownloadReply:
        
        print('token = ', request.token_id,'num segments',  len(request.segments))
        committed_segments = self.checkDownloadSchedule(request.segments, request.contact_points)
        reply = clairvoyant_pb2.DownloadReply()
        reply.token_id = request.token_id
        
        for segment in request.segments:
            if segment.segment_id not in committed_segments:
                continue
            segmentInfo = {}
            #segmentInfo['segment']  =segment
            #segmentInfo['source_ip'] = request.segment_sources[segment.segment_id]
            #self.metadataManager.addSegment(segmentInfo)
            sourceSpeed = self.configDict['downloadSources'][request.segment_sources[segment.segment_id]]
            self.queueManager.enqueue(segment, sourceSpeed, request.segment_sources[segment.segment_id])
            #segment_id = reply.segment_ids.add(sefmen)
            #segment_id = segment.segment_id
        reply.segment_ids.extend(committed_segments.keys())
        self.metadataManager.addRoute(request.token_id, request.arrival_time, request.contact_time, list(committed_segments.values()))
        print('responding to server with ' + str(len(reply.segment_ids)) + ' segments')        
        return reply

    def shutdown(self):
        self.metadataManager.shutdown()
        self.queueTracker.join()

def create_dl_server(filename):
    dlServer = EdgeDownloadServer(filename)
    return dlServer

async def serve(dlServer, listen_addr) -> None:
    server = grpc.aio.server()
    clairvoyant_pb2_grpc.add_EdgeServerServicer_to_server(dlServer, server)
    #listen_addr = '[::]:50056'
    server.add_insecure_port(listen_addr)
    logging.info('starting server on %s', listen_addr)
    await server.start()
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await dlServer.shutdown()
        await server.stop(0)
        
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', type=str, help='config file')
    parser.add_argument('-a', '--address', dest='address', type=str, help='config file')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    dlServer = create_dl_server(args.config)
    asyncio.run(serve(dlServer, args.address))

if __name__=='__main__':
    main()
