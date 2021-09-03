import logging
import threading, asyncio

import grpc
import genprotos.clock_pb2 as clock_pb2
import genprotos.clock_pb2_grpc as clock_pb2_grpc

logging.basicConfig()
logger = logging.getLogger("client")

class ClockEndException(Exception):
    pass

class CVClock(clock_pb2_grpc.ClockServerServicer):
    def __init__(self, end_of_time, time_incr):
        self.end_of_time = end_of_time
        self.time_incr = time_incr
        self.cur_time = 0
        self.server = None
        self.ClockServerThread = threading.Thread(target=self.server_thread, daemon=True)
        self.ClockServerThread.start()

    def server_thread(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task = asyncio.ensure_future(self.serve())
            loop.run_until_complete(task)
        except (KeyboardInterrupt,ClockEndException) as e :
            self.server.stop(0)
            #loop.stop()
            #loop.run_until_complete(task)
            loop.close()

    async def serve(self) -> None:

        addr = "0.0.0.0:8383"
        self.server = grpc.aio.server()
        clock_pb2_grpc.add_ClockServerServicer_to_server(self, self.server)
        self.server.add_insecure_port(addr)
        logging.info('starting server on %s', addr)
        await self.server.start()
        await self.server.wait_for_termination()
         
    def HandleSyncRequest(self, request: clock_pb2.SyncRequest, \
            context: grpc.aio.ServicerContext) -> clock_pb2.SyncResponse:
        response = clock_pb2.SyncResponse()
        response.cur_time = self.cur_time
        return response

    def shutdown(self):
        self.server.stop(0)

    def advance(self):
        self.cur_time += self.time_incr
        if self.cur_time == self.end_of_time:
            raise ClockEndException
        return self.cur_time
