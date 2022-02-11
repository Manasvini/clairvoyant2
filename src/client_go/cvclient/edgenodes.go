package cvclient

import (
	"encoding/csv"
	"fmt"
	"github.com/golang/glog"
	"io"
	"os"
	"sort"
	"strconv"
)

type DistBW struct {
	distance int
	bw       float64
}

type EdgeNode struct {
	id       string
	ip       string
	location Point
	model    []DistBW
}

type EdgeNodes struct {
	nodes []EdgeNode
}

func (edgeNode *EdgeNode) GetDownloadSpeedAtDistance(distance int) float64 {
	i := 0
	j := len(edgeNode.model) - 1
	if distance < edgeNode.model[i].distance {
		return edgeNode.model[i].bw
	}
	if distance > edgeNode.model[j].distance {
		return 0
	}
	var mid int
	for i <= j {
		mid = (i + j) / 2
		if edgeNode.model[mid].distance < distance {
			i = mid + 1
		} else if edgeNode.model[mid].distance >= distance {
			j = mid - 1
		}
	}
	if i >  1{
		i -= 1
	}
	return edgeNode.model[i].bw
}

func NewEdgeNodes() EdgeNodes {
	var enodes []EdgeNode
	edgeNodes := EdgeNodes{nodes: enodes}
	return edgeNodes
}
// weird haversine issue, need to switch lat/lon
func getCoord(p Point) Coord {
	return Coord{Lat: p.lon, Lon: p.lat}
}

func (edgeNodes *EdgeNodes) GetNearestEdgeNode(point Point) (EdgeNode, float64) {
	_, minDist := Distance(getCoord(edgeNodes.nodes[0].location), getCoord(point))
	minDistNode := edgeNodes.nodes[0]
	for _, edge := range edgeNodes.nodes[1:] {
		_, dist := Distance(getCoord(edge.location), getCoord(point))
		if dist < minDist {
			minDist = dist
			minDistNode = edge
		}
	}
	// haversine returns distance in miles and km. convert km to m
	return minDistNode, minDist * 1000
}

func loadModel(filename string) []DistBW {
	f, err := os.Open(filename)

	model := make([]DistBW, 0)
	if err != nil {
		fmt.Println(err)
	}
	// model file doesn't seem to have header
	r := csv.NewReader(f)
	//_, err = r.Read()
	//if err != nil {
	//	fmt.Println(err)
	//}
	for {
		rec, err := r.Read()
		if err != nil {
			if err == io.EOF {
				break
			}
		}
		dist, err := strconv.ParseInt(rec[0], 10, 64)
		speed, err := strconv.ParseFloat(rec[1], 64)
		model = append(model, DistBW{distance: int(dist), bw: speed})
	}
	sort.Slice(model, func(i, j int) bool {
		return model[i].distance < model[j].distance
	})
	return model

}

func (edgeNodes *EdgeNodes) LoadFromFile(filename string) {
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
		curlat, err := strconv.ParseFloat(rec[0], 64)
		curlon, err := strconv.ParseFloat(rec[1], 64)

		point := Point{lat: curlat, lon: curlon}
		modelPath := rec[4]

		node := EdgeNode{location: point, id: rec[2], ip: rec[3], model: loadModel(modelPath)}

		edgeNodes.nodes = append(edgeNodes.nodes, node)
	}
	glog.Infof("Got %d edge nodes\n", len(edgeNodes.nodes))
}
