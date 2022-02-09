package main

import (
	"errors"
	"sync"

	"github.com/golang/glog"
	cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

/*types*/
const (
	LRU = "lru"
	LFU = "lfu" //unimplemented
)

type SegmentMetadata struct {
	segmentId    string
	segSize      int32
	routeIdSet   map[int64]bool
	timestamp    int64 //for LRU
	evictListIdx int   //can be -1 if not in list
}

type SegmentCache struct {
	evictable        []string
	segmentRouteMap  map[string]*SegmentMetadata
	size             int32
	currentSize      int32
	cachePolicy      string
	mu               sync.Mutex
	currentTimestamp int64
}

/*package internal functions*/

func NewSegmentCache(size int32, cachetype string) *SegmentCache {
	segSegmentCache := &SegmentCache{
		size:             size,
		cachePolicy:      cachetype,
		evictable:        make([]string, 0),
		segmentRouteMap:  make(map[string]*SegmentMetadata),
		currentTimestamp: 0,
	}
	return segSegmentCache
}

func (cache *SegmentCache) curTS() int64 {
	cache.currentTimestamp++
	return cache.currentTimestamp
}

func (cache *SegmentCache) updateEvictable(segmentId string) {
	idx := cache.segmentRouteMap[segmentId].evictListIdx
	if idx != -1 {
		cache.evictable = append(cache.evictable[:idx], cache.evictable[idx+1:]...)
	}
}

func (cache *SegmentCache) pop() error {
	if len(cache.evictable) == 0 {
		return errors.New("Nothing to evict")
	}
	segId := cache.evictable[0]
	cache.currentSize -= cache.segmentRouteMap[segId].segSize
	delete(cache.segmentRouteMap, segId)
	cache.evictable = cache.evictable[1:]
	return nil
}

func (cache *SegmentCache) isSegmentCacheFull(excess int32) bool {

	if (cache.currentSize + excess) <= cache.size {
		return false
	}

	for (cache.currentSize + excess) > cache.size {
		err := cache.pop()
		if err != nil {
			return true
		}
	}
	return false
}

func insert(a []string, index int, value string) []string {
	if len(a) == index { // nil or empty slice or after last element
		return append(a, value)
	}
	a = append(a[:index+1], a[index:]...) // index < len(a)
	a[index] = value
	return a
}

func (cache *SegmentCache) addToEvictable(curSeg *SegmentMetadata) {
	switch cache.cachePolicy {
	case LRU:
		var idx int
		for i, segId := range cache.evictable {
			segTs := cache.segmentRouteMap[segId].timestamp
			if curSeg.timestamp < segTs {
				idx = i
				break
			}
		}
		curSeg.evictListIdx = idx
		cache.evictable = insert(cache.evictable, idx, curSeg.segmentId)
	}
}

/*package external functions*/

func (cache *SegmentCache) HasSegment(segmentId string) bool {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	_, ok := cache.segmentRouteMap[segmentId]
	return ok
}

func (cache *SegmentCache) AddSegment(segment cvpb.Segment, routeId int64) error {
	cache.mu.Lock()
	defer cache.mu.Unlock()
	if cache.isSegmentCacheFull(segment.SegmentSize) {
		return errors.New("SegmentCache is full")
	}

	if _, ok := cache.segmentRouteMap[segment.SegmentId]; !ok {
		cache.segmentRouteMap[segment.SegmentId] = &SegmentMetadata{
			segmentId:  segment.SegmentId,
			segSize:    segment.SegmentSize,
			routeIdSet: map[int64]bool{routeId: true},
		}
	} else {
		cache.segmentRouteMap[segment.SegmentId].routeIdSet[routeId] = true
		//remove from evictable if we need to
		cache.updateEvictable(segment.SegmentId)
	}
	cache.segmentRouteMap[segment.SegmentId].timestamp = cache.curTS()
	return nil
}

func (cache *SegmentCache) UpdateSegmentStatus(segmentId string, routeId int64) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	if segMeta, ok := cache.segmentRouteMap[segmentId]; !ok {
		glog.Errorf("segment=%s does not exist in state", segmentId)
		return
	} else if _, ok := segMeta.routeIdSet[routeId]; !ok {
		glog.Errorf("segment=%s, route=%d does not exist in state", segmentId, routeId)
		return
	}

	delete(cache.segmentRouteMap[segmentId].routeIdSet, routeId)
	if len(cache.segmentRouteMap[segmentId].routeIdSet) == 0 {
		cache.addToEvictable(cache.segmentRouteMap[segmentId])
	}

}
