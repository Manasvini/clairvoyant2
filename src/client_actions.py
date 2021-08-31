#!/usr/bin/python3
import grpc
import pandas as pd
import requests
import time
import os
import sklearn.neighbors
import numpy as np
import requests
#from concurrent.futures import ThreadPoolExecutor
import asyncio
import clairvoyant_pb2
import clairvoyant_pb2_grpc
import request_creator
import json

dist = sklearn.neighbors.DistanceMetric.get_metric('haversine')

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

    async def make_request(self):
        request = request_creator.create_user_request(self.id)
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
        return len(self.urls) == len(self.buffer)

    def move(self, cur_time):
        if int(cur_time) >=  max(0, int(self.traj_df.iloc[0]['time']) - 1000) and self.cv_resp == False:
            print(cur_time, self.traj_df.iloc[0]['time'])
            self.cv_resp = True
            start = time.time()
            loop = asyncio.get_event_loop()
            future = asyncio.ensure_future(self.make_request())
            loop.run_until_complete(future)    
            end = time.time()
            print('request took ', (end - start) , ' seconds')
        if self.idx < len(self.traj_df) - 1 and cur_time >= float(self.traj_df.iloc[self.idx]['time']):
            self.idx += self.time_incr
            
            if len(self.buffer) < len(self.urls):
                #self.get_segment(self.urls[len(self.buffer)])
                self.get_segments()
            #else:
            #    self.get_segment(self.default_url)

    def get_delivery_stats(self):
        return {'edgeDelivery': self.receivedBytesEdge, 'cloudDelivery':self.receivedBytesCloud}

    def get_edge_delivery(self):
        return self.receivedBytesEdge
    
    def get_cloud_delivery(self):
        return self.receivedBytesCloud

    def move_playback(self, cur_time):
        if cur_time < float(self.traj_df.iloc[0]['time']) or self.playback >= len(self.urls):
            return None
        if cur_time >= float(self.traj_df.iloc[self.idx]['time']): 
            self.playback += 0.25
    
    def get_distance_from_edge_node(self):
        max_dist = 30 #meters
        
        if self.idx < len(self.dists) and self.dists.iloc[self.idx].min() * 1000 < max_dist:

            min_dist_idx = self.dists.iloc[self.idx].argmin()
            return min_dist_idx, self.dists.iloc[self.idx].min() * 1000
        return -1, 0

    def get_download_speed(self, distance, node_idx):
        if node_idx != -1 and node_idx < len(self.model_map):
            model = self.model_map[node_idx]
            return model.get_download_speed(distance)/8
        return 4e7/8
  
    def get_filepath(self, url):
        http_idx = len('http://')
        filepath_idx = url.find('/', http_idx + 1)
        filepath = url[filepath_idx + 1:]
        return filepath 

    def set_pending_bytes(self, url): 

        filepath = self.get_filepath(url)
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

    def get_segments(self):
        idx, dist = self.get_distance_from_edge_node()
        dl_bytes = (4e7/8) / self.time_scale # 40 Mbps default LTE
        if idx != -1:
            dl_bytes = self.get_download_speed(dist, idx)/self.time_scale
            print('edge contact with node:', idx, 'bytes = ', dl_bytes)
        else:
            #TODO: delay cloud downloads
            if self.playback < len(self.buffer) - 1:
                return

        while len(self.buffer) < len(self.urls) and dl_bytes > 0: 
            url = self.urls[len(self.buffer)]
            filepath = self.get_filepath(url)

            if self.pendingBytes <= 0:
                self.set_pending_bytes(url)

            is_cloud_delivery = True
            new_segment_download = False
            
            if idx != -1:
                if dl_bytes > self.pendingBytes: # Sufficient b/w exists to download segment
                    url = self.get_url(idx, url)
                    resp = self.session.get(url)
                    if '{}' not in resp.text: 
                        # NOTE: "else" needs special handling, because we already sent a GET request
                        dl_bytes -= self.pendingBytes
                        self.count[0] += 1
                        self.receivedBytesEdge += float(self.video_meta[filepath]['size'])
                        new_segment_download = True
                        is_cloud_delivery = False

            if is_cloud_delivery:
                self.pendingBytes -= dl_bytes
                if self.pendingBytes > 0: #next step, as segment not complete
                    break


                dl_bytes = 0 #simplify, and get dl_bytes in next step
                self.count[1] += 1
                self.receivedBytesCloud += float(self.video_meta[filepath]['size'])
                new_segment_download = True

            if new_segment_download == True:
                self.pendingBytes  = 0
                self.buffer.append(url)
            print('cloud:', self.count[1], ' edge:', self.count[0])
     
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
        time.sleep((1.0* self.time_incr) / self.time_scale)
        
        for c in self.clients:
            c.move(self.cur_time)

            if self.cur_time % self.segment_duration == 0:
                c.move_playback(self.cur_time) 
   
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
                    return
        end = time.time()
        print('simulation with', len(self.clients), 'clients took', end - start)
