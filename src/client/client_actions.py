#!/usr/bin/python3
import grpc
import requests
import time
import os, logging
import sklearn.neighbors
import requests
import asyncio
import json
import pandas as pd
import numpy as np


import genprotos.clairvoyant_pb2 as clairvoyant_pb2
import genprotos.clairvoyant_pb2_grpc as clairvoyant_pb2_grpc
import client.request_creator as request_creator
from client.clock import CVClock, ClockEndException

dist = sklearn.neighbors.DistanceMetric.get_metric('haversine')

logger = logging.getLogger("client")
logger.setLevel(logging.DEBUG)

LTE_SPEED = 4e7 #40Mbps

class Client:
    def __init__(self, filename, edgenodes_file, address, video_meta, time_scale, time_incr, models, edge_ips):

        self.video_meta = video_meta
        self.traj_df = pd.read_csv(filename)

        self.idx = 0
        self.playback = 0
        self.urls = []
        self.edge_node_positions = pd.read_csv(edgenodes_file)
        self.default_url = 'http://ftp.itec.aau.at/DASHDataset2014'
        self.edge_node_positions[['lat_rad_A', 'lon_rad_A']] = np.radians(self.edge_node_positions.loc[:,['y','x']])
        self.traj_df[['lat_rad', 'lon_rad']] = np.radians(self.traj_df.loc[:,['y','x']])

        # calculates pairwise distance between route points and edge nodes in km
        dist_matrix = (dist.pairwise(self.traj_df[['lat_rad', 'lon_rad']], self.edge_node_positions[['lat_rad_A', 'lon_rad_A']])) * 6400

        self.dists = pd.DataFrame(dist_matrix)
        self.buffer = []
        self.session = requests.Session()
        #self.session.headers.update({'token':str(tokenid)})
        self.pendingBytes = 0
        self.receivedBytesEdge = 0
        self.receivedBytesCloud = 0
        self.id = filename
        self.address = address

        self.time_incr = time_incr
        self.time_scale = time_scale
        self.cv_resp = False
        self.model_map = models
        self.edge_ips = {n : edge_ips[n][:edge_ips[n].find(':')] for n in edge_ips}
        self.edge_idxs = {i: 'node_' + str(i) for i in range(len(self.edge_node_positions))}

        #debug
        self.count = [0,0]
        self.edge_dlBytes = 0

        #get_segments
        self.last_node = -1
        self.availBits = 0
        self.last_dist = -1
        self.time_of_last_dist = 0
        self.buffer_set = set()

        self.is_complete = False

        self.token = None
        #scaling
        #self.traj_df['time'] = 2*self.traj_df['time']
        
        self.bench_info = None


    def set_benchmark_info(self, info):
        self.bench_info = info

    def add_route_start_offset(self, offset):
        self.traj_df['time'] += offset

    def make_request(self, request_timestamp):
        if self.bench_info == "bench2":
            request = request_creator.create_request(self.traj_df, request_timestamp, dont_random=True)
        else:
            request = request_creator.create_request(self.traj_df, request_timestamp)

        with grpc.insecure_channel(self.address) as channel:
            stub = clairvoyant_pb2_grpc.CVServerStub(channel)
            response = stub.HandleCVRequest(request)
            self.session.headers.update({'token':str(response.videoreply.token_id)})
            self.urls = response.videoreply.urls
            logger.info(f"client={self.id}, urls_len={len(self.urls)},\
                    token={response.videoreply.token_id}")
            self.token = response.videoreply.token_id

    def getId(self):
        return self.id

    def download_complete(self):
        return (self.cv_resp == True and len(self.urls) == len(self.buffer))

    def add_token_to_logger(self):
        logger.propagate = False
        logger.addHandler(logging.StreamHandler())
        formatter = logging.Formatter(f"%(levelname)s:%(name)s: routeid={self.token} -  %(message)s")
        logger.handlers[0].setFormatter(formatter)

    def move(self, cur_time):
        if self.is_complete:
            return

        if self.cv_resp == False and \
                int(cur_time) >=  max(0, int(self.traj_df.iloc[0]['time']) - 100):
            # Make a request only only after you are 1000 seconds before travel
            logger.debug("current_time: {}, journey_start_time: {}"
                    .format(cur_time, self.traj_df.iloc[0]['time']))
            start = time.time()
            self.make_request(cur_time)
            end = time.time()
            self.cv_resp = True

            logger.info(f"client={self.token},  request duration={(end - start)}")

            if self.bench_info == "bench2":
                self.is_complete = True
                return

         
        if self.idx < len(self.traj_df) and \
                cur_time >= float(self.traj_df.iloc[self.idx]['time']):

            while self.idx < len(self.traj_df) and \
                    float(self.traj_df.iloc[self.idx]['time']) == cur_time:
                #traverse trajectory at cur_time
                if len(self.buffer) < len(self.urls):
                    self.get_segments(self.traj_df.iloc[self.idx]['time'])
                self.idx += 1#self.time_incr

        if self.idx >= len(self.traj_df):
            self.is_complete = True
            logger.info(f"client={self.id} journey ended")



    def get_delivery_stats(self):
        logger.debug(f"len_buffer:{len(self.buffer)}")
        print("dlBytes", self.edge_dlBytes)
        return {'edgeDelivery': self.receivedBytesEdge, 'cloudDelivery':self.receivedBytesCloud}

    def get_edge_delivery(self):
        return self.receivedBytesEdge
    
    def get_cloud_delivery(self):
        return self.receivedBytesCloud

    def move_playback(self, cur_time):
        if cur_time < float(self.traj_df.iloc[0]['time']) or self.playback >= len(self.urls):
            return None
        if cur_time >= float(self.traj_df.iloc[0]['time']): 
            self.playback += 1
    
    def get_distance_from_nearest_edge_node(self):
        max_dist = 32 #30 meters, but allow room for error 2 meters
        
        if self.idx < len(self.dists) and self.dists.iloc[self.idx].min() * 1000 < max_dist:

            min_dist_node_idx = self.dists.iloc[self.idx].argmin()

            row = self.traj_df.iloc[self.idx]
            cur_dist = self.dists.iloc[self.idx].min()
            #logger.debug(f"node{min_dist_node_idx}, idx{self.idx}, contact points ({row['x']},{row['y']}), dist: {cur_dist}")

            return min_dist_node_idx, self.dists.iloc[self.idx].min() * 1000
        return -1, 0

    def get_download_speed(self, distance, node_idx): #in bps
        speed = LTE_SPEED
        if node_idx < len(self.model_map):
            model = self.model_map[node_idx]
            speed = model.get_download_speed(distance)
        else:
            logger.error('node {} does not exist for speed calculation'.format(node_idx))

        return speed

  
    def get_filepath(self, url):
        http_idx = len('http://')
        filepath_idx = url.find('/', http_idx + 1)
        if "ftp" in url: # cloud path
            prefix = "http://ftp.itec.aau.at/DASHDataset2014/"
            filepath = url[len(prefix):]
        else:
            filepath = url[filepath_idx + 1:]
        return filepath 

    def set_pending_bytes(self, url): 

        filepath = self.get_filepath(url)
        with open('debug.json','w') as fh:
            fh.write(json.dumps(self.video_meta, indent=2))
        if filepath not in self.video_meta:
            print(filepath, ' not found')
            return None
        if self.pendingBytes <= 0 and  len(self.buffer) < len(self.urls) :
            self.pendingBytes = int(self.video_meta[filepath]['size']) /self.time_scale
        return filepath
 
    def get_ip_from_url(self, url):
        start_idx = url.find('://') + 3
        end_idx = start_idx + url[start_idx:].find(':')
        return url[start_idx:end_idx], start_idx, end_idx
   
    def get_url(self, node_idx, url):
        ip = self.edge_ips['node_' + str(node_idx)]

        start_idx =  url.find('://') + 3
        end_idx =  start_idx + url[start_idx:].find(':')
        new_url = url[0:start_idx] + ip + url[end_idx:] 
        print(url, new_url)
        return new_url

    def make_edge_request(self, node_idx, segment=None, reset=False):
        ip = self.edge_ips['node_' + str(node_idx)]
        url = f"http://{ip}:8000"

        if reset:
            logger.info('Reset contact history, as no segments to fetch')
            params = {"reset":True}

        elif segment == None:
            logger.info('First request to edge')

            # HACK: weird fix to get the key. TODO: make it more streamlined
            splits = self.urls[0].split('/')
            for part in splits:
                if 'BigBuckBunny' in part:
                    key = part
                    break

            params = {"key": key, \
                    "start_time": self.start_contact_time, \
                    "end_time": self.end_contact_time}
        else:
            #logger.debug(f"request to segment={segment}")
            params = {"segment":segment}

        resp = self.session.get(url, params=params)
        time.sleep(0.01)

        return resp.json()


    def complete_edge_actions(self):

        #add last_dist (TODO: experiment with this)
        bits = self.get_download_speed(self.last_dist, self.last_node)
        self.availBits += bits
        logger.debug(f"Accumulate for dist={self.last_dist}, time=1, bits={bits}")
        logger.info(f"availableBytes to download for node {self.last_node} = {self.availBits/8}")
        totalBytes = self.availBits / 8

        #get list of segments available at edge:
        res = self.make_edge_request(self.last_node)

        to_download = []
        if 'segments' in res:
            segments = res['segments']
            for seg in segments:
                if seg not in self.buffer_set:
                    to_download.append(seg)

        logger.info(f"client={self.token}, to_download={len(to_download)}")
        if len(to_download) == 0:
            logger.info('no data on edge avaialable')
            if 'error' in res:
                logger.info(f"{res['error']}")
            self.make_edge_request(self.last_node, reset=True)
            return
        
        idx = 0
        if self.bench_info == "bench3":
            #sort to_download for data set
            def sorter(x):
                tokens = x.split('.')
                target = tokens[1]
                comp = target.split('-')
                minor = int(comp[1][1:])
                major = int(comp[0][3:])

                return major, minor

            import pdb; pdb.set_trace()
            to_download = list(sorted(to_download, key=sorter))
        


        dcount = 0

        while totalBytes >=0 and idx < len(to_download):
            cur_seg = to_download[idx]
            filesize = float(self.video_meta[cur_seg]['size'])
            if filesize < totalBytes:
                res = self.make_edge_request(self.last_node, cur_seg)
                if '{}' in res:
                    logger.error(f"missing segment on edge={self.last_node}")
                else:
                    totalBytes -= filesize
                    self.buffer_set.add(cur_seg)
                    self.count[1] += 1
                    dcount = 1
                    self.receivedBytesEdge += filesize
            else:
                totalBytes = -1 # not enough bytes
            idx += 1
        if dcount:
            logger.debug(f"client={self.token} | counts - cloud: {self.count[0]} | edge: {self.count[1]}")
        

    def need_cloud(self, url, segment):
        if segment in self.buffer_set:
            self.buffer.append(url)
            return False

        return True

    def get_segments(self, timestamp):
        node_id, act_dist = self.get_distance_from_nearest_edge_node()
        
        if node_id == -1:
            # Complete any pending tasks of the last valid edge
            if self.last_node != -1:
                self.complete_edge_actions()
                self.last_node = -1

            """
            NOTE: Download segments from cloud, don't need to worry about keeping time of the download.
            Once cloud starts, edge can't take over mid segment. 
            Playback check ensures next segment isn't downloaded until duly required, 
            and at that time edge contact is also checked.
            """
            # Implies a cloud delivery
            while len(self.buffer) <= len(self.urls) and self.playback+30 >= len(self.buffer):
                """
                the while loop to catch up to playback with cloud downloads.
                I know, it doesn't make sense for playback to cross buffer. 
                But this is simulation where we don't do anything to buffer when connected to edge.
                Alternate approach: check if cloud download needed after every edge action.
                """
                url = self.urls[len(self.buffer)]
                filepath = self.get_filepath(url)

                if not self.need_cloud(url, filepath):
                    #fill from edge buffer_set
                    continue

                self.receivedBytesCloud += float(self.video_meta[filepath]['size'])
                self.buffer.append(url)
                self.buffer_set.add(filepath)
                self.count[0] += 1
                #if self.count[0]%100 == 0:
                import pdb; pdb.set_trace()
                logger.debug(f"client={self.token} | counts - cloud: {self.count[0]} | edge: {self.count[1]} | time: {self.traj_df.iloc[self.idx]['time']}")

        else:
            #if node_id != 0:
            dist = self.model_map[node_id].get_model_dist(act_dist)
            if self.last_node == -1: #first time node encounter after gap
                self.availBits = 0
                self.last_dist = dist
                self.time_of_last_dist = timestamp
                self.last_node = node_id

                #need this to inform edge server of when i am asking for content
                self.start_contact_time = timestamp

            elif self.last_node != node_id: # no cloud gap between 2 edge nodes
                #need this to inform edge server of when i am asking for content
                self.end_contact_time = timestamp
                self.complete_edge_actions()
                self.availBits = 0 
                self.last_node = node_id
                self.last_dist = dist
                self.time_of_last_dist = dist

            else: # accumulate bytes as long as you are in contact with node.
                #TODO: need to handle special cases like single point of contact with node
                # or last point of contact
                if dist != self.last_dist:
                    point_contact_time = timestamp - self.time_of_last_dist
                    bits = 0
                    if point_contact_time == 0:
                        bits = self.get_download_speed(self.last_dist, self.last_node)
                    else:
                        bits = self.get_download_speed(self.last_dist, self.last_node)*point_contact_time

                    self.availBits += bits

                    logger.debug(f"Accumulate for traj_i={self.idx}, dist={self.last_dist}, time={point_contact_time}, bits={bits}")
                    self.last_dist = dist
                    self.time_of_last_dist = timestamp
                
                    #need this to inform edge server of when i am asking for content
                    self.end_contact_time = timestamp


