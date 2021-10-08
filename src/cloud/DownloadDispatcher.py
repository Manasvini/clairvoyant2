import logging
import asyncio
import grpc

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

parent_logger = logging.getLogger("cloud")
logger = parent_logger.getChild('dwnlddispatch')
logger.setLevel(logging.WARNING)

class DownloadDispatcher:
    def __init__(self, edge_ip_map, callback):
        self.edge_ip_map = edge_ip_map
        self.callback = callback

    def makeRequest(self, token_id, edge_node_id, segments,  segment_sources, arrival_time, contact_time) -> None:
        if edge_node_id not in self.edge_ip_map:
            return None
        ip = self.edge_ip_map[edge_node_id]    
        with grpc.insecure_channel(ip) as channel:
            stub = clairvoyant_pb2_grpc.EdgeServerStub(channel)
            request = clairvoyant_pb2.DownloadRequest()
            request.token_id = token_id
            request.arrival_time = int(arrival_time)
            request.contact_time = contact_time

            for segment in segments:
                s = request.segments.add()
                s.CopyFrom(segment)
            for s in segment_sources:
                request.segment_sources[s] = segment_sources[s]
            logger.info(f"node_id={edge_node_id}, num_segments={len(request.segments)}")
            response = stub.HandleDownloadRequest(request)
            #print(response)
            if self.callback is not None:
                self.callback(response)
            logging.info("Dl client received response for token %s: ", response.token_id)


#if __name__ == '__main__':
#    logging.basicConfig()
#    segment_sources = {'1':'0.0.0.0:8000'}
#    downloadDispatcher = DownloadDispatcher({'0':'0.0.0.0:50056'}, None)
#    for i  in range(2):
#        segment = clairvoyant_pb2.Segment()
#        segment.segment_id = '1'
#        segment.segment_size = 10
#        segment.segment_name = '1'
#        segments = [segment]
#        asyncio.run(downloadDispatcher.makeRequest(1, '0', segments, segment_sources))
