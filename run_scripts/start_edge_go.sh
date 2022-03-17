#PATH=$PATH:/usr/local/go/bin
echo "pwd is $PWD"
cd src/edge_go
rm ../../logs.edge.out
#/usr/local/go/bin/go run . -config ../../conf/edgeConfig.json  -log_dir ./ > ../../logs.edge.out 2>&1 & 
#binary is built already
./edge_go -config ../../conf/edgeConfig.json  -log_dir ./ > ../../logs.edge.out 2>&1 & 
