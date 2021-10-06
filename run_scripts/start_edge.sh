#single node
#python src/edge_runner.py -a 0.0.0.0:51050 -c conf/edgeConfig.json

#2 node
id=$1
python3 src/edge_runner.py -a 0.0.0.0:50056 -c conf/edgeConfig$1.json
