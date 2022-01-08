package cvclient

import (
  "encoding/csv"
	"fmt"
	"io"
	"strconv"
	"os"
  "github.com/golang/glog"
)

type VideoSegment struct {
  id string
  size float64
}

type Video struct {
  segments map[string]VideoSegment
  videoId string
}


func (video *Video) LoadFromFile(filename string, videoId string) {
  totalSize := 0.0
  f, err := os.Open(filename)
  segments := make(map[string]VideoSegment)
	if err != nil {
		fmt.Println(err)
	}
	r := csv.NewReader(f)
	_, err = r.Read()
	if err != nil {
		fmt.Println(err)
	}
	for {
    rec, err := r.Read()
		if err != nil {
			if err == io.EOF {
				break
			}
		}
    vsize, err := strconv.ParseFloat(rec[1], 64)
		segment := VideoSegment{id: videoId + "_" + rec[0], size:vsize}
		segments[videoId + "_" + rec[0]] = segment
    totalSize += vsize
	}
	video.segments = segments
  video.videoId = videoId
  glog.Infof("have %d segments, total size= %f\n", len(video.segments), totalSize)
}


