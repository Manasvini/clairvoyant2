package main

import (
	"errors"
	"sync/atomic"
	"os"
	"time"
	"fmt"
	"github.com/bluele/gcache"
	"github.com/golang/glog"
	cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

const DEFAULT_SIZE = 1000000

type Cache struct {
	cache        gcache.Cache
	size         int64
	currentSize  int64
	evictCount   int64
	hitCount     int64
	accessCount  int64
	//mu sync.Mutex
	sizeLog      []int64
	hitRateLog   []float64
	evictLog     []int64
}

func NewCache(size int64, cachetype string, evictedFunc gcache.EvictedFunc) *Cache {
	segCache := &Cache{}
	switch {
	case cachetype == "lru":
		segCache.cache = gcache.New(DEFAULT_SIZE).EvictedFunc(evictedFunc).LRU().Build()
	case cachetype == "lfu":
		segCache.cache = gcache.New(DEFAULT_SIZE).EvictedFunc(evictedFunc).LFU().Build()
	}
	segCache.size = size
	segCache.currentSize = 0
	segCache.evictCount = 0
	segCache.hitCount = 0
	segCache.accessCount = 0
	segCache.sizeLog = make([]int64, 0)
	segCache.hitRateLog = make([]float64, 0)
	segCache.evictLog = make([]int64, 0)
	return segCache
}

func (segmentCache *Cache) RecordStats(filename string) {
	ts := time.Now().Unix()
	f, err := os.Create(fmt.Sprintf("%s_%d.cachesize.csv",filename , ts))
	defer f.Close()
	if err != nil {
		panic(err)
	}
	_, err = f.WriteString("time,size,evictCount\n")
	if err != nil {
		panic(err)
	}
	i := 0
	for{
		dataLine := fmt.Sprintf("%d,%d,%d\n",i,segmentCache.sizeLog[i], segmentCache.evictLog[i])
		glog.Info(dataLine)
		_, err = f.WriteString(dataLine)
		i++
		if i == len(segmentCache.sizeLog){
			break
		}
	}
	f1, err := os.Create(fmt.Sprintf("%s_%d.hitrate.csv", filename , ts))
	defer f1.Close()
	if err != nil {
		panic(err)
	}
	_, err = f1.WriteString("time,hitrate\n")
	if err != nil {
		panic(err)
	}
	i = 0
	for{
		dataLine := fmt.Sprintf("%d,%f\n",i,segmentCache.hitRateLog[i])
		_, err = f1.WriteString(dataLine)
		i++
		if i == len(segmentCache.hitRateLog){
			break
		}
	}
}

func (segmentCache *Cache) HasSegment(segmentId string) bool {
	return segmentCache.cache.Has(segmentId)
}

func (segmentCache *Cache) AddSegment(segment cvpb.Segment) {
	//segmentCache.mu.Lock()
	//defer segmentCache.mu.Unlock()
	//glog.Infof("Add segment %s with size %fMB to cache with size %fMB", segment.SegmentId, float64(segment.SegmentSize)/1e6, float64(segmentCache.currentSize)/1e6)
	if int64(segment.SegmentSize) > segmentCache.size {
		glog.Errorf("Segment size = %fMB cache size = %fMB, will skip", float64(segment.SegmentSize)/1e6, float64(segmentCache.size)/1e6)
		return
	}
	for {
		if int64(segment.SegmentSize)+segmentCache.currentSize > segmentCache.size {
			segmentCache.evict()
		} else {
			break
		}
		if segmentCache.cache.Len(false) == 0 {
			break
		}
	}
	if int64(segment.SegmentSize)+segmentCache.currentSize < segmentCache.size {
		segmentCache.cache.Set(segment.SegmentId, segment)
		atomic.AddInt64(&segmentCache.currentSize, int64(segment.SegmentSize))
		glog.Infof("Cache size is now %f evict count is %d, %d entries in log", float64(segmentCache.currentSize)/1e6, segmentCache.evictCount, len(segmentCache.sizeLog))
		segmentCache.sizeLog = append(segmentCache.sizeLog, segmentCache.currentSize)
		segmentCache.evictLog = append(segmentCache.evictLog, segmentCache.evictCount)
	}
}

func (segmentCache *Cache) evict() {
	if segmentCache.cache.Len(false) == 0 {
		return
	}
	lastItem, err := segmentCache.cache.GetLastItem()
	if err != nil {
		panic(err)
	}

	segmentSize := interface{}(lastItem).(cvpb.Segment).SegmentSize
	segmentCache.cache.Evict()
	atomic.AddInt64(&segmentCache.currentSize, -1*int64(segmentSize))
	atomic.AddInt64(&segmentCache.evictCount, 1)
	glog.Infof("Evicted 1 segment, now evict count is %d", segmentCache.evictCount)
	//glog.Infof("Evicting segment %s with size %f from cache, cache size is now %f",  lastItem.(cvpb.Segment).SegmentId, float64(segmentSize)/1e6, float64(segmentCache.currentSize)/1e6)
}

func (segmentCache *Cache) GetSegment(segmentId string) (*cvpb.Segment, error) {
	//segmentCache.mu.Lock()
	//defer segmentCache.mu.Unlock()
	glog.Infof("Request segment %s from cache", segmentId)
	hasSegment := segmentCache.cache.Has(segmentId)
	currentHitRate := float64(segmentCache.hitCount) /float64(segmentCache.accessCount)
	segmentCache.hitRateLog = append(segmentCache.hitRateLog, currentHitRate)
	atomic.AddInt64(&segmentCache.accessCount, 1)
	if !hasSegment {
		return nil, errors.New("Segment does not exist")
	} else {
		val, _ := segmentCache.cache.Get(segmentId)
		segment := new(cvpb.Segment)
		*segment = val.(cvpb.Segment)
		atomic.AddInt64(&segmentCache.hitCount, 1)
		return segment, nil
	}

}
