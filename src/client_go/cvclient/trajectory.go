package cvclient

import (
  "encoding/csv"
	"fmt"
	"io"
	"strconv"
	"os"
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
  if len(trajectory.points) >= trajectory.curIdx {
    trajectory.curIdx += 1
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
    curlat, err := strconv.ParseFloat(rec[0], 64)
    curlon, err := strconv.ParseFloat(rec[1], 64)
    speed, err := strconv.ParseFloat(rec[4], 64)
    timestamp, err := strconv.ParseFloat(rec[3], 64)
    point := Point{lat:curlat, lon:curlon, speed:speed, timestamp:timestamp}
		trajectory.points = append(trajectory.points, point)
	}
	fmt.Printf("Got %d points in traj\n", len(trajectory.points))
}


