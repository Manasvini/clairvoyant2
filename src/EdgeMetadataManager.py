import clairvoyant_pb2

from redis import Redis
import threading
import time

class EdgeMetadataManager:
    
    def __init__(self, redis_address, redis_port):
        self.redis = Redis(host=redis_address, port=redis_port, decode_responses=True)
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
                print ("Subscriber got", message['data'])
                vals  = str(message['data']).split('|')
                print(vals)
                if len(vals) >= 2:
                    token_id = int(vals[0])
                    segment_id = vals[1]
                    self.updateRoute(token_id, segment_id)
            time.sleep(0.001)

    def startRedisSubscription(self):
        self.updateListener = threading.Thread(target=self.listen)
        self.updateListener.start()
   
    def addSegment(self, segmentInfo):
        values = {}
        values['segmentid'] = segmentInfo['segment'].segment_id
        values['segmentsize'] = str(segmentInfo['segment'].segment_size)
        values['segmentname'] = segmentInfo['segment'].segment_name
        values['nodeip'] = segmentInfo['source_ip']
        self.redis.hmset(segmentInfo['segment'].segment_id, values)
        #self.redis.sadd(video_id, set(segmentInfo['segment'].segment_id))

    def getSegment(self, segment_id):
        segmentInfo = {'segment':None, 'source':None, 'source_ip':None}
        values = self.redis.hgetall(segment_id)
        print(values)
        segment = clairvoyant_pb2.Segment()
        segment.segment_id = values['segmentid']
        segment.segment_size = values['segmentsize']
        segment.segment_name = values['segmentname']
        segmentInfo['segment'] = segment
        segmentInfo['nodeip'] = values['nodeip']
        return segmentInfo

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
        
