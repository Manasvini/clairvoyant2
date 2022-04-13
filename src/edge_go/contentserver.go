package main

import (
	"context"
	"net"
	"sync"
    "os"
	"github.com/golang/glog"
	//cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	pb "github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver"
	"google.golang.org/grpc"
    "fmt"
)
type UserDlRequest struct {
    segmentId   string
    routeId     int64
}
type ContentServer struct {
	pb.UnimplementedContentServer
	address       string
	grpcServer    *grpc.Server
	metamgr       *MetadataManager
    userDlReqs    []UserDlRequest
	maxClients     int
	contactHistory map[int64][]int64
	mu             sync.Mutex
    nodeId         string
    resultDir      string
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
	glog.Infof("Got segment %s request for route %d",req.SegmentId, req.RouteId)
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
            if req.RouteId != -1 {
                dlReq := UserDlRequest{segmentId: req.SegmentId, routeId:req.RouteId}
                server.userDlReqs = append(server.userDlReqs, dlReq)
            }
            segment := segmentMeta.segmentId
			response.Status = "segment found"
			response.Segments = append(response.Segments, segment)
		    glog.Infof("Found segment%s", req.SegmentId)
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

func (server *ContentServer) Close() {
    dlReqFile := server.resultDir + "/" + server.nodeId + "_userRequests.csv"
    f, _ := os.Create(dlReqFile)
    defer f.Close()
    f.WriteString("route,segment\n")
    for _, dlReq := range server.userDlReqs {
        f.WriteString(fmt.Sprintf("%d,%s\n", dlReq.routeId , dlReq.segmentId))
    }
    f.Sync()
}
