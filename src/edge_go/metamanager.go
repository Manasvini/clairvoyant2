package main

import (
  "github.com/golang/glog"
  "github.com/bluele/gcache"
  pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

type RouteInfo struct {
  request pb.DownloadRequest
  doneChannel chan []string //to send evicted segments
}

type MetadataManager struct {
  SegmentCache gcache.Cache
  routeAddChannel chan RouteInfo
  evicted []string
  routes map[int64]RouteInfo
}

func (metamgr *MetadataManager) evictionHandler(key, value interface{}) {
  metamgr.evicted = append(metamgr.evicted, key.(string))
}

func newMetadataManager(size int, cachetype string) (*MetadataManager) {
  metamgr := &MetadataManager{}
  switch {
  case cachetype == "lru":
    metamgr.SegmentCache = gcache.New(size).
      EvictedFunc(metamgr.evictionHandler).LRU().Build()
  case cachetype == "lfu":
    metamgr.SegmentCache = gcache.New(size).
      EvictedFunc(metamgr.evictionHandler).LFU().Build()
  case cachetype == "arc":
    metamgr.SegmentCache = gcache.New(size).
      EvictedFunc(metamgr.evictionHandler).ARC().Build()
  }
  metamgr.routeAddChannel = make(chan RouteInfo, 10) //can accept at most 10 simultaneous routeAdd requests

  go metamgr.handleAddRoute()

  glog.Infof("initialized metadamanager of size = %d, type = %s", size, cachetype)

  return metamgr
}

func (metamgr *MetadataManager) addSegments(segments []*pb.Segment) {
  for _, segment := range segments {
    metamgr.SegmentCache.Set(segment.SegmentId, *segment)
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
  }
  return segmentIDs
}

func (metamgr *MetadataManager) handleAddRoute() {
  for routeInfo := range metamgr.routeAddChannel {
    metamgr.evicted = nil
    if _, ok := metamgr.routes[routeInfo.request.TokenId]; ok {
      metamgr.routes[routeInfo.request.TokenId] = routeInfo
      metamgr.addSegments(routeInfo.request.Segments)
    } else {
      toAdd := []*pb.Segment{}
      for _,seg := range routeInfo.request.Segments {
        if !metamgr.SegmentCache.Has(seg.SegmentId) {
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
