import clairvoyant_pb2

from redis import Redis
import threading
import time
from collections import OrderedDict
import copy

class RouteInfo:
    def __init__(self):
        self.token_id = None
        self.arrival_time = None
        self.contact_time = None
        self.segments = None

class EdgeMetadataManager:
    
    def __init__(self, redis_address, redis_port, missedDeliveryThreshold, timeScale):
        self.redis = Redis(host=redis_address, port=redis_port, decode_responses=True)
        self.routes_queue = []
        self.routes = OrderedDict()

        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe('user_download_notify')
        self.updateListener = None
        self.mutex = threading.Lock()
        self.missedDeliveryThreshold = missedDeliveryThreshold
        self.timeScale = timeScale

    def updateDeliveryForRoute(self, token_id, segment_id):
        self.mutex.acquire()
        try:
            print('delivered', segment_id, ' for ', token_id)
            if token_id in self.routes: 
                routeInfo = self.routes[token_id]
                routeInfo.segments.pop(segment_id)
                self.routes[token_id] = routeInfo 
        finally:
            self.mutex.release()

    def listen(self):
        while True:
            message = self.pubsub.get_message()
            if message:
                #print ("Subscriber got", message['data'])
                vals  = str(message['data']).split('|')
                if len(vals) >= 2:
                    token_id = int(vals[0])
                    segment_id = vals[1]
                    self.updateDeliveryForRoute(token_id, segment_id)
                    self.cleanUpRoute(token_id)


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

    def hasSegment(self, segment_id):
        if self.redis.exists(segment_id):
            return True
        return False
    
    def getSegment(self, segment_id):
        segmentInfo = {'segment':None, 'source':None, 'source_ip':None}
        values = self.redis.hgetall(segment_id)
        segment = clairvoyant_pb2.Segment()
        segment.segment_id = values['segmentid']
        segment.segment_size = values['segmentsize']
        segment.segment_name = values['segmentname']
        segmentInfo['segment'] = segment
        segmentInfo['nodeip'] = values['nodeip']
        return segmentInfo

    def addRoute(self, token_id, arrival_time, contact_time, segments):
        self.mutex.acquire()
        try:
            #print(token_id, arrival_time, contact_time, segments)
            print('added route', token_id)
            routeInfo = RouteInfo()
            routeInfo.token_id = token_id
            routeInfo.arrival_time = arrival_time
            routeInfo.contact_time = contact_time
            routeInfo.segments = {segment.segment_id: segment for segment in segments}
            self.routes[token_id] = routeInfo        
        finally:
            self.mutex.release()
 
    def getOverdueSegments(self):
        self.mutex.acquire()
        undelivered_segments = {}
        try:
            now = time.time_ns() / 1e9
            deadline = now + self.missedDeliveryThreshold
            deadline /= self.timeScale
            if len(self.routes) == 0:
                print('no routes')
            for token_id in self.routes:
                print('route is ', token_id)
                routeInfo =  self.routes[token_id]
                print('deadline = ', deadline, ' latest',  routeInfo.arrival_time + routeInfo.contact_time/self.timeScale, ' arrival = ', routeInfo.arrival_time)
                if len(routeInfo.segments) > 0 and routeInfo.arrival_time + routeInfo.contact_time/self.timeScale > deadline:
                    undelivered_segments[token_id] = copy.deepcopy(routeInfo)
        finally:
            self.mutex.release()
        return undelivered_segments

    def getRoutesAt(self, arrival_time, contact_time):
        self.mutex.acquire()
        route_ids = []
        try:
            for token_id, routeInfo in route.items():
                if (routeInfo.arrival_time + routeInfo.contact_time < arrival_time) or (routeInfo.arrivalTime > arrival_time + contact_time):
                    continue
                route_ids.append(token_id)
        finally:
            self.mutex.release()
        return route_ids

    def cleanUpRoute(self, token_id):
        self.mutex.acquire()
        try:
            if token_id in self.routes and len(self.routes[token_id].segments) == 0:
                print('removed route', token_id)
                self.routes.pop(token_id)
        finally:
            self.mutex.release()
    
    def shutdown(self):
        self.updateListener.join()
        
