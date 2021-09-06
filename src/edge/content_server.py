#!/usr/bin/env python
"""
Very simple HTTP server in python (Updated for Python 3.7)
Usage:
    ./dummy-web-server.py -h
    ./dummy-web-server.py -l localhost -p 8000
Send a GET request:
    curl http://localhost:8000
Send a HEAD request:
    curl -I http://localhost:8000
Send a POST request:
    curl -d "foo=bar&bin=baz" http://localhost:8000
This code is available for use under the MIT license.
----
Copyright 2021 Brad Montgomery
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and 
associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial 
portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT 
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.    
"""

import os, time, sys
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import redis
import json
import logging
from concurrent import futures
import threading

def writePidFile():
    pid = str(os.getpid())
    f = open('/tmp/edge_content_svr.pid', 'w')
    f.write(pid)
    f.close()

writePidFile()


redisc = None
#pubsub = redisc.pubsub()
channel = "user_download_notify"
#pubsub.subscribe(channel)

def update_metadata_task(routeid, segment):
    logging.info("Begin Metadata update task | route={}, segement={}".format(routeid, segment))
    msg = "{}|{}".format(routeid, segment)
    redisc.publish(channel, msg)
    logging.info("Metadata updated | route={}, segment={}".format(routeid, segment))

ex = futures.ThreadPoolExecutor(max_workers=5)


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        """This just generates an HTML document that includes `message`
        in the body. Override, or re-write this do do more interesting stuff.
        """
        content = f'<html><body><h1>{message}</h1></body></html>'
        return content.encode("utf8")  # NOTE: must return a bytes object!

    def do_GET(self):
        self._set_headers()
        logging.info(self.path)

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        print(self.path, self.headers)
        routeid = self.headers['token']
        segment = parsed.path[1:] #strip leading '/'
        
        #if redisc.exists(segment):
        #    print('segment', segment, 'exists')
        #    self.send_header(segment, 'exists')
        #else:
        #    print('segment', segment, ' not found')
        #    self.send_header(segment, 'not exists')
        #fullpath = os.path.join(os.getcwd(),segment) #can't use os.path.join if latter string is absolute
        
        #if not os.path.isfile(fullpath):
        #    logging.warning("{} not found".format(segment))
        #    self.wfile.write(self._html("Given segment not a path"))
        #else:
        #    res = ex.submit(update_metadata_task, routeid, segment)
        #    logging.info("Received download | route: {}, segment {}".format(routeid, fullpath))
        #    self.wfile.write(self.getContent(fullpath))
        str_data = {}
        if redisc.exists(segment):
            print('segment', segment, 'exists')
            data = redisc.hgetall(segment)
            print('metadata is ', data)
            for d in data:
                str_data[str(d)] = str(data[d])
                self.send_header(d, data[d])
            self.send_header(segment, 'exists')
            res = ex.submit(update_metadata_task, routeid, segment)
 
        else:
            print('segment', segment, ' not found')
            self.send_header(segment, 'not exists')
        self.end_headers()
        self.send_response(200) 
        
        self.wfile.write(self._html(json.dumps(str_data)))

    def do_HEAD(self):
        self._set_headers()
    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write(self._html("POST!"))

    def getContent(self, content_path): #get raw bytes of segment files
        with open(content_path, mode='rb') as f:
            content = f.read()
        return content

def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="0.0.0.0",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    parser.add_argument(
        "-d",
        "--directory",
        default="/tmp",
        help="Specify serve directory",
        )
    parser.add_argument(
        "-f",
        "--logfile",
        default="/tmp/pyhttp.log",
        help="Filename for logging",
        )
    parser.add_argument(
        "-r",
        "--redis",
        type=str,
        default="localhost",
        help="redis ip",
        )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=6379,
        help="Specify the redis port",
    )
    args = parser.parse_args()
    writePidFile()


    redisc = redis.Redis(host=args.redis, port=args.redis_port)
    pubsub = redisc.pubsub()
    channel = "user_download_notify"
    pubsub.subscribe(channel)

    os.chdir(args.directory)


    #logging
    logging.basicConfig(filename=args.logfile, level=logging.DEBUG)
    #logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    #datefmt='%Y-%m-%d:%H:%M:%S',
    #level=logging.DEBUG)
    run(server_class=ThreadingHTTPServer, addr=args.listen, port=args.port)
