package main

import (
  "github.com/golang/glog"
  pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

type RouteInfo struct {
  request pb.DownloadRequest
  doneChannel chan []string //to send evicted segments
}

type MetadataManager struct {
  SegmentCache *Cache
  routeAddChannel chan RouteInfo
  evicted []string
  routes map[int64]RouteInfo
}

func (metamgr *MetadataManager) evictionHandler(key, value interface{}) {
  metamgr.evicted = append(metamgr.evicted, key.(string))
}

func newMetadataManager(size int64, cachetype string) (*MetadataManager) {
  metamgr := &MetadataManager{}
  switch {
  case cachetype == "lru":
	  metamgr.SegmentCache = NewCache(size, "lru", metamgr.evictionHandler)
  case cachetype == "lfu":
	  metamgr.SegmentCache = NewCache(size, "lfu", metamgr.evictionHandler)
  }
  metamgr.routeAddChannel = make(chan RouteInfo, 10) //can accept at most 10 simultaneous routeAdd requests
  metamgr.routes = make(map[int64]RouteInfo, 0)
  go metamgr.handleAddRoute()

  glog.Infof("initialized metadamanager of size = %d, type = %s", size, cachetype)

  return metamgr
}

func (metamgr *MetadataManager) addSegments(segments []*pb.Segment) {
  for _, segment := range segments {
    metamgr.SegmentCache.AddSegment(*segment)
  }
}

func (metamgr *MetadataManager) getSegments(routeId int64) []string {
  //getsegments does not need to look at the cache. it's a given that when
  // client asks for a route then corresponding segments must be there
  segmentIDs := []string{}
  if rinfo, ok := metamgr.routes[routeId]; ok {
    for _,segment := range rinfo.request.Segments{
      segmentIDs = append(segmentIDs, segment.SegmentId)
    }
  } else{
    glog.Errorf("Route %d not found", routeId)
  }
  return segmentIDs
}

func (metamgr *MetadataManager) handleAddRoute() {
  for routeInfo := range metamgr.routeAddChannel {
    metamgr.evicted = nil
    if _, ok := metamgr.routes[routeInfo.request.TokenId]; !ok {
      metamgr.routes[routeInfo.request.TokenId] = routeInfo
      glog.Infof("Added route %d with %d segments", routeInfo.request.TokenId, len(routeInfo.request.Segments))
      metamgr.addSegments(routeInfo.request.Segments)
    } else {
      toAdd := []*pb.Segment{}
      for _,seg := range routeInfo.request.Segments {
        if !metamgr.SegmentCache.HasSegment(seg.SegmentId) {
          toAdd = append(toAdd, seg)
        }
      }
      if len(toAdd) > 0 {
        metamgr.addSegments(toAdd)
      }
    }
    glog.Infof("len_evicted=%d", len(metamgr.evicted))
    routeInfo.doneChannel <- metamgr.evicted
  }
}