class Simulation:
    def __init__(self, clients, time_scale, segment_duration, time_incr, outputfile):
        self.clients = clients
        self.time_scale = time_scale
        self.cur_time = 0
        self.segment_duration = segment_duration
        self.time_incr = time_incr
        self.outputfile = outputfile



    def simulate_step(self):
        #if self.cur_time % (1.0/self.time_incr) == 0:
        #time.sleep((1.0* self.time_incr) / self.time_scale)
        
        for c in self.clients:
            c.move(self.cur_time)
            c.move_playback(self.cur_time) 
            #if self.cur_time % self.segment_duration == 0:
   
    def save_to_file(self):
        output = [{'id': client.getId(), 'edge':client.get_edge_delivery(), 'cloud':client.get_cloud_delivery()} for client in self.clients]
        with open(self.outputfile, 'w') as ofh:
            json.dump(output, ofh, indent=2)

    def clients_are_complete(self):
        res = []

        for client in self.clients:
            res.append(client.download_complete())
            res[-1] = client.is_complete
            if res[-1]:
                if client.idx < len(client.traj_df):
                    logger.info(f"client={client.token} complete, last_time={client.traj_df.iloc[client.idx]['time']}")

        return all(res)

    def run_simulation(self, num_steps):
        start = time.time()
        clock = CVClock(time_incr=self.time_incr, end_of_time=num_steps)
        while self.cur_time < num_steps:
            time.sleep(0.01)
            self.cur_time = clock.advance()
            self.simulate_step()
            if self.cur_time % 100 == 0:
                logger.info(f"Ran simulation step = {self.cur_time}")
                if self.clients_are_complete():
                    logger.info("All client downloads are complete")
                    try:
                        clock.shutdown()
                    except ClockEndException:
                        pass
                    return
        end = time.time()
        print('simulation with', len(self.clients), 'clients took', end - start)

