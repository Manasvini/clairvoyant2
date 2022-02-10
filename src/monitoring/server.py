
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
import json
import logging
import threading

if __name__ == "__main__":
    from os import path
    sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )
from shared.EdgeNetworkModel import EdgeNetworkModel

logging.basicConfig()
logger = logging.getLogger("monitoring")
logger.setLevel(logging.INFO)

class MonitoringHandler(BaseHTTPRequestHandler):
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
        self.send_response(401) 
        
        self.wfile.write(self._html(json.dumps(str_data)))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        logger.debug("received post")
        self._set_headers()
        content_len = int(self.headers.get('content-length'))
        post_body = self.rfile.read(content_len)
        post_dict = json.loads(post_body)
        model_dict = post_dict['model']
        node_id  = post_dict['nodeid']
        self.server.edge_model_dict[node_id].update(model_dict, time.time())
        logger.debug('Updated model successfully!')

        self.end_headers()
        self.send_response(201) 
        #self.wfile.write(self._html("POST!"))

    def getContent(self, content_path): #get raw bytes of segment files
        with open(content_path, mode='rb') as f:
            content = f.read()
        return content

    def log_message(self, format, *args):
        with open('/tmp/monitoring_httpd.log', 'w') as fh:
            fh.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format%args))


"""
Ideally run this in a different thread.
"""
class MonitoringServer:
    def __init__(self, address, port, edge_model_dict): #default monitoring port = 8192
        self.address = address
        self.port = port
        self.edge_model_dict = edge_model_dict
        
        #can make this non hardcoded
        self.server_class = ThreadingHTTPServer

    def run(self): # TODO:potentially run this within the constructor 
        
        self.httpd = self.server_class((self.address, self.port), MonitoringHandler)
        self.httpd.edge_model_dict = self.edge_model_dict
        print("Starting Moniroring httpd server on {}:{}".format(self.address, self.port))
        self.httpd.serve_forever()

    def shutdown(self):
        self.httpd.shutdown()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run Monitoring Service") 
    parser.add_argument(
        "-a",
        "--address",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8192,
        help="Specify the port on which the server listens",
    )
    parser.add_argument(
        "-f",
        "--logfile",
        default="/tmp/pyhttp.log",
        help="Filename for logging",
    )
    args = parser.parse_args()
    temp_dict = {'node_1':EdgeNetworkModel('node_1')}
    monserver = MonitoringServer(address=args.address, port=args.port, edge_model_dict=temp_dict)
    monserver.run()
