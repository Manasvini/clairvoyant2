package main

import (
	"context"
	"net"
	"sync"

	"github.com/golang/glog"
	//cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	pb "github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver"
	"google.golang.org/grpc"
)

type ContentServer struct {
	pb.UnimplementedContentServer
	address    string
	grpcServer *grpc.Server
	metamgr    *MetadataManager

	maxClients     int
	contactHistory map[int64][]int64
	mu             sync.Mutex
}

func (server *ContentServer) canMakeContact(routeId, start, end int64) bool {
	isBusy := true
	server.mu.Lock()
	activeClientCount := 0
	for _, interval := range server.contactHistory {
		if end > interval[0] && start < interval[1] {
			activeClientCount++
		}
		if activeClientCount >= server.maxClients {
			break
		}
	}
	if activeClientCount < 2 {
		server.contactHistory[routeId] = []int64{start, end}
	}
	server.mu.Unlock()
	return isBusy
}

func (server *ContentServer) GetSegment(ctx context.Context, req *pb.SegmentRequest) (*pb.SegmentResponse, error) {
	response := &pb.SegmentResponse{}
	response.Status = "Success"
	//glog.Infof("Got segment request for route %d", req.RouteId)
	if req.Remove {
		//this is a disconnect request
		server.mu.Lock()
		if _, ok := server.contactHistory[req.RouteId]; ok {
			delete(server.contactHistory, req.RouteId)
		}
		server.mu.Unlock()
	} else if len(req.SegmentId) == 0 {
		// this is the first contact request
		if server.canMakeContact(req.RouteId, req.StartTime, req.EndTime) {
            segmentIds := server.metamgr.GetSegments(req.RouteId)
            for _, segId := range segmentIds{
                response.Segments = append(response.Segments, segId)
		    }
        } else {
			response.Status = "node busy"
		}
	} else {
		// this is a segment request
		segmentMeta, err := server.metamgr.GetSegment(req.SegmentId, req.RouteId, req.IsEdge)
		if err == nil  && segmentMeta != nil {
            segment := segmentMeta.segmentId
			response.Status = "segment found"
			response.Segments = append(response.Segments, segment)
		} else {
			response.Status = "segment not found"
		}
		//hasSegment := server.metamgr.SegmentCache.HasSegment(req.SegmentId)

		//if hasSegment {
		//	if !req.IsEdge {
		//		//TODO:update delivery monitor
		//		server.metamgr.SegmentCache.GetSegment(req.SegmentId)
		//	}
		//} else {
		//	response.Status = "segment not found"
		//}
	}
	return response, nil
}

func (server *ContentServer) start() {
	lis, err := net.Listen("tcp", server.address)
	if err != nil {
		glog.Fatalf("ContentServer failed to listen: %v", err)
	}

	//start grpc Content Server to listen from  to listen from cloud
	go func() {
		server.grpcServer = grpc.NewServer()
		pb.RegisterContentServer(server.grpcServer, server)
		glog.Infof("Starting ContentServer")
		server.grpcServer.Serve(lis)
	}()
}