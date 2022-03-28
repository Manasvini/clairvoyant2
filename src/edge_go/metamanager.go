package main

import (
	"context"
	"encoding/json"
	"errors"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"fmt"

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
type HistoryRecord struct {
    segmentId     string
    timestamp     int64
    routeId       int64
}

type MetadataManager struct {
	SegmentCache *SegmentCache
	// pub sub stuff in go
	routeAddChannel    chan RouteInfo
	downloadReqChannel chan pb.DownloadRequest
	linkStateTracker   *LinkStateTracker
	clock              *Clock
	evicted            []string
	routes             map[int64]RouteInfo
	// store results here, stores as json
	resultFile         string
	nodeId             string
	resultDir          string
	wg                 sync.WaitGroup
	requestCtr         int64
    receivedReqCtr     int64
    dlHistory          []HistoryRecord
    pendingDlSize      int64
}
const CDNSTR = "ftp"
const CDNSRC = "ftp:8000"
func newMetadataManager(size int64, cachetype string, nodeId string, clock *Clock, linkStateTracker *LinkStateTracker) *MetadataManager {
	metamgr := &MetadataManager{clock: clock, linkStateTracker: linkStateTracker}
	switch {
	case cachetype == "lru":
		metamgr.SegmentCache = NewSegmentCache(size, "lru", clock)
	case cachetype == "lfu":
		metamgr.SegmentCache = NewSegmentCache(size, "lfu", clock)
	}
    metamgr.pendingDlSize = 0
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

	resultDir := filepath.Join(homeDir, "clairvoyant2", "edge_results")
	err = os.MkdirAll(resultDir, 0755)
	if err != nil {
		glog.Fatal(err)
	}
	metamgr.resultFile = filepath.Join(resultDir, nodeId+"_bench2.json")
	metamgr.resultDir = resultDir
	metamgr.nodeId = nodeId
	glog.Infof("initialized metadamanager of size = %d, type = %s", size, cachetype)

	return metamgr
}

func (metamgr *MetadataManager) canAddSegments(request pb.DownloadRequest) []string {
    availableSpace := metamgr.SegmentCache.GetAvailableFreeSpace() - metamgr.pendingDlSize
    var possibleAdditions int64
    possibleAdditions = 0

    glog.Infof("available free space = %d", availableSpace)
    var possibleCommitted []string

    for _, segment := range request.Segments {
		segmentId := segment.SegmentId
		source := request.SegmentSources[segmentId]
		currentTime := metamgr.clock.GetTime()
		deadline := request.ArrivalTime
		glog.Infof("source for seg %s is %s", segmentId, source)
	    if int64(segment.SegmentSize) + int64(possibleAdditions) > int64(availableSpace) {
            glog.Info("Ran out of cache space")
            break
        }
        if strings.Contains(source, CDNSTR){
                source = CDNSRC
        }
        isDownloadPossible, err := metamgr.linkStateTracker.IsDownloadPossible(int64(segment.SegmentSize), currentTime, deadline, source)
		 _, isSegmentLocal := metamgr.SegmentCache.HasSegment(segmentId)
		if !isSegmentLocal && !isDownloadPossible && err != nil {
            glog.Infof("No b/w to download from source %s", source)
            continue
        }
		if !isSegmentLocal {
            metamgr.pendingDlSize += int64(segment.SegmentSize)
        }
        possibleCommitted = append(possibleCommitted, segment.SegmentId)
        possibleAdditions += int64(segment.SegmentSize)
    }
    glog.Infof("Metamgr added %d segments to pending, now pending size =%d, total pending size = %d", len(possibleCommitted), possibleAdditions, metamgr.pendingDlSize)
    return possibleCommitted
}

// add multiple segments into the cache
// evicted segments are appended to a append only array in the manager
// returns all segment ids which get added into the cache.
func (metamgr *MetadataManager) addSegments(segments []*pb.Segment, routeId int64) []string {
	var committed []string
    var committedSize int64
    committedSize = 0
	for _, segment := range segments {
		evicted, err := metamgr.SegmentCache.AddSegment(*segment, routeId)
		if err != nil {
			break
		}
        committedSize += int64(segment.SegmentSize)
	    glog.Infof("Cache is %fMB occupied, had %d evictions so far", float64(metamgr.SegmentCache.GetCurrentStorageUsed())/1e6, metamgr.SegmentCache.GetEvictionCount())
		committed = append(committed, segment.SegmentId)
		metamgr.evicted = append(metamgr.evicted, evicted...)
	}
    if metamgr.pendingDlSize > 0 {
        metamgr.pendingDlSize -= committedSize
    }
    glog.Infof("Metamgr committed %d segments total size =%d, now total pending size is %d", len(committed), committedSize, metamgr.pendingDlSize)
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
			//glog.Infof("overdue segs, curTime=%d, contact=%f, arrival=%d, deadline=%f", curTime, req.ContactTime, req.ArrivalTime, deadline)

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

// do a grpc call to the content server to retrieve the segment
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
	linkUtilFile := metamgr.resultDir + "/" + metamgr.nodeId + "_linkutilization.csv"
	glog.Infof("file is %s", linkUtilFile)
	f, err := os.Create(linkUtilFile)
	defer f.Close()
	f.WriteString("node,bandwidth\n")
	linkUtils := metamgr.linkStateTracker.GetLinkStates()
	for node, bw := range linkUtils {
		_, err = f.WriteString(node + "," + fmt.Sprintf("%f", bw) + "\n")
		if err != nil {
			panic(err)
		}
	}
	f.Sync()

	evictCtFile := metamgr.resultDir + "/" + metamgr.nodeId + "_eviction.csv"
	f1, err := os.Create(evictCtFile)
	defer f1.Close()
	f1.WriteString("evict,promote,accept,request,received\n")
	f1.WriteString(fmt.Sprintf("%d,%d,%d,%d,%d", metamgr.SegmentCache.GetEvictionCount(), metamgr.SegmentCache.GetPromoteCount(), metamgr.SegmentCache.GetAcceptCount(), metamgr.requestCtr, metamgr.receivedReqCtr))
	f1.Sync()

    dlHistoryFile := metamgr.resultDir + "/" + metamgr.nodeId + "_dlhistory.csv"
    f2, err := os.Create(dlHistoryFile)
    glog.Info(err)
    defer f2.Close()
    glog.Infof("Writing %d dl records", len(metamgr.dlHistory))
    f2.WriteString("segmentId,routeId,timestamp\n")
	for _, rec := range metamgr.dlHistory{
        _, err = f2.WriteString(fmt.Sprintf("%s,%d,%d\n",rec.segmentId, rec.routeId, rec.timestamp))
        if err != nil{

            panic(err)
        }
    }
    f2.Sync()
}

// Download the segments from the cloud
func (metamgr *MetadataManager) processDownloads() {

	var edgeAggDownload, cloudAggDownload int64
	var edgeSegCount, cloudSegCount int32

	// read from the publisher queue
	for request := range metamgr.downloadReqChannel {
		nodeSegMap := map[string][]int{} //map from node_src_ip -> seg_idx list
		numEdge := 0
        numLocal := 0
		successTracker := make([]bool, len(request.Segments))
        localSegments := map[string]int64{}
		for idx, segment := range request.Segments {
			segmentId := segment.SegmentId
			source := request.SegmentSources[segmentId]
			currentTime := metamgr.clock.GetTime()
			glog.Infof("source for seg %s is %s", segmentId, source)
			_, isSegmentLocal := metamgr.SegmentCache.HasSegment(segmentId)
            if strings.Contains(source, CDNSTR){
                source = CDNSRC
            }
            if !isSegmentLocal {
                if source !=CDNSRC {
				    nodeSegMap[source] = append(nodeSegMap[source], idx)
				}
                metamgr.linkStateTracker.UpdateDownloads(int64(segment.SegmentSize), currentTime, source)
				if !isSegmentLocal && source != CDNSRC {
                    numEdge++
                }
			}
            if isSegmentLocal {
                glog.Infof("Segment %s found in cache", segmentId)
                localSegments[segmentId] = int64(segment.SegmentSize)
                numLocal++
            } else {
                historyRec := HistoryRecord{timestamp:currentTime, segmentId: segmentId, routeId: request.TokenId}
                metamgr.dlHistory = append(metamgr.dlHistory, historyRec)

            }
		}

		for source, segIdxList := range nodeSegMap {
			metamgr.getSegmentFromEdge(source, request.Segments, segIdxList, &successTracker)
		}

		for idx, success := range successTracker {
            _, exists := localSegments[request.Segments[idx].SegmentId]
            if exists {
                continue
            }
			if success {
				edgeSegCount++
				edgeAggDownload += int64(request.Segments[idx].SegmentSize)
			} else {
				cloudSegCount++
				cloudAggDownload += int64(request.Segments[idx].SegmentSize)
			}
		}
        _ = metamgr.addSegments(request.Segments, request.TokenId)
		glog.Infof("num_cloud=%d, num_edge=%d num_local=%d", len(request.SegmentSources)-numEdge - numLocal, numEdge, numLocal)


	}
	jsonString, err := json.MarshalIndent(struct {
		EdgeAggDownload  int64
		CloudAggDownload int64
		EdgeSegCount     int32
		CloudSegCount    int32
	}{
		EdgeAggDownload:  edgeAggDownload,
		CloudAggDownload: cloudAggDownload,
		EdgeSegCount:     edgeSegCount,
		CloudSegCount:    cloudSegCount,
	}, "", "  ")
	check(err)

	glog.Infof("result file is %s", metamgr.resultFile)
	err = ioutil.WriteFile(metamgr.resultFile, jsonString, 0644)
	glog.Infof("Finished Writing File")
	check(err)
}

// ?
func (metamgr *MetadataManager) GetSegment(segmentId string, routeId int64, isEdge bool) (*SegmentMetadata, error) {
	segmentMeta, hasSegment := metamgr.SegmentCache.HasSegment(segmentId)
	if !hasSegment {
		return nil, errors.New("segment not found")
	}

	if !isEdge {
		metamgr.SegmentCache.UpdateSegmentStatus(segmentId, routeId)
	}
	return segmentMeta, nil
}

// gets segments for a given route.
// Does not check cache as the cache is strict lru
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

// hande add when something is added to the route add channel
func (metamgr *MetadataManager) handleAddRoute() {
	// read the add route channel
	for routeInfo := range metamgr.routeAddChannel {
		metamgr.evicted = nil
		var committedSegments []string

		// check if the token id is present in the routes
		if _, ok := metamgr.routes[routeInfo.request.TokenId]; !ok {
			// if not, add the new route
			metamgr.routes[routeInfo.request.TokenId] = routeInfo
			glog.Infof("Added route %d with %d segments", routeInfo.request.TokenId, len(routeInfo.request.Segments))
			// find out how many segments can potentially be added
            // This operation does NOT add segments to the cache, only checks if segments can be added
            // Segments are added in processDownloads()
            // By moving addition of segments to processDownloads, we can keep track of segments that were downloaded from (1) cloud (2) edge and (3) already cached. 
            // The move will also make procrastination cleaner 
			committedSegments = metamgr.canAddSegments(routeInfo.request)
		    glog.Infof("Accepted %d segments", len(committedSegments))
            if len(committedSegments) > 0 {
                metamgr.requestCtr += 1
            }
            metamgr.receivedReqCtr +=1
        }
		// add the download request to download the segments
		dlReply := &pb.DownloadReply{TokenId: routeInfo.request.TokenId, SegmentIds: committedSegments, EvictedIds: metamgr.evicted}
		metamgr.downloadReqChannel <- routeInfo.request
		glog.Infof("len_evicted=%d, len_committed=%d", len(metamgr.evicted), len(committedSegments))

		routeInfo.doneChannel <- dlReply
        metamgr.evicted = metamgr.evicted[:0]
	}
}
