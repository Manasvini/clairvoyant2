from argparse import ArgumentParser
import logging

from client.clock import CVClock

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-a', '--address', dest='address', type=str, help='port')
    parser.add_argument('-s', '--start_time', dest='start_time', type=int, help='port')
    parser.add_argument('-i', '--time_incr', dest='time_incr', type=int, help='port')
    parser.add_argument('-c', '--config', dest='config', type=str, help='config file')
    args = parser.parse_args()
    return args

def create_cv_clock(start_time, incr, cloud_config):
    cvServer = CVClock(start_time, incr, cloud_config, is_thread=False)
    return cvServer

def main():
    args = parse_args()
    print("it's alive")
    logging.basicConfig(level=logging.INFO)
    cvServer = create_cv_clock(args.start_time, args.time_incr, args.config) 
    cvServer.serve()

if __name__=='__main__':
    main()
