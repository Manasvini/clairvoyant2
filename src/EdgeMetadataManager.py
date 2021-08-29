import clairvoyant_pb2

from redis import Redis
import threading
import time

class EdgeMetadataManager:
    
    def __init__(self, redis_address, redis_port):
        self.redis = Redis(host=redis_address, port=redis_port)
        self.routes_queue = []
        self.routes_info = {}

        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe('user_download_notify')
        self.updateListener = None

    def updateRoute(self, token_id, segment_id):
        pass


    def listen(self):
        while True:
            message = self.pubsub.get_message()
            if message:
                print ("Subscriber got", message)
                token_id, segment_id = message.split('|')
                self.updateRoute(token_id, segment_id)
            time.sleep(0.001)

    def startRedisSubscription(self):
        self.updateListener = threading.Thread(target=self.listen)
        self.updateListener.start()
   
    def addSegment(self, segment):
        pass

    def getSegment(self, segment_id):
        pass

    def addRoute(self, token_id, arrival_time, contact_time, segments):
        pass

    def getOverdueSegments(self, token_id):
        pass        


    def getRoutesAt(self, arrival_time, contact_time):
        pass
    def removeRoute(self, route_id):
        pass
    
    def shutdown(self):
        self.updateListener.join()
        
