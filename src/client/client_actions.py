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
        self.traj_df['time'] = 2*self.traj_df['time']
        #self.traj_df['time'] = self.traj_df['scaled_time']
        #import pdb; pdb.set_trace()

    async def make_request(self, request_timestamp):
        request = request_creator.create_request(self.traj_df, request_timestamp)
        #request = request_creator.create_user_request(self.id, request_timestamp)
        async with grpc.aio.insecure_channel(self.address) as channel:
            stub = clairvoyant_pb2_grpc.CVServerStub(channel)
            response = await stub.HandleCVRequest(request)

            self.session.headers.update({'token':str(response.videoreply.token_id)})
            self.urls = response.videoreply.urls
            print('have ' , len(self.urls) , ' for client client id ', self.id, ' token is ', response.videoreply.token_id)
            #print(self.urls)
    def getId(self):
        return self.id

    def download_complete(self):
        return (self.cv_resp == True and len(self.urls) == len(self.buffer))

    def move(self, cur_time):

        if self.cv_resp == False and \
                int(cur_time) >=  max(0, int(self.traj_df.iloc[0]['time']) - 100):
            # Make a request only only after you are 1000 seconds before travel
            logger.debug("current_time: {}, journey_start_time: {}"
                    .format(cur_time, self.traj_df.iloc[0]['time']))
            self.cv_resp = True
            start = time.time()
            loop = asyncio.get_event_loop()
            future = asyncio.ensure_future(self.make_request(cur_time))
            loop.run_until_complete(future)    
            end = time.time()
            logger.info('Client {} request duration '.format(self.id, (end - start)))

         
        if self.idx < len(self.traj_df) - 1 and \
                cur_time >= float(self.traj_df.iloc[self.idx]['time']):
            while float(self.traj_df.iloc[self.idx]['time']) <= cur_time:
                #catch up trajectory with the cur_time
                if len(self.buffer) < len(self.urls):
                    self.get_segments(self.traj_df.iloc[self.idx]['time'])
                self.idx += self.time_incr

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
            self.playback += 1#0.25
    
    def get_distance_from_nearest_edge_node(self):
        max_dist = 30 #meters
        
        if self.idx < len(self.dists) and self.dists.iloc[self.idx].min() * 1000 < max_dist:

            min_dist_node_idx = self.dists.iloc[self.idx].argmin()

            row = self.traj_df.iloc[self.idx]
            cur_dist = self.dists.iloc[self.idx].min()
            logger.debug(f"node{min_dist_node_idx}, idx{self.idx}, contact points ({row['x']},{row['y']}), dist: {cur_dist}")

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

    def complete_edge_actions(self):

        #add last_dist (TODO: experiment with this)
        bits = self.get_download_speed(self.last_dist, self.last_node)
        self.availBits += bits
        logger.debug(f"Accumulate for dist={self.last_dist}, time=1, bits={bits}")
        logger.info(f"availableBits to download for node {self.last_node} = {self.availBits}")
        totalBytes = self.availBits / 8
        while totalBytes >= 0:
            url = self.urls[len(self.buffer)]
            filepath = self.get_filepath(url)
            filesize = float(self.video_meta[filepath]['size'])
            if filesize < totalBytes:
                self.receivedBytesEdge += filesize
                self.buffer.append(url)
                url = self.get_url(self.last_node, url)
                resp = self.session.get(url)
                totalBytes -= filesize
                self.count[1] += 1
                logger.debug("counts - cloud: {} | edge: {}".format(self.count[0], self.count[1]))
            else:
                totalBytes = -1

    def get_segments(self, timestamp):
        node_id, act_dist = self.get_distance_from_nearest_edge_node()
        

        if node_id == -1:
            # Complete any pending tasks of the last valid edge
            if self.last_node != -1:
                self.complete_edge_actions()
                self.last_node = -1

            # Implies a cloud delivery
            if self.playback < len(self.buffer) - 1:
                #delay cloud downloads
                return

            """
            NOTE: Download segments from cloud, don't need to worry about keeping time of the download.
            Once cloud starts, edge can't take over mid segment. 
            Playback check ensures next segment isn't downloaded until duly required, 
            and at that time edge contact is also checked.
            """
            url = self.urls[len(self.buffer)]
            filepath = self.get_filepath(url)
            self.receivedBytesCloud += float(self.video_meta[filepath]['size'])
            self.buffer.append(url)
            self.count[0] += 1
            logger.debug("counts - cloud: {} | edge: {}".format(self.count[0], self.count[1]))

        else:
            dist = self.model_map[node_id].get_model_dist(act_dist)
            if self.last_node == -1: #first time node encounter after gap
                self.availBits = 0
                self.last_dist = dist
                self.time_of_last_dist = timestamp
                self.last_node = node_id

            elif self.last_node != node_id: # no cloud gap between 2 edge nodes
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

                    logger.debug(f"Accumulate for dist={self.last_dist}, time={point_contact_time}, bits={bits}")
                    self.last_dist = dist
                    self.time_of_last_dist = timestamp


    #def get_segments(self):
    #    node_id, dist = self.get_distance_from_nearest_edge_node()

    #    dl_bytes = LTE_SPEED

    #    if idx != -1:
    #        dl_bytes = self.get_download_speed(dist, idx)
    #        self.edge_dlBytes += dl_bytes
    #    else:
    #        #delay only cloud downloads
    #        if self.playback < len(self.buffer) - 1:
    #            return
    #        is_cloud_delivery = True

    #    while len(self.buffer) < len(self.urls) and dl_bytes > 0: 
    #        url = self.urls[len(self.buffer)]
    #        filepath = self.get_filepath(url)

    #        if self.pendingBytes <= 0:
    #            self.set_pending_bytes(url)

    #        is_cloud_delivery = True
    #        new_segment_download = False
    #        
    #        if idx != -1:
    #            if dl_bytes > self.pendingBytes: # Sufficient b/w exists to download segment
    #                url = self.get_url(idx, url)
    #                resp = self.session.get(url)
    #                if '{}' not in resp.text: 
    #                    # NOTE: "else" needs special handling, because we already sent a GET request
    #                    dl_bytes -= self.pendingBytes
    #                    self.count[0] += 1
    #                    self.receivedBytesEdge += float(self.video_meta[filepath]['size'])
    #                    new_segment_download = True
    #                    is_cloud_delivery = False

    #        if is_cloud_delivery:
    #            self.pendingBytes -= dl_bytes
    #            if self.pendingBytes > 0: #next step, as segment not complete
    #                break


    #            dl_bytes = 0 #simplify, and get dl_bytes in next step
    #            self.count[1] += 1
    #            self.receivedBytesCloud += float(self.video_meta[filepath]['size'])
    #            new_segment_download = True

    #        if new_segment_download == True:
    #            self.pendingBytes  = 0
    #            self.buffer.append(url)
    #        print('cloud:', self.count[1], ' edge:', self.count[0])
     
    #def get_segments(self):    
    #    is_edge_delivery = False
    #    idx, dist = self.get_distance_from_edge_node()
 
    #    #if self.pendingBytes > 0:
    #    dl_bytes = (4e7/8) / self.time_scale
    #    if idx != -1:
    #       dl_bytes = self.get_download_speed(dist, idx)/self.time_scale
    #       print('edge contact:', idx, 'bytes = ', dl_bytes)
    #    
    #    while len(self.buffer) < len(self.urls) and dl_bytes > 0:   
    #        is_edge_delivery = False 
    #        url = self.urls[len(self.buffer)]
    #        filepath = self.get_filepath(url)

    #        if self.pendingBytes <= 0:
    #            self.set_pending_bytes(url)
    #        ip, start_idx, end_idx = self.get_ip_from_url(url)
    #        if self.pendingBytes > dl_bytes:
    #            self.pendingBytes -= dl_bytes
    #            break

    #        if 'ftp' not in url and idx != -1 and ('node_' + str(idx) in self.edge_ips):
    #            if ip != self.edge_ips['node_' + str(idx)]:
    #                url = url[:start_idx] + ip + url[end_idx:]
    #                print('new url is ', url)
    #            print('url to query is ', url)
    #            resp = self.session.get(url)

    #            if '{}' not in resp.text:
    #                is_edge_delivery = True
    #            else:
    #                print('did not find ' , url, ' at edge node ', idx)
    #        else:
    #             
    #            if is_edge_delivery:
    #                dl_bytes -= self.pendingBytes
    #            
    #                print('segment', filepath, ' from edge')
    #                self.receivedBytesEdge += float(self.video_meta[filepath]['size'])
    #            else:
    #                if self.playback < len(self.buffer) - 1:
    #                    break
    #                else:
    #                    dl_bytes -= self.pendingBytes
    #                    print('segment', filepath, ' from cloud')
    #                    self.receivedBytesCloud += float(self.video_meta[filepath]['size']) 
    #        self.pendingBytes  = 0
    #        self.buffer.append(url)
    #        print('url is ', url)

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
        for client in self.clients:
            if not client.download_complete():
                return False

        return True
 
    def run_simulation(self, num_steps):
        i = 0
        start = time.time()
        while i < num_steps:
            self.simulate_step()
            #loop = asyncio.get_event_loop()
            #future = asyncio.ensure_future(self.simulate_step_async())
            #loop.run_until_complete(future)
            i += self.time_incr
            self.cur_time = i
            if i % 100 == 0:
                print('Ran simulation step', i)
                if self.clients_are_complete():
                    logger.info("All client downloads are complete")
                    return
        end = time.time()
        print('simulation with', len(self.clients), 'clients took', end - start)

