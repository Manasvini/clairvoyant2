package cvclient

import (
  "encoding/csv"
	"fmt"
	"io"
	"strconv"
	"os"
  "github.com/golang/glog"
)

type Trajectory struct {
  points []Point
  curIdx int
}

func NewTrajectory()(Trajectory){
  var trajectory = Trajectory{points:make([]Point, 0), curIdx:0}
  return trajectory
}

func (trajectory *Trajectory) HasEnded() bool {
  return trajectory.curIdx == len(trajectory.points)
}

func (trajectory *Trajectory) Advance() {
  if len(trajectory.points)  > trajectory.curIdx + 4{
    trajectory.curIdx += 4
  } else {
    trajectory.curIdx = len(trajectory.points)
  }
}

func (trajectory *Trajectory) LoadFromFile(filename string) {
  f, err := os.Open(filename)

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
    // csv row: userid, time,x,y,z,velcoity, we're taking x, y, velocity, time
    curlat, err := strconv.ParseFloat(rec[2], 64)
    curlon, err := strconv.ParseFloat(rec[3], 64)
    speed, err := strconv.ParseFloat(rec[5], 64)
    timestamp, err := strconv.ParseFloat(rec[1], 64)
    point := Point{lat:curlat, lon:curlon, speed:speed, timestamp:timestamp}
		trajectory.points = append(trajectory.points, point)
	}
	glog.Infof("Got %d points in traj first=%f\n", len(trajectory.points), trajectory.points[0].timestamp)
}


