#single node
#python src/edge_runner.py -a 0.0.0.0:51050 -c conf/edgeConfig.json

#2 node
id=$1
python src/edge_runner.py -a 0.0.0.0:5105$id -c conf/n${id}_edgeConfig.json
