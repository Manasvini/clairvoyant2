import logging
import threading, asyncio

import grpc
import genprotos.clock_pb2 as clock_pb2
import genprotos.clock_pb2_grpc as clock_pb2_grpc

client_logger = logging.getLogger("client")
logger = client_logger.getChild("clock")
logger.setLevel(logging.INFO)

class ClockEndException(Exception):
    pass

class CVClock(clock_pb2_grpc.ClockServerServicer):
    def __init__(self, end_of_time, time_incr):
        self.end_of_time = end_of_time
        self.time_incr = time_incr
        self.cur_time = 0
        self.server = None
        self.addr = "0.0.0.0:8383"
        self.ClockServerThread = threading.Thread(target=self.server_thread, daemon=True)
        self.ClockServerThread.start()

        self.loop = None

    def server_thread(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            task = asyncio.ensure_future(self.serve())
            self.loop.run_until_complete(task)
        except (KeyboardInterrupt, ClockEndException) as e :
            self.loop.stop()
            self.loop.run_until_complete(task)
            self.loop.close()

    async def serve(self) -> None:
        self.server = grpc.aio.server()
        clock_pb2_grpc.add_ClockServerServicer_to_server(self, self.server)
        self.server.add_insecure_port(self.addr)
        logger.info(f"starting clock server on {self.addr}")
        try: 
            await self.server.start()
            await self.server.wait_for_termination()
        except(KeyboardInterrupt, ClockEndException):
            self.server.stop(0)
         
    def HandleSyncRequest(self, request: clock_pb2.SyncRequest, \
            context: grpc.aio.ServicerContext) -> clock_pb2.SyncResponse:
        logger.debug('Received sync request')
        response = clock_pb2.SyncResponse()
        response.cur_time = self.cur_time
        return response

    def shutdown(self):
        raise ClockEndException
        

    def advance(self):
        self.cur_time += self.time_incr
        if self.cur_time == self.end_of_time:
            raise ClockEndException
        return self.cur_time
