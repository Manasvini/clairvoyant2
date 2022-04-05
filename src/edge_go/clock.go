package main

import (
	"context"
	"time"

	"github.com/golang/glog"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"google.golang.org/grpc"
)

type Clock struct {
	timestamp  int64
	nodeId     string
	serverAddr string
}

func NewClock(nodeId string, serverAddr string) *Clock {
	return &Clock{timestamp: 0, nodeId: nodeId, serverAddr: serverAddr}
}

func (clock *Clock) sync() {
	conn, err := grpc.Dial(clock.serverAddr, grpc.WithInsecure())
	if err != nil {
		panic("Could not connect to clock server")
	}
	defer conn.Close()
	clockClient := pb.NewClockServerClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 5 * time.Second)
	defer cancel()
	req := &pb.SyncRequest{NodeId: clock.nodeId}
	resp, err := clockClient.HandleSyncRequest(ctx, req)
	if err != nil {
		glog.Error(err)
	} else {
		clock.timestamp = resp.GetCurTime()
		//glog.Infof("Tick tock. Time is %d", clock.timestamp)
	}
}

func (clock *Clock) GetTime() int64 {
	clock.sync()
	return clock.timestamp
}

func (clock *Clock) UpdateTime(newTime int64) int64 {
	oldTime := clock.timestamp
	clock.timestamp = newTime
	return oldTime
}
