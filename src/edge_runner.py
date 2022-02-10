import asyncio
import logging
from argparse import ArgumentParser
from edge.EdgeDownloadServer import EdgeDownloadServer, serve

def create_dl_server(filename):
    dlServer = EdgeDownloadServer(filename)
    return dlServer

        
def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='config', type=str, help='config file')
    parser.add_argument('-a', '--address', dest='address', type=str, help='config file')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    dlServer = create_dl_server(args.config)
    asyncio.run(serve(dlServer, args.address))
     


if __name__=='__main__':
    main()
