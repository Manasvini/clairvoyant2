package main
import (
	cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"github.com/golang/glog"
	"sync/atomic"
	"github.com/bluele/gcache"
	"errors"
)

const DEFAULT_SIZE = 1000000
type Cache struct {
	cache gcache.Cache
	size int64
	currentSize int64
	//mu sync.Mutex
}


func NewCache(size int64, cachetype string, evictedFunc gcache.EvictedFunc) (*Cache) {
	segCache := &Cache{}
	switch {
	case cachetype == "lru":
		segCache.cache = gcache.New(DEFAULT_SIZE).EvictedFunc(evictedFunc).LRU().Build()
	case cachetype == "lfu":
		segCache.cache = gcache.New(DEFAULT_SIZE).EvictedFunc(evictedFunc).LFU().Build()
	}
	segCache.size = size
	segCache.currentSize = 0
	return segCache
}

func (segmentCache *Cache) HasSegment(segmentId string) bool {
	return segmentCache.cache.Has(segmentId)
}

func (segmentCache *Cache) AddSegment(segment cvpb.Segment){
	//segmentCache.mu.Lock()
	//defer segmentCache.mu.Unlock()
	//glog.Infof("Add segment %s with size %fMB to cache with size %fMB", segment.SegmentId, float64(segment.SegmentSize)/1e6, float64(segmentCache.currentSize)/1e6)
	if int64(segment.SegmentSize) > segmentCache.size{
		glog.Errorf("Segment size = %fMB cache size = %fMB, will skip", float64(segment.SegmentSize)/1e6, float64(segmentCache.size)/1e6)
		return
	}
	for {
		if int64(segment.SegmentSize) + segmentCache.currentSize > segmentCache.size {
			segmentCache.evict()
		} else{
			break
		}
		if segmentCache.cache.Len(false) == 0{
			break
		}
	}
	if int64(segment.SegmentSize) + segmentCache.currentSize < segmentCache.size {
		segmentCache.cache.Set(segment.SegmentId, segment)
		atomic.AddInt64(&segmentCache.currentSize, int64(segment.SegmentSize))
		//glog.Infof("Cache size is now %f", float64(segmentCache.currentSize)/1e6)
	}
}

func (segmentCache *Cache) evict () {
	if segmentCache.cache.Len(false) == 0{
		return
	}
	lastItem, err := segmentCache.cache.GetLastItem()
	if err != nil {
		panic(err)
	}
	segmentSize := interface{}(lastItem).(cvpb.Segment).SegmentSize
	segmentCache.cache.Evict()
	atomic.AddInt64(&segmentCache.currentSize, -1*int64(segmentSize))
	//glog.Infof("Evicting segment %s with size %f from cache, cache size is now %f",  lastItem.(cvpb.Segment).SegmentId, float64(segmentSize)/1e6, float64(segmentCache.currentSize)/1e6)
}


func (segmentCache *Cache) GetSegment(segmentId string) (*cvpb.Segment, error){
	//segmentCache.mu.Lock()
	//defer segmentCache.mu.Unlock()
	hasSegment := segmentCache.cache.Has(segmentId)
	if !hasSegment {
		return nil, errors.New("Segment does not exist")
	} else{
		val, _ := segmentCache.cache.Get(segmentId)
		segment := new(cvpb.Segment)
		*segment = val.(cvpb.Segment)
		return segment, nil
	}
}
