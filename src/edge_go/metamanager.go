package main

import (
	"context"
	"encoding/json"
	"errors"
	"io/ioutil"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/golang/glog"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	cpb "github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver"
	"google.golang.org/grpc"
)

func check(err error) {
	if err != nil {
		glog.Fatal(err)
	}
}

type RouteInfo struct {
	request     pb.DownloadRequest
	doneChannel chan *pb.DownloadReply //to send evicted segments
}

type MetadataManager struct {
	SegmentCache       *SegmentCache
	routeAddChannel    chan RouteInfo
	downloadReqChannel chan pb.DownloadRequest
	evicted            []string
	routes             map[int64]RouteInfo
	resultFile         string
	resultDir          string
	wg                 sync.WaitGroup
}

func newMetadataManager(size int64, cachetype string) *MetadataManager {
	metamgr := &MetadataManager{}
	switch {
	case cachetype == "lru":
		metamgr.SegmentCache = NewSegmentCache(size, "lru")
	}

	metamgr.routeAddChannel = make(chan RouteInfo, 10)             //can accept at most 10 simultaneous routeAdd requests
	metamgr.downloadReqChannel = make(chan pb.DownloadRequest, 10) //can accept at most 10 simultaneous requests
	metamgr.routes = make(map[int64]RouteInfo, 0)
	go metamgr.handleAddRoute()

	metamgr.wg.Add(1)
	go func() {
		metamgr.processDownloads()
		metamgr.wg.Done()
	}()

	//TODO: take from config file
	homeDir, err := os.UserHomeDir()
	if err != nil {
		glog.Fatal(err)
	}

	resultDir := filepath.Join(homeDir, "clairvoyant2", "results_"+strconv.FormatInt(size, 10))
	err = os.MkdirAll(resultDir, 0755)
	if err != nil {
		glog.Fatal(err)
	}
	metamgr.resultFile = filepath.Join(resultDir, "bench2.json")
	metamgr.resultDir = resultDir
	glog.Infof("initialized metadamanager of size = %d, type = %s", size, cachetype)

	return metamgr
}

func (metamgr *MetadataManager) addSegments(segments []*pb.Segment, routeId int64) []string {
	var committed []string
	for _, segment := range segments {
		evicted, err := metamgr.SegmentCache.AddSegment(*segment, routeId)
		if err != nil {
			break
		}
		committed = append(committed, segment.SegmentId)
		metamgr.evicted = append(metamgr.evicted, evicted...)
	}
	return committed
}

func (metamgr *MetadataManager) GetOverdueSegments(curTime int64, threshold int64) map[int64][]*pb.Segment {
	// TODO report actual missed segments and not all segments. This is only for TESTINGGGGG
	undeliveredSegments := make(map[int64][]*pb.Segment)

	for routeId, routeInfo := range metamgr.routes {
		req := &(routeInfo.request)
		deadline := float64(req.ArrivalTime) + req.ContactTime + float64(threshold)

		if float64(curTime) > deadline {
			// currently fetching overdue only if we cross the deadline for the route
			glog.Infof("overdue segs, curTime=%d, contact=%f, arrival=%d, deadline=%f", curTime, req.ContactTime, req.ArrivalTime, deadline)

			var unused, used []string
			for _, segment := range req.Segments {

				isDelivered := metamgr.SegmentCache.DeliveredSegment(segment.SegmentId, routeId)
				if len(used) == 0 {
					if isDelivered {
						used = append(used, segment.SegmentId)
					} else {
						unused = append(unused, segment.SegmentId)
					}
				} else if isDelivered {
					used = append(used, segment.SegmentId)
				} else {
					undeliveredSegments[routeId] = append(undeliveredSegments[routeId], segment)
				}
			}

			glog.Infof("overdue calc - unused=%d, used=%d, missed=%d", len(unused), len(used), len(undeliveredSegments))

			for _, segId := range unused {
				metamgr.SegmentCache.UpdateSegmentStatus(segId, routeId)
			}
		}
	}
	return undeliveredSegments
}

func (metamgr *MetadataManager) getSegmentFromEdge(address string, segments []*pb.Segment, segmentIdxList []int, successTracker *[]bool) {
	conn, err := grpc.Dial(address, grpc.WithInsecure())
	if err != nil {
		glog.Error(err)
	}

	defer conn.Close()

	contentClient := cpb.NewContentClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	for idx := range segmentIdxList {
		segmentRequest := cpb.SegmentRequest{
			RouteId:   -1,
			SegmentId: segments[idx].SegmentId,
			StartTime: 0,
			EndTime:   0,
			Remove:    false,
			IsEdge:    true,
		}
		resp, err := contentClient.GetSegment(ctx, &segmentRequest)
		if err == nil {

			if len(resp.Segments) > 0 {
				(*successTracker)[idx] = true
			} else {
				(*successTracker)[idx] = false
			}
		} else {
			glog.Error(err)
		}
	}
}

