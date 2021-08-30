import sys
import os
import asyncio
import grpc
import logging

import clairvoyant_pb2
import clairvoyant_pb2_grpc

from EdgeMetadataManager import EdgeMetadataManager
from ModelReader import Model
import json
from argparse import ArgumentParser

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

    def checkDownloadSchedule(self, segments, contact_points):
        return {segment.segment_id: segment for segment in segments}        

    async def HandleDownloadRequest(
                self, request: clairvoyant_pb2.DownloadRequest, 
                context: grpc.aio.ServicerContext) -> clairvoyant_pb2.DownloadReply:
        
        print(request.token_id, request.segment_sources, len(request.segments))
        committed_segments = self.checkDownloadSchedule(request.segments, request.contact_points)
        reply = clairvoyant_pb2.DownloadReply()
        reply.token_id = request.token_id
        
        for segment in request.segments:
            if segment.segment_id not in committed_segments:
                continue
            segmentInfo = {}
            segmentInfo['segment']  =segment
            segmentInfo['source_ip'] = request.segment_sources[segment.segment_id]
            self.metadataManager.addSegment(segmentInfo)
            #segment_id = reply.segment_ids.add(sefmen)
            #segment_id = segment.segment_id
        reply.segment_ids.extend(committed_segments.keys())
        self.metadataManager.addRoute(request.token_id, request.arrival_time, request.contact_time, list(committed_segments.values()))
        print('responding to server with ' + str(len(reply.segment_ids)) + ' segments')        
        return reply

    def shutdown(self):
        self.metadataManager.shutdown()

async def serve(filename, listen_addr) -> None:
    server = grpc.aio.server()
    dlServer = EdgeDownloadServer(filename)
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
    asyncio.run(serve(args.config, args.address))

if __name__=='__main__':
    main()
