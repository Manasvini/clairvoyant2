package main

import (
	"context"
	"github.com/golang/glog"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"google.golang.org/grpc"
	"net"
)

type EdgeServer struct {
	pb.UnimplementedEdgeServerServer
	config     EdgeConfig
	address    string
	grpcServer *grpc.Server
	metamgr    *MetadataManager
}

func (server *EdgeServer) HandleDownloadRequest(ctx context.Context,
	req *pb.DownloadRequest) (*pb.DownloadReply, error) {
	glog.Infof("req token=%d, arrival_time=%d, num_segments=%d", req.TokenId,
		req.ArrivalTime, len(req.Segments))

	//return segments which require downloading
	reply := &pb.DownloadReply{}
	reply.TokenId = req.TokenId

	dc := make(chan []string)
	routeInfo := RouteInfo{
		request:     *req,
		doneChannel: dc,
	}

	server.metamgr.routeAddChannel <- routeInfo
	glog.Infof("Route Add message sent fo %d. Awaiting evictions", routeInfo.request.TokenId)

	reply.SegmentIds = <-routeInfo.doneChannel
	glog.Infof("Sending evicted segments")
	return reply, nil
}

func (server *EdgeServer) start() {
	lis, err := net.Listen("tcp", server.address)
	if err != nil {
		glog.Fatalf("EdgeServer failed to listen: %v", err)
	}

	//start grpc Edge Server to listen from cloud
	go func() {
		server.grpcServer = grpc.NewServer()
		pb.RegisterEdgeServerServer(server.grpcServer, server)
		glog.Infof("Starting EdgeServerServer")
		server.grpcServer.Serve(lis)
	}()
}
