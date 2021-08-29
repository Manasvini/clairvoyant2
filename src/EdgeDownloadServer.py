import sys
import os
import asyncio
import grpc
import logging

import clairvoyant_pb2
import clairvoyant_pb2_grpc

from EdgeMetadataManager import EdgeMetadataManager

class EdgeDownloadServer(clairvoyant_pb2_grpc.EdgeServerServicer):
    def __init__(self):
        self.metadataManager = EdgeMetadataManager('127.0.0.1', '6379')
        self.metadataManager.startRedisSubscription()
        print('started subs')

    async def HandleDownloadRequest(
                self, request: clairvoyant_pb2.DownloadRequest, 
                context: grpc.aio.ServicerContext) -> clairvoyant_pb2.DownloadReply:
        # do stuff here
        print(request.token_id, request.segment_sources, len(request.segments))
        for segment in request.segments:
            segmentInfo = {}
            segmentInfo['segment']  =segment
            segmentInfo['source_ip'] = request.segment_sources[segment.segment_id]
            self.metadataManager.addSegment(segmentInfo)
        reply = clairvoyant_pb2.DownloadReply()
        reply.token_id = request.token_id
        return reply

    def shutdown(self):
        self.metadataManager.shutdown()
async def serve() -> None:
    server = grpc.aio.server()
    dlServer = EdgeDownloadServer()
    clairvoyant_pb2_grpc.add_EdgeServerServicer_to_server(dlServer, server)
    listen_addr = '[::]:50056'
    server.add_insecure_port(listen_addr)
    logging.info('starting server on %s', listen_addr)
    await server.start()
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await dlServer.shutdown()
        await server.stop(0)
        

def main():
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())

if __name__=='__main__':
    main()
