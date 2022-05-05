package main

import (
	"context"
	"net"

	"github.com/golang/glog"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"google.golang.org/grpc"
)

type EdgeServer struct {
	pb.UnimplementedEdgeServerServer
	config     EdgeConfig
	address    string
	grpcServer *grpc.Server
	metamgr    *MetadataManager
}

func (server *EdgeServer) HandleUpdateClock(ctx context.Context,
	req *pb.ClockUpdateRequest) (*pb.ClockUpdateReply, error) {
	// glog.Infof("update clock request start, new time = %d", req.NewClock)

	oldClock := server.metamgr.clock.UpdateTime(req.NewClock)

	// glog.Infof("update clock request complete, old time = %d,new time = %d", oldClock, req.NewClock)

	return &pb.ClockUpdateReply{OldClock: oldClock}, nil
}

func (server *EdgeServer) HandleDownloadRequest(ctx context.Context,
	req *pb.DownloadRequest) (*pb.DownloadReply, error) {
	glog.Infof("req token=%d, arrival_time=%d, num_segments=%d", req.TokenId,
		req.ArrivalTime, len(req.Segments))

	//return segments which require downloading
	//reply := &pb.DownloadReply{}
	//reply.TokenId = req.TokenId

	dc := make(chan *pb.DownloadReply)
	routeInfo := RouteInfo{
		request:     *req,
		doneChannel: dc,
	}

	server.metamgr.routeAddChannel <- routeInfo
	glog.Infof("Route Add message sent fo %d. Awaiting evictions", routeInfo.request.TokenId)

	reply := <-routeInfo.doneChannel
	glog.Infof("Sending evicted and committed segments")
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
