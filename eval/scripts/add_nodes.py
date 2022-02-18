from rediscluster import RedisCluster
import pandas as pd
from optparse import OptionParser
  
startup_nodes = [{"host":"127.0.0.1", "port":"7000"}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)

#nodes_df = pd.read_csv('trafficLights_geo.csv')
#addr_df = pd.read_csv('node_address.csv')
#nodes_df = pd.read_csv('enode_positions/.csv')
def process_args():
    parser = OptionParser()
    parser.add_option("-n", dest="n", type=int, help="number of nodes")
    parser.add_option("-p", dest="prefix", type=str, help="ip prefix, e.g, 10.3.0.")
    parser.add_option("-s", dest="start", type=int, help="ip start")
    parser.add_option("-i", dest="nodeid", type=int, help="id start")
    parser.add_option("-f", dest="filename", type=str, help="nodes file")
    (options, args) = parser.parse_args()
    return options

def main():
    args = process_args()
    nodes_df = pd.read_csv(args.filename)
    #'enode_positions/microbenchmark/' + str(args.n) + 'nodes.csv')
    print(nodes_df)
    for j in range(1000):
        ctr = args.start
        port = 50056
        for i in range(len(nodes_df)):
            lat = nodes_df.iloc[i]['y']
            lon = nodes_df.iloc[i]['x']
            rc.geoadd('nodes' + str(j), lon, lat, 'node_' + str(i + args.nodeid))
            if i > args.n:
                break
    for i in range(len(nodes_df)):
        if i < args.n :
            print("adding ", args.prefix+str(i + ctr) + " address to node " + "node_" + str(i))
                #rc.hset('node_'+ str(i + args.nodeid),None, None, {'address':args.prefix + str(ctr) + ':' + str(port)})
            rc.hset('node_'+ str(i + args.nodeid),None, None, {'address':args.prefix + str(ctr+i) + ':50056'})
                
                #ctr += 1
                #port += 3 
        else:
            break

if __name__=='__main__':
    main()

