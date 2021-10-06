import json
import sys
import datetime
import time
import pandas as pd
import logging
from random import randrange

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc
import grpc

logger = logging.getLogger("client")

def get_point(val1, val2, val3, val4):
    point = clairvoyant_pb2.Coordinate()
    point.x = val1
    point.y = val2
    point.speed = val3
    point.time = val4
    return point
    
def create_request(df, request_timestamp, dont_random=False):
    req = clairvoyant_pb2.VideoRequest()

    req.video_id = 'v' + str(1 + randrange(10))
    if dont_random:
        req.video_id = 'v1'
        
    req.timestamp = request_timestamp

    route = clairvoyant_pb2.Route()
    points = [get_point(r[0], r[1], r[2], r[3]) for r in zip(df['x'], df['y'], df['velocity'], df['time'])]
    logger.info('Number of points in route request: {}'.format(len(points)))

    for p in points:
        point = route.points.add()
        point.CopyFrom(p)
    req.route.CopyFrom(route)

    cvreq = clairvoyant_pb2.CVRequest()
    cvreq.videorequest.CopyFrom(req)
    return cvreq

def create_user_request(trajectory_file, request_timestamp):
    df = pd.read_csv(trajectory_file)
    return create_request(df, request_timestamp)