func (metamgr *MetadataManager) Close() {
	glog.Info("Closing Metamgr!")
	close(metamgr.downloadReqChannel)
	metamgr.wg.Wait()
	//metamgr.SegmentCache.RecordStats(filepath.Join(metamgr.resultDir, "edgestats"))
}

func (metamgr *MetadataManager) processDownloads() {
	cdnstr := "ftp" //TODO: make this more robust

	var edgeAggDownload, cloudAggDownload, edgeSegCount, cloudSegCount int32

	for request := range metamgr.downloadReqChannel {
		nodeSegMap := map[string][]int{} //map from node_src_ip -> seg_idx list
		numEdge := 0
		successTracker := make([]bool, len(request.Segments))
		for idx, segment := range request.Segments {
			segmentId := segment.SegmentId
			source := request.SegmentSources[segmentId]
			if !strings.Contains(source, cdnstr) {
				nodeSegMap[source] = append(nodeSegMap[source], idx)
				numEdge++
			} else {
				cloudSegCount++
				cloudAggDownload += segment.SegmentSize
			}
		}

		glog.Infof("num_cloud=%d, num_edge=%d", len(request.SegmentSources)-numEdge, numEdge)

		for source, segIdxList := range nodeSegMap {
			metamgr.getSegmentFromEdge(source, request.Segments, segIdxList, &successTracker)
		}

		for idx, success := range successTracker {
			if success {
				edgeSegCount++
				edgeAggDownload += request.Segments[idx].SegmentSize
			} else {
				cloudSegCount++
				cloudAggDownload += request.Segments[idx].SegmentSize
			}
		}

	}
	jsonString, err := json.MarshalIndent(struct {
		EdgeAggDownload  int32
		CloudAggDownload int32
		EdgeSegCount     int32
		CloudSegCount    int32
	}{
		EdgeAggDownload:  edgeAggDownload,
		CloudAggDownload: cloudAggDownload,
		EdgeSegCount:     edgeSegCount,
		CloudSegCount:    cloudSegCount,
	}, "", "  ")
	check(err)

	err = ioutil.WriteFile(metamgr.resultFile, jsonString, 0644)
	glog.Infof("Finished Writing File")
	check(err)
}

func (metamgr *MetadataManager) GetSegment(segmentId string, routeId int64, isEdge bool) error {
	hasSegment := metamgr.SegmentCache.HasSegment(segmentId)
	if !hasSegment {
		return errors.New("segment not found")
	}

	if !isEdge {
		metamgr.SegmentCache.UpdateSegmentStatus(segmentId, routeId)
	}

	return nil
}

func (metamgr *MetadataManager) GetSegments(routeId int64) []string {
	//getsegments does not need to look at the cache. it's a given that when
	// client asks for a route then corresponding segments must be there
	segmentIDs := []string{}
	if rinfo, ok := metamgr.routes[routeId]; ok {
		for _, segment := range rinfo.request.Segments {
			segmentIDs = append(segmentIDs, segment.SegmentId)
		}
	} else {
		glog.Errorf("Route %d not found", routeId)
	}
	return segmentIDs
}

func (metamgr *MetadataManager) handleAddRoute() {
	for routeInfo := range metamgr.routeAddChannel {
		metamgr.evicted = nil
		var committedSegments []string
		if _, ok := metamgr.routes[routeInfo.request.TokenId]; !ok {
			metamgr.routes[routeInfo.request.TokenId] = routeInfo
			glog.Infof("Added route %d with %d segments", routeInfo.request.TokenId, len(routeInfo.request.Segments))
			committedSegments = metamgr.addSegments(routeInfo.request.Segments, routeInfo.request.TokenId)
		}
		dlReply := &pb.DownloadReply{TokenId: routeInfo.request.TokenId, SegmentIds: committedSegments, EvictedIds: metamgr.evicted}
		metamgr.downloadReqChannel <- routeInfo.request
		glog.Infof("len_evicted=%d, len_committed=%d", len(metamgr.evicted), len(committedSegments))

		routeInfo.doneChannel <- dlReply
	}
}
