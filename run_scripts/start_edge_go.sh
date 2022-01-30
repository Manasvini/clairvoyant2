
#single node
#python src/edge_runner.py -a 0.0.0.0:51050 -c conf/edgeConfig.json

#2 node
#python3 src/edge_runner.py -a 0.0.0.0:50056 -c conf/edgeConfig$1.json
PATH=$PATH:/usr/local/go/bin
echo "pwd is $PWD"
cd src/edge_go
/usr/local/go/bin/go run . -config ../../conf/edgeConfig.json > ../../logs.edge.out 2>&1 & 
