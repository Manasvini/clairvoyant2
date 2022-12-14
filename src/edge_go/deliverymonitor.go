package main

import (
	"context"
	"time"

	"github.com/golang/glog"
	"github.com/madflojo/tasks"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"google.golang.org/grpc"
)

type DeliveryMonitor struct {
	serverAddr              string
	metamgr                 *MetadataManager
	nodeId                  string
	syncThreshold           int
	scheduler               *tasks.Scheduler
    clock                   *Clock
	missedDeliveryThreshold int64
}

func NewDeliveryMonitor(serverAddr string, metaMgr *MetadataManager, nodeId string, clock *Clock) *DeliveryMonitor {
	dm := &DeliveryMonitor{serverAddr: serverAddr,
		metamgr:       metaMgr,
		nodeId:        nodeId,
		clock:         clock,
		syncThreshold: 5,
		scheduler:     nil}

	return dm
}

func (dm *DeliveryMonitor) Stop() {
	dm.scheduler.Stop()
}

func (dm *DeliveryMonitor) Start() {
	dm.scheduler = tasks.New()
	// Add a task
	_, err := dm.scheduler.Add(&tasks.Task{
		Interval: time.Duration(time.Duration(dm.syncThreshold) * time.Second),
		TaskFunc: func() error {
			//dm.Sync()
			dm.UpdateRoutes()
			return nil
		},
	})
	if err != nil {
		// Do Stuff
		panic(err)
	}

}

/*func (dm *DeliveryMonitor) Sync() {
	/*conn, err := grpc.Dial(dm.clockSvrAddr, grpc.WithInsecure())
	if err != nil {
		panic("Could not connect to clock server")
	}
	defer conn.Close()
	clockClient := pb.NewClockServerClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	req := &pb.SyncRequest{NodeId: dm.nodeId}
	resp, err := clockClient.HandleSyncRequest(ctx, req)
	if err != nil {
		glog.Error(err)
	} else {
		dm.timestamp = resp.GetCurTime()
		glog.Infof("Tick tock. Time is %d", dm.timestamp)
	}
    //dm.timestamp = clock.GetTime()
}
*/

func (dm *DeliveryMonitor) UpdateRoutes() {
	timestamp := dm.clock.GetTime()
    overdueSegmentsByRoute := dm.metamgr.GetOverdueSegments(timestamp, dm.missedDeliveryThreshold)
	if overdueSegmentsByRoute == nil || len(overdueSegmentsByRoute) == 0 {
		glog.Infof("No routes with overdue segments")
		return
	}
	for route, segments := range overdueSegmentsByRoute {
		missedDeliveryReq := &pb.MissedDeliveryRequest{TokenId: route, Segments: segments, NodeId: dm.nodeId, Timestamp: timestamp}
		req := &pb.CVRequest{Request: &pb.CVRequest_Misseddeliveryrequest{missedDeliveryReq}}
		conn, err := grpc.Dial(dm.serverAddr, grpc.WithInsecure())
		if err != nil {
			glog.Fatalf("Did not connect to server at %s", dm.serverAddr)
		}
		defer conn.Close()
		c := pb.NewCVServerClient(conn)
		ctx, cancel := context.WithTimeout(context.Background(), time.Second*30)
		defer cancel()
		_, err = c.HandleCVRequest(ctx, req)
		if err != nil {
			glog.Error(err)
		}

	}
}
