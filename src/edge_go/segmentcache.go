package main

import (
	"errors"
	"sync"

	"github.com/golang/glog"
	cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

/*types*/
const (
	// this is strict lru. objects are tagged as "needed". Only uneeded objects are evicted.
	LRU = "lru"
	LFU = "lfu" //unimplemented
)

type SegmentMetadata struct {
	segmentId    string
	segSize      int64
	routeIdSet   map[int64]bool
	timestamp    int64 //for LRU, not in sync with global time
	evictListIdx int   //can be -1 if not in list
}

type SegmentCache struct {
	// lazy eviction. this set is guranteed to contain elements which are not going to be used.
	evictable []string
	// segment id -> metadata map (per route) -> bool if present. acts as a hash store
	segmentRouteMap map[string]*SegmentMetadata
	// CONST defined at initialization
	size int64
	// size left
	currentSize      int64
	cachePolicy      string
	mu               sync.Mutex
	currentTimestamp int64
	evictCount       int64
	promoteCount     int64
	acceptCount      int64
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

func (cache *SegmentCache) GetAcceptCount() int64 {
	return cache.acceptCount
}

func (cache *SegmentCache) GetPromoteCount() int64 {
	return cache.promoteCount
}
func (cache *SegmentCache) GetEvictionCount() int64 {
	return cache.evictCount
}
func (cache *SegmentCache) GetCurrentStorageUsed() int64 {
	return cache.currentSize
}

func (cache *SegmentCache) curTS() int64 {
	cache.currentTimestamp++
	return cache.currentTimestamp
}

// remove a segment id from the evictable set if it exists in that set.
// basically performs a "policy touch"
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
	cache.promoteCount += 1
}

// cache pop based on policy. removes a complete segment
// simply removed first element from evicted array
func (cache *SegmentCache) pop() (string, error) {
	// nothing can be evicted???
	if len(cache.evictable) == 0 {
		return "", errors.New("Nothing to evict")
	}
	segId := cache.evictable[0]
	cache.currentSize -= cache.segmentRouteMap[segId].segSize
	cache.evictCount += 1
	glog.Infof("deleting segment %s, total evictions = %d", segId, cache.evictCount)

	delete(cache.segmentRouteMap, segId)
	cache.evictable = cache.evictable[1:]
	return segId, nil
}

// check if a specific segment size can be inserted, takes extra segment size required as input
// returns a list of entries that ARE evicted to create the excess space
func (cache *SegmentCache) isSegmentCacheFull(excess int64) ([]string, bool) {
	// if current size with the excess is less than the capacity
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
		// pops the entry based on policy, returns evicted segment id
		id, err := cache.pop()
		if err != nil {
			glog.Errorf("pop() did not find segments to evict")
			return evicted, true
		}
		evicted = append(evicted, id)
	}
	return evicted, false
}

// array util to insert at random position
func insert(a []string, index int, value string) []string {
	if len(a) == index { // nil or empty slice or after last element
		return append(a, value)
	}
	b := append(a[:index], value)
	c := append(b, a[index+1:]...) // index < len(a)
	c[index] = value
	return c
}

// Marks a segment to be useless and hence can be thrown away
func (cache *SegmentCache) addToEvictable(curSeg *SegmentMetadata) {
	switch cache.cachePolicy {
	case LRU:
		var idx int
		// get the position in the LRU where to insert this segment id based on the recent touch.
		for i, segId := range cache.evictable {
			segTs := cache.segmentRouteMap[segId].timestamp
			if curSeg.timestamp < segTs {
				idx = i
				break
			}
		}
		// idx stores the first index where timestamp is less, hence to recent touch
		curSeg.evictListIdx = idx
		// simply do an insert
		cache.evictable = insert(cache.evictable, idx, curSeg.segmentId)
	case LFU:
		var idx int
		for i, segId := range cache.evictable {
			if curSeg.popularity < cache.segmentRouteMap[segId].popularity {
				idx = i
				break
			}
		}
		curSeg.evictListIdx = idx
		cache.evictable = insert(cache.evictable, idx, curSeg.segmentId)
	}
}

/*package external functions*/

// check if cache has the given segment
func (cache *SegmentCache) HasSegment(segmentId string) (*SegmentMetadata, bool) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	segment, ok := cache.segmentRouteMap[segmentId]
	return segment, ok
}

// check if segment is delivered or not.
// if it is still in cache, return true else return false
// if it is delivered, it would be out of cache?
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

// adds a given segment and a route id to the cache
// returns the evicted ids if some get evicted
func (cache *SegmentCache) AddSegment(segment cvpb.Segment, routeId int64) ([]string, error) {
	cache.mu.Lock()
	defer cache.mu.Unlock()
	var evictedIds []string
	var isFull bool

	// create space in the cache
	if evictedIds, isFull = cache.isSegmentCacheFull(int64(segment.SegmentSize)); isFull {
		return nil, errors.New("SegmentCache is full")
	}

	// add to cache now
	// first case when segment id is not present
	if _, ok := cache.segmentRouteMap[segment.SegmentId]; !ok {
		cache.segmentRouteMap[segment.SegmentId] = &SegmentMetadata{
			segmentId:  segment.SegmentId,
			segSize:    int64(segment.SegmentSize),
			routeIdSet: map[int64]bool{routeId: true},
			popularity: 0,
		}
		// segment id is present
	} else {
		cache.segmentRouteMap[segment.SegmentId].routeIdSet[routeId] = true
		cache.segmentRouteMap[segment.SegmentId].popularity += 1
		//remove from evictable if we need to
		cache.updateEvictable(segment.SegmentId)
	}
	// update the segment map with the "touched" timestamp
	cache.segmentRouteMap[segment.SegmentId].timestamp = cache.curTS()
	return evictedIds, nil
}

// remove a segment id for a given route id
func (cache *SegmentCache) UpdateSegmentStatus(segmentId string, routeId int64) {
	cache.mu.Lock()
	defer cache.mu.Unlock()

	// first check if that entry is present
	if segMeta, ok := cache.segmentRouteMap[segmentId]; !ok {
		glog.Errorf("segment=%s does not exist in state", segmentId)
		return
	} else if _, ok := segMeta.routeIdSet[routeId]; !ok {
		glog.Errorf("segment=%s, route=%d does not exist in state", segmentId, routeId)
		return
	}

	// if present, then mark as evictable
	delete(cache.segmentRouteMap[segmentId].routeIdSet, routeId)
	if len(cache.segmentRouteMap[segmentId].routeIdSet) == 0 {
		cache.addToEvictable(cache.segmentRouteMap[segmentId])
	}

}
