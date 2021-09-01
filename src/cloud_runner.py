from argparse import ArgumentParser
import asyncio
import logging

from cloud.CVCloudServer import CVCloudServer, serve

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', type=str, help='config file')
    parser.add_argument('-a', '--address', dest='address', type=str, help='config file')
    args = parser.parse_args()
    return args

def create_cv_server(filename):
    cvServer = CVCloudServer(filename)
    return cvServer

def main():
    args = parse_args()
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    cvServer = create_cv_server(args.config) 
    asyncio.run(serve(args.address, cvServer))

if __name__=='__main__':
    main()
