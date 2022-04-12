import logging
import threading
from concurrent import futures
import json
import asyncio
import grpc
import genprotos.clock_pb2 as clock_pb2
import genprotos.clock_pb2_grpc as clock_pb2_grpc
import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc

client_logger = logging.getLogger("client")
logger = client_logger.getChild("clock")
logger.setLevel(logging.INFO)

class ClockEndException(Exception):
    pass

class CVClock(clock_pb2_grpc.ClockServerServicer):
    def __init__(self, end_of_time, time_incr, cloud_config, is_thread=True):
        self.end_of_time = end_of_time
        self.time_incr = time_incr
        self.cur_time = 0
        self.server = None
        self.addr = "0.0.0.0:8383"
        self.is_thread = is_thread

        self.cloud_config_dict = {}
        with open(cloud_config) as fh:
            self.cloud_config_dict = json.load(fh)
        logger.info('cloud config = {}'.format(json.dumps(self.cloud_config_dict, indent=2)))
        
        if is_thread:
          self.ClockServerThread = threading.Thread(target=self.server_thread, daemon=True)
          self.ClockServerThread.start()
          self.loop = None

    def server_thread(self):
        if self.is_thread:
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                task = asyncio.ensure_future(self.serve())
                self.loop.run_until_complete(task)
            except (KeyboardInterrupt, ClockEndException) as e :
                self.loop.stop()
                self.loop.close()

    def serve(self) -> None:
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
        clock_pb2_grpc.add_ClockServerServicer_to_server(self, self.server)
        self.server.add_insecure_port(self.addr)
        logger.info(f"starting clock server on {self.addr}")
        try: 
            self.server.start()
            self.server.wait_for_termination()
        except(KeyboardInterrupt, ClockEndException):
            self.shutdown()
            self.server.stop(0)
         
    def HandleSyncRequest(self, request: clock_pb2.SyncRequest, \
            context: grpc.aio.ServicerContext) -> clock_pb2.SyncResponse:
        logger.debug('Received sync request')
        response = clock_pb2.SyncResponse()
        response.cur_time = self.cur_time
        return response

    def HandleAdvanceClock(self, request: clock_pb2.AdvanceClock, \
                           context: grpc.aio.ServicerContext) -> clock_pb2.SyncResponse:
        logger.debug('Received Advance request')
        response = clock_pb2.SyncResponse()
        response.cur_time = self.advance()
        return response

    def shutdown(self):
        if self.is_thread:
          raise ClockEndException
          self.server_thread.join()
        

    def advance(self):
        self.cur_time += self.time_incr

        logger.info(f"advancing clock server to {self.cur_time}")

        self.advanceEdges()
        
        if self.cur_time == self.end_of_time:
            raise ClockEndException
        return self.cur_time

    def advanceEdges(self):
        for edge_node in self.cloud_config_dict["edgeNodes"]:
            address = str(edge_node["ip"]) + ":" + str(edge_node["edgeDaemon"])
            with grpc.insecure_channel(address) as channel:
                stub = clairvoyant_pb2_grpc.EdgeServerStub(channel)
                request = clairvoyant_pb2.ClockUpdateRequest()
                request.newClock = self.cur_time

                response = stub.HandleUpdateClock(request)
                
                logger.info(response)
                logger.info("advancing clock " + str(response.oldClock) + "->"  + str(self.cur_time) + " for " + str(edge_node["id"]) + " on " + address)
        return