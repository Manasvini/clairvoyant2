package main

import (
  pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
  "google.golang.org/grpc"
  "github.com/golang/glog"
  "context"
  "net"
)

type EdgeDaemon struct {
  pb.UnimplementedEdgeServerServer
  config EdgeConfig
  address string
  grpcServer *grpc.Server
  metamgr *MetadataManager
}


func (daemon *EdgeDaemon) HandleDownloadRequest(ctx context.Context,
    req *pb.DownloadRequest) (*pb.DownloadReply, error) {
  glog.Infof("req token=%d, arrival_time=%d, num_segments=%d", req.TokenId,
      req.ArrivalTime, len(req.Segments))

  //return segments which require downloading
  reply := &pb.DownloadReply{}
  reply.TokenId = req.TokenId

  dc := make(chan []string)
  routeInfo := RouteInfo{
    request : *req,
    doneChannel : dc,
  }

  daemon.metamgr.routeAddChannel <- routeInfo
  glog.Infof("Route Add message sent. Awaiting evictions")

  reply.SegmentIds = <-routeInfo.doneChannel
  glog.Infof("Sending evicted segments")
  return reply, nil
}

func (daemon *EdgeDaemon) start() {
  lis, err := net.Listen("tcp", daemon.address)
  if err != nil {
    glog.Fatalf("EdgeDaemon failed to listen: %v", err)
  }

  //start grpc Edge Server to listen from cloud
  go func(){
    daemon.grpcServer = grpc.NewServer()
    pb.RegisterEdgeServerServer(daemon.grpcServer, daemon)
    glog.Infof("Starting EdgeServerServer")
    daemon.grpcServer.Serve(lis)
  }()
}
