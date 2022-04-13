#!/usr/bin/python3
from planar import Polygon
from haversine import inverse_haversine, Direction, Unit, haversine
from math import pi
import copy
from argparse import ArgumentParser
import pandas as pd
import numpy as np
import random
from scipy import interpolate
import itertools

def get_num_users_to_start(mean):
    num_users = np.random.poisson(lam=mean)
    return num_users


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-n', '--numedgenodes', type=int, default=1, help='Number of edge nodes')# 10
    parser.add_argument('--lon', type=float, required=True, help='start latitude') # 7.490957273435992
    parser.add_argument('--lat', type=float, required=True, help='start longitude')# 43.77477219407852
    parser.add_argument('-o', '--outputfile', required=True, type=str, help='output file') # 10nodes.csv
    parser.add_argument('-u', '--numusers', required=True, type=int, help='num users') # 20 users
    
    parser.add_argument('-i', '--timeincr', required=True, type=float, help='time step size') # 1
    parser.add_argument('-s', '--speed', required=True, type=float, help='speed in m/s') # 15
    parser.add_argument('-e', '--edge', required=True, type=float, help='polygon edge') # 3272
    parser.add_argument('-p', '--poisson', required=False, type=float, help='model poisson arrival') # 3272
    args = parser.parse_args()

    return args

def getRange(a, b, num_vals):
    incr = (b - a)/num_vals
    start = a
    vals = [a]
    while start != b and len(vals) < num_vals:
        start += incr
        vals.append(start)
    return vals

#    return [v for v in range(a, b, incr)]

def interpolate_vals(lat1, lon1, lat2, lon2, incr, speed):
    x = [lon1, lon2]
    y = [lat1, lat2]
    distance = haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS)
    numPoints = int(distance / speed) / incr
    print('dist', distance, 'numpts ', numPoints)
    f = interpolate.interp1d(x, y, kind='linear')
    xnew = getRange(lon1, lon2, numPoints)
    ynew = f(xnew)
    return xnew, ynew
    
def build_collection(numNodes):
    nodes = list(range(numNodes))
    collection = [nodes.copy()]
    for _ in range(numNodes-1):
        nodes = nodes[1:] + [nodes[0]]
        collection.append(nodes.copy())
    print(len(collection))
    for nodeset in sorted(collection, key=lambda x : x.index(0)):
        print(nodeset)
        

def create_trajectory(numNodes, speed, edge_node_positions, time_incr, filename, userId, cur_time):
    nodes = [i for i in range(numNodes)]
    random.shuffle(nodes)
    print(nodes)
    idx = 0
    start_lon = edge_node_positions[idx]['x']
    start_lat = edge_node_positions[idx]['y']
    move_dist = speed * time_incr
    points = []
    while idx < numNodes - 1:
        lat1 = edge_node_positions[nodes[idx]]['y']
        lon1 = edge_node_positions[nodes[idx]]['x']
        lat2 = edge_node_positions[nodes[idx + 1]]['y']
        lon2 = edge_node_positions[nodes[idx + 1]]['x']
        print('cur edge node is ', nodes[idx], ' next is ', nodes[idx + 1]) 
        xvals, yvals = interpolate_vals(lat1, lon1, lat2, lon2, time_incr, speed)
        for x, y in zip(xvals, yvals):
            points.append({'x':x, 'y':y, 'z':0, 'time':cur_time, 'velocity':speed, 'userId':userId})
            cur_time += time_incr
        idx += 1
    df = pd.DataFrame(points)
    ndf = df.reindex(columns=['userId','time','x','y','z','velocity'])
    ndf.to_csv(filename, index=False)
    return cur_time

def create_polygon(numNodes, maxDist, lat, lon, outFile):
    points = []
    start_lon = lon
    start_lat = lat
    #points.append({'x':lon, 'y':lat})
    angle = 0
    for i in range(numNodes):
        angle = angle + 2 * (pi/ numNodes)
        print('angle=', angle*(180/pi))
        next_lat, next_lon = inverse_haversine((start_lat, start_lon), maxDist/2, angle, unit=Unit.METERS)

        points.append({'x':next_lon, 'y':next_lat})
    df = pd.DataFrame(points)
    df.to_csv(outFile, index=False)
    return points

def do_non_overlapping(numusers, numedge, speed, edge_nodes, time_incr, cur_time):
    for i in range(numusers):
        cur_time = create_trajectory(numedge, speed, edge_nodes, time_incr, 'user' + str(i) + '.csv', 'user' + str(i),  cur_time)


def do_poisson(numusers, numedge, speed, edge_nodes, time_incr, cur_time, poisson_mean):
    user_ctr = 0
    while user_ctr < numusers:
        num_users_to_create = get_num_users_to_start(poisson_mean)
        print('time = ', cur_time, 'num users to create=', num_users_to_create)
        for i in range(user_ctr, user_ctr + num_users_to_create, 1):
            create_trajectory(numedge, speed, edge_nodes, time_incr, 'user' + str(i) + '.csv', 'user'+str(i), cur_time)
        user_ctr += num_users_to_create
        cur_time += 1
       
if __name__ == '__main__':
    args = parse_args()
    edge_nodes = create_polygon(args.numedgenodes, args.edge, args.lat, args.lon, args.outputfile)
    
    cur_time = 400
    if not args.poisson:
        do_non_overlapping(args.numusers, args.numedgenodes, args.speed, edge_nodes, args.timeincr, cur_time)
    else:
        do_poisson(args.numusers, args.numedgenodes, args.speed, edge_nodes, args.timeincr, cur_time, args.poisson)
    #for i in range(args.numusers):
        #first = edge_nodes[i:]
        #last = []
        #if i > 0:
        #    last = edge_nodes[0:i]
        #print(len(first), len(last))
        #edge_nodes_list = first + last
     #   cur_time = create_trajectory(args.numedgenodes, args.speed, edge_nodes, args.timeincr, 'user' + str(i) + '.csv', 'user' + str(i), cur_time)
