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
	segSize      int64
	routeIdSet   map[int64]bool
	timestamp    int64 //for LRU
	evictListIdx int   //can be -1 if not in list
}

type SegmentCache struct {
	evictable        []string
	segmentRouteMap  map[string]*SegmentMetadata
	size             int64
	currentSize      int64
	cachePolicy      string
	mu               sync.Mutex
	currentTimestamp int64
}

/*package internal functions*/

func NewSegmentCache(size int64, cachetype string) *SegmentCache {
	segmentCache := &SegmentCache{
		size:             size,
		cachePolicy:      cachetype,
		evictable:        make([]string, 0),
		segmentRouteMap:  make(map[string]*SegmentMetadata),
		currentTimestamp: 0,
	}
	return segmentCache
}

func (cache *SegmentCache) curTS() int64 {
	cache.currentTimestamp++
	return cache.currentTimestamp
}

func (cache *SegmentCache) updateEvictable(segmentId string) {
	//idx := cache.segmentRouteMap[segmentId].evictListIdx
	idx := -1
	for i, v := range cache.evictable {
		if v == segmentId {
			idx = i
			break
		}
	}
	if idx != -1 {
		cache.evictable = append(cache.evictable[:idx], cache.evictable[idx+1:]...)
	}
}

func (cache *SegmentCache) pop() (string, error) {
	if len(cache.evictable) == 0 {
		return "", errors.New("Nothing to evict")
	}
	segId := cache.evictable[0]
	cache.currentSize -= cache.segmentRouteMap[segId].segSize
	delete(cache.segmentRouteMap, segId)
	cache.evictable = cache.evictable[1:]
	return segId, nil
}

func (cache *SegmentCache) isSegmentCacheFull(excess int64) ([]string, bool) {

	if (cache.currentSize + excess) <= cache.size {
		return nil, false
	}

	//check if evicted list size can support excess
	var evictSize int64
	for _, segId := range cache.evictable {
		evictSize += cache.segmentRouteMap[segId].segSize
	}
	if (cache.currentSize - evictSize + excess) > cache.size {
		return nil, true
	}

	evicted := []string{}
	for (cache.currentSize + excess) > cache.size {
		id, err := cache.pop()
		if err != nil {
			glog.Errorf("pop() did not find segments to evict")
			return evicted, true
		}
		evicted = append(evicted, id)
	}
	return evicted, false
}

func insert(a []string, index int, value string) []string {
	if len(a) == index { // nil or empty slice or after last element
		return append(a, value)
	}
	b := append(a[:index], value)
	c := append(b, a[index+1:]...) // index < len(a)
	c[index] = value
	return c
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

func (cache *SegmentCache) HasSegment(segmentId string) (*SegmentMetadata, bool) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	segment, ok := cache.segmentRouteMap[segmentId]
	return segment, ok
}

func (cache *SegmentCache) DeliveredSegment(segmentId string, routeId int64) bool {
	cache.mu.Lock()
	defer cache.mu.Unlock()
	if segMeta, ok := cache.segmentRouteMap[segmentId]; !ok {
		glog.Warningf("segment %s not in cache")
		return true
	} else if _, ok := segMeta.routeIdSet[routeId]; !ok {
		return true
	}
	return false
}

func (cache *SegmentCache) AddSegment(segment cvpb.Segment, routeId int64) ([]string, error) {
	cache.mu.Lock()
	defer cache.mu.Unlock()
	var evictedIds []string
	var isFull bool

	if evictedIds, isFull = cache.isSegmentCacheFull(int64(segment.SegmentSize)); isFull {
		return nil, errors.New("SegmentCache is full")
	}

	if _, ok := cache.segmentRouteMap[segment.SegmentId]; !ok {
		cache.segmentRouteMap[segment.SegmentId] = &SegmentMetadata{
			segmentId:  segment.SegmentId,
			segSize:    int64(segment.SegmentSize),
			routeIdSet: map[int64]bool{routeId: true},
		}
	} else {
		cache.segmentRouteMap[segment.SegmentId].routeIdSet[routeId] = true
		//remove from evictable if we need to
		cache.updateEvictable(segment.SegmentId)
	}
	cache.segmentRouteMap[segment.SegmentId].timestamp = cache.curTS()
	return evictedIds, nil
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
