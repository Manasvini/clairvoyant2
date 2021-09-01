import json
import sys
import datetime
import time
import pandas as pd
from random import randrange

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc
import grpc

SCALE_TO_SECONDS = 60.0


def get_point(val1, val2, val3, val4):
    point = clairvoyant_pb2.Coordinate()
    point.x = val1
    point.y = val2
    point.speed = val3
    point.time = val4
    return point
    
def create_request(df):
    req = clairvoyant_pb2.VideoRequest()
    req.video_id = 'v' + str(1 + randrange(10))
    now = time.time_ns()/ 1e9
    start = time.time()
    #timestamp = datetime.datetime.timestamp(now)
    route = clairvoyant_pb2.Route()
    df['arrival'] = (df['time'] +now) / SCALE_TO_SECONDS 
    points = [get_point(r[0], r[1], r[2], r[3]) for r in zip(df['x'], df['y'], df['velocity'], df['arrival'])]
    for p in points:
        point = route.points.add()
        point.CopyFrom(p)

    end = time.time()
    print('loop took ', end - start)
    req.route.CopyFrom(route)
    cvreq = clairvoyant_pb2.CVRequest()
    cvreq.videorequest.CopyFrom(req)
    print('req has ' , len(df) , ' points ')
    return cvreq

def create_user_request(trajectory_file):
    df = pd.read_csv(trajectory_file)
    return create_request(df)


