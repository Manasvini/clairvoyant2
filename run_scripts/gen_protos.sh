protoc --go_out=../src/edge_go/contentserver/ --go_opt=paths=source_relative \
       --go-grpc_out=../src/edge_go/contentserver/ --go-grpc_opt=paths=source_relative \
       -I ~/clairvoyant2/protos/ contentserver.proto

protoc --python_out=../src/genprotos clairvoyant.proto
