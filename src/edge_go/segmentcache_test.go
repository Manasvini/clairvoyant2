package main

import (
	"strings"
	"testing"

	cvpb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
)

func TestHasSegment(t *testing.T) {
	//input table
	table := []struct {
		name     string
		input    string
		expected bool
	}{
		{"segment present", "test1", true},
		{"segment not present", "test2", false},
	}

	cache := NewSegmentCache(2, "lru", nil)
	cache.segmentRouteMap["test1"] = &SegmentMetadata{}

	for _, tc := range table {
		result := cache.HasSegment(tc.input)
		if result != tc.expected {
			t.Errorf("For %s test, got %t want %t", tc.name, result, tc.expected)
		}
	}
}

type TestCase struct {
	id   int
	name string
}

func setupSuite(tc TestCase) (*SegmentCache, cvpb.Segment, int64) {
	cache := NewSegmentCache(3, "lru", nil)
	cache.currentSize = 2
	cache.segmentRouteMap = map[string]*SegmentMetadata{
		"test1": &SegmentMetadata{
			segmentId:  "test1",
			segSize:    1,
			routeIdSet: map[int64]bool{1: true},
		},
		"test2": &SegmentMetadata{
			segmentId:  "test2",
			segSize:    1,
			routeIdSet: map[int64]bool{2: true},
		},
	}

	var routeId int64
	routeId = 3
	seg := cvpb.Segment{SegmentId: "test3",
		SegmentSize: 1}
	switch tc.id {
	case 0: //cache not full
	case 1: //cache full, no evictions
		cache.size = 2
	case 2: //cache full, evictions performed and space found
		cache.size = 2
		cache.evictable = []string{"test2"}
		delete(cache.segmentRouteMap["test2"].routeIdSet, 2)
	case 3: //cache full, evictions performed and space not found
		cache.size = 2
		cache.evictable = []string{"test2"}
		delete(cache.segmentRouteMap["test2"].routeIdSet, 2)
		seg.SegmentSize = 2
	case 4: //update segment status, test lru
		//fill evictable for test
		cache.segmentRouteMap["test3"] = &SegmentMetadata{timestamp: 3}
		cache.segmentRouteMap["test4"] = &SegmentMetadata{timestamp: 5}
		cache.evictable = []string{"test3", "test4"}
		routeId = 2
		seg.SegmentId = "test2"
		//so that item can be placed in the middle of evictable
		cache.segmentRouteMap["test2"].timestamp = 4

	}

	return cache, seg, routeId
}

func TestCacheNotFull(t *testing.T) {
	tc := TestCase{0, "cache not full"}
	cache, seg, routeId := setupSuite(tc)
	evicted, err := cache.AddSegment(seg, routeId)
	if err != nil {
		t.Fatalf("tc %s failed, want=nil, got=%s", tc.name, err)
	}
	if evicted != nil {
		t.Fatalf("tc %s failed, want=nil, got=%s", tc.name, evicted)
	}
	has := cache.HasSegment(seg.SegmentId)
	if !has {
		t.Fatalf("tc %s failed, want=true, got=%t", tc.name, has)
	}
}

func TestCacheFullWithNoEvictions(t *testing.T) {
	tc := TestCase{1, "cache full, no evictions"}
	cache, seg, routeId := setupSuite(tc)
	evicted, err := cache.AddSegment(seg, routeId)
	if err == nil || !strings.Contains(err.Error(), "SegmentCache is full") {
		var got string
		if err == nil {
			got = "nil"
		} else {
			got = err.Error()
		}

		t.Fatalf("tc %s failed, want='SegmentCache is full', got=%s", tc.name, got)
	}
	if evicted != nil {
		t.Fatalf("tc %s failed, want=nil, got=%s", tc.name, evicted)
	}
}

func TestCacheFullWithEvictions(t *testing.T) {
	tc := TestCase{2, "evictions, cache not full"}
	cache, seg, routeId := setupSuite(tc)
	evicted, err := cache.AddSegment(seg, routeId)
	if err != nil {
		t.Fatalf("tc %s failed, want=nil, got=%s", tc.name, err)
	}

	if evicted == nil || evicted[0] != "test2" {
		var got string
		if evicted != nil {
			got = evicted[0]
		} else {
			got = "nil"
		}
		t.Fatalf("tc %s failed, want=test2, got=%s", tc.name, got)
	}

	has := cache.HasSegment(seg.SegmentId)
	if !has {
		t.Fatalf("tc %s failed, want=true, got=%t", tc.name, has)
	}
}

func TestCacheFullWithEvictionsFail(t *testing.T) {
	tc := TestCase{3, "evictions, cache still full"}
	cache, seg, routeId := setupSuite(tc)
	evicted, err := cache.AddSegment(seg, routeId)
	if err == nil || !strings.Contains(err.Error(), "SegmentCache is full") {
		var got string
		if err == nil {
			got = "nil"
		} else {
			got = err.Error()
		}

		t.Fatalf("tc %s failed, want='SegmentCache is full', got=%s", tc.name, got)
	}
	if evicted != nil {
		t.Fatalf("tc %s failed, want=nil, got=%s", tc.name, evicted)
	}
}

func TestUpdateSegmentStatus(t *testing.T) {
	tc := TestCase{4, "test update segment status, lru policy"}
	cache, seg, routeId := setupSuite(tc)
	cache.UpdateSegmentStatus(seg.SegmentId, routeId)
	if cache.evictable[1] != seg.SegmentId {
		t.Fatalf("tc %s failed, want=%s, got=%s", tc.name, seg.SegmentId, cache.evictable[1])
	}
}
