from redis import Redis
from collections import OrderedDict
import threading
import time
import copy
import logging

import grpc
import genprotos.clairvoyant_pb2 as clairvoyant_pb2

parent_logger = logging.getLogger("edge")
logger = parent_logger.getChild("metadatamgr")
logger.setLevel(logging.DEBUG)

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
        self.sub_topic = 'user_download_notify'
        self.pubsub.subscribe(self.sub_topic)
        self.updateListener = None
        self.mutex = threading.Lock()
        self.missedDeliveryThreshold = missedDeliveryThreshold
        self.timeScale = timeScale

    def updateDeliveryForRoute(self, token_id, segment_id):
        self.mutex.acquire()
        try:
            if token_id in self.routes: 
                routeInfo = self.routes[token_id]
                if segment_id in routeInfo.segments:
                    logger.info(f"route={token_id}, delivered segment={segment_id}")
                    del routeInfo.segments[segment_id]
                else:
                    logger.error("missing segment metadata")
                self.routes[token_id] = routeInfo 
        finally:
            self.mutex.release()

    def listen(self):
        while True:
            message = self.pubsub.get_message()
            if message:
                vals  = str(message['data']).split('|')
                if len(vals) >= 2:
                    token_id = int(vals[0])
                    segment_id = vals[1]
                    self.updateDeliveryForRoute(token_id, segment_id)
                    #self.cleanUpRoute(token_id)


            time.sleep(0.001)

    def startRedisSubscription(self):
        self.updateListener = threading.Thread(target=self.listen)
        self.updateListener.start()
        logger.info(f"redis subscription started on topic={self.sub_topic}")
   
    def addSegment(self, segmentInfo):
        values = {}
        values['segmentid'] = segmentInfo['segment'].segment_id
        values['segmentsize'] = str(segmentInfo['segment'].segment_size)
        values['segmentname'] = segmentInfo['segment'].segment_name
        values['nodeip'] = segmentInfo['source_ip']
        self.redis.hmset(segmentInfo['segment'].segment_id, values)
        #print('added segment',  values)
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

    def addSegments(self, segments, segment_sources):
        for segment in segments:
            source_ip = segment_sources[segment.segment_id]

            values = {}
            values['segmentid'] = segment.segment_id
            values['segmentsize'] = str(segment.segment_size)
            values['segmentname'] = segment.segment_name
            values['nodeip'] = source_ip
            self.redis.hmset(segment.segment_id, values)


    def addRoute(self, token_id, arrival_time, contact_time, segments, segment_sources):
        self.mutex.acquire()
        try:
            #print(token_id, arrival_time, contact_time, segments)
            routeInfo = RouteInfo()
            routeInfo.token_id = token_id
            routeInfo.arrival_time = arrival_time
            routeInfo.contact_time = contact_time
            routeInfo.segments = {segment.segment_id: segment for segment in segments}
            self.routes[token_id] = routeInfo        
            logger.debug(f"add_route={token_id}, contact_time={routeInfo.contact_time}")
            self.addSegments(segments, segment_sources)
            logger.debug(f"added segments - count={len(segments)}")
        finally:
            self.mutex.release()


    def getOverdueSegments(self, cur_time):
        self.mutex.acquire() # contending with redis listener
        undelivered_segments = {}
        try:
            for token_id in self.routes:
                routeInfo =  self.routes[token_id]
                deadline = routeInfo.arrival_time + routeInfo.contact_time + \
                        self.missedDeliveryThreshold 

                #logger.debug(f"cur_time={cur_time}, contact_time={routeInfo.contact_time}, arrival={routeInfo.arrival_time},deadline={deadline}")
                if len(routeInfo.segments) > 0 and cur_time > deadline:
                    logger.debug("clean up routeInfo post overdue calculation")
                    undelivered_segments[token_id] = self.routes.pop(token_id)
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
                logger.info(f"Removed route={token_id}")
                del self.routes[token_id]
        finally:
            self.mutex.release()
    
    def shutdown(self):
        self.exitThread = True
        self.clockThread.join()
        self.updateListener.join()
        
