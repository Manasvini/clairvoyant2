import clairvoyant_pb2_grpc
import clairvoyant_pb2
import grpc
import logging
import asyncio
import time
import requests

class CVCloudClient:    
    def __init__(self, address):
        self.address = address
        self.session = requests.Session()
        self.urls = []
    def make_request(self):
        
        request = clairvoyant_pb2.CVRequest()
        videoReq = clairvoyant_pb2.VideoRequest()
        videoReq.video_id = 'v1'
        route = clairvoyant_pb2.Route()
        pts = [(7.48379, 43.765967), (7.4837299, 43.765964), (7.4836400, 43.765961), (7.4837630, 43.765964)]
        ctr = time.time_ns()/1e9 + 100
        for p in pts:
            point = route.points.add()
            point.x = p[0]
            point.y = p[1]
            point.time = ctr /60
            ctr += 1
        videoReq.route.CopyFrom(route)
        request.videorequest.CopyFrom(videoReq)
        start = time.time()
        with grpc.insecure_channel(self.address) as channel:
            stub = clairvoyant_pb2_grpc.CVServerStub(channel)
            response = stub.HandleCVRequest(request)

#            self.session.headers.update({'token':str(response.videoreply.token_id)})
            self.urls = response.videoreply.urls
            print('have ' , len(response.videoreply.urls) , ' token is ', response.videoreply.token_id)
            self.session.headers.update({'token':str(response.videoreply.token_id)})
#print(self.urls)
        end = time.time()
        i = 0   
        for url in self.urls:
            print('fetching', url)
            self.session.get(url)
            if i== 10:
                break
            i +=1
        print('request took', (end-start), 'seconds')
if __name__=='__main__':
    client = CVCloudClient('localhost:50058')
    client.make_request() 
