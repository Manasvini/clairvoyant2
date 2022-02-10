import sys
import time
import logging
import asyncio
import os
import json
import random

from argparse import ArgumentParser
from rediscluster import RedisCluster

import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc
import grpc

from shared.ModelReader import Model
from client.client_actions import Client, Simulation
import client.request_creator as request_creator

SEGMENT_DURATION_SECONDS = 1.0

logging.basicConfig()
logger = logging.getLogger("client")

def populate_videos():
    startup_nodes = [{"host":"127.0.0.1", "port":"7000"}]
    rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

    videos = ['v' + str(i) for i in range(1, 210)]
    segments = {v: [] for v in videos}
    video_seg_data = {}
    for v in videos:
        segs = rc.lrange(v, 0, -1)
        for s in segs:
            meta = rc.hgetall(s)
            if int(meta['size'])> 0:
                video_seg_data[s] = meta
        
    return video_seg_data

def get_edge_ips(configFile):
    with open(configFile) as fh:
        config = json.load(fh)
    return config['nodeIps']

def get_node_pos(configFile):
    with open(configFile) as fh:
        config = json.load(fh)
    return  '../'+ config['nodePosFile']

    

async def create_request(user_traj):
    request = request_creator.create_user_request(user_traj)
    return {'user': user_traj, 'request':request}


def get_models_map(modelMapFile):
    model_map = {}
    with open(modelMapFile) as fh:
        lines = fh.readlines()
        for l in lines:
            vals = l.strip().split(',')
            model_map[vals[0]] = vals[1]
    return model_map

def get_models(model_node_map, model_dir, n):
    model_map = get_models_map(model_node_map)
    edge_models = []
    for i in model_map:
        edge_models.append(Model(model_dir + '/' + model_map[i]))
    logger.debug(f"model_count={len(edge_models)}")
    return edge_models
 
def create_simulation(users, address,  video_seg_data, outputfile, models, opts):
    
    config = opts.config
    clients = []
    time_incr = 1
    time_scale = 60.0
    simulation_max_steps = 1000000 
    edge_ips = get_edge_ips(config)
    logger.info(f"Edge IPs - {edge_ips}")

    #enode_pos = '../eval/monaco_traffic_lights.csv'
    enode_pos = get_node_pos(config)

    for user in users:
        client = Client(user, enode_pos, address, video_seg_data, time_scale, time_incr, models, edge_ips) 
        clients.append(client)

    if opts.bench2:
        start_offset = opts.bench2
        clients[0].add_route_start_offset(start_offset)
        for client in clients:
            #NOTE: offset not needed for the current config of route.
            #client.add_route_start_offset(start_offset)
            client.set_benchmark_info("bench2")
            #start_offset += 400

        for client in clients:
            logger.debug(f"start_time={client.traj_df['time'].iloc[0]}")
            if opts.bench3:
                client.set_benchmark_info("bench3")

    simulation = Simulation(clients, time_scale, SEGMENT_DURATION_SECONDS, time_incr, outputfile)
    simulation.run_simulation(simulation_max_steps)
    
    for c in clients:
        print('client', c.getId(), 'delivery stats =', c.get_delivery_stats())
    
    simulation.save_to_file()


def process_args():
    parser = ArgumentParser()
    parser.add_argument("-n", dest="n", type=int, help="number of users", default=1)
    parser.add_argument("-f", dest="trajectoriesdir", type=str, help="trajectories directory", required=True)
    parser.add_argument("-u", dest="userids", type=str, nargs='*',action='append', help="user ids", required=False)
    parser.add_argument("-a", dest="address", type=str, help="server address", required=True)
    parser.add_argument('-i', dest='nodeid', type=str, help='requests specific to node id')
    parser.add_argument('-o', dest='outputfile', type=str, help='output file name')
    parser.add_argument('-m', dest='modelmapfile', type=str, help='model map filr')
    parser.add_argument('-d', dest='modeldir', type=str, help='model dir')
    parser.add_argument('-c', dest='config', type=str, help='cloud config file')
    parser.add_argument("--user-file", type=str, help="file containing user ids")

    parser.add_argument("--bench1", type=int, help="benchmark 1, how many concurrent users?")
    parser.add_argument("--bench2", type=int, help="benchmark 2, start offset of first route")
    parser.add_argument("--bench3", type=int, help="benchmark 3")
    

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    opts = process_args()
    traj_dir = opts.trajectoriesdir
    logging.basicConfig(filename='logs/out.log', level=logging.INFO)

    num_users = opts.n
    address = opts.address

    users = []
    if opts.bench1:
        logger.info(f"Running benchmark 1, concurrent users={opts.bench1}")
        users = ["../eval/enode_positions/microbenchmark/bench1/user0_17min.csv"]*opts.bench1
    elif opts.bench2:
        logger.info(f"Running benchmark 2")
        user_dir = "../eval/enode_positions/microbenchmark/bench2/30users"
        files = sorted(os.listdir(user_dir), key=lambda x : int(x.split('.')[0][4:]))
        users = [os.path.join(user_dir, f) for f in files]
    elif opts.bench3:
        logger.info(f"Running benchmark3")
        users = ["../eval/enode_positions/microbenchmark/bench3/user0.csv"]
    else:
        if opts.userids and len(opts.userids) > 0:
            users = [traj_dir + '/' + u[0] + '.csv'  for u in opts.userids]
        elif opts.nodeid and len(opts.nodeid) > 0:
            with open('../eval/route.json') as fh:
                routes_for_node = json.load(fh)
            if opts.nodeid in routes_for_node:
                users = [traj_dir + '/' + user + '.csv' for user in routes_for_node[opts.nodeid]]
            else:
                users = []
        elif opts.user_file:
            try:
                with open(opts.user_file) as fh:
                    inobj = json.loads(fh.read())
                    entries = inobj['lastMile']
                    for entry in entries:
                        tj_file = entry['id'].split('/')[-1]
                        users.append(os.path.join(traj_dir,tj_file))
            except:
                logger.error('Error in reading user file!')
                sys.exit(-1) 
            logger.debug(f"user files len={len(users)}")
        else:
            files = [os.path.join(traj_dir,f) for f in os.listdir(traj_dir) if os.path.isfile(os.path.join(traj_dir, f))] 
            users = random.sample(files, opts.n)
            logger.info('picked %s users', len(users))
            print(users)
    if len(users) == 0:
        logger.warning('no user trajectories found!')


    video_seg_data = populate_videos()

    print('starting simulation')
    #requests = [i for i in info]
    models = get_models(opts.modelmapfile, opts.modeldir, opts.n)
    create_simulation(users, address, video_seg_data, opts.outputfile, models, opts)
