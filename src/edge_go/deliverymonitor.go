package main
import(
	"github.com/madflojo/tasks"
	"github.com/golang/glog"
	"time"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"context"
	"google.golang.org/grpc"
)

type DeliveryMonitor struct{
	serverAddr	string
	metamgr		*MetadataManager
	nodeId		string
	clockSvrAddr	string
	syncThreshold	int
	scheduler	*tasks.Scheduler
	timestamp	int64
}

func NewDeliveryMonitor(serverAddr string, metaMgr *MetadataManager, nodeId string, clockSvrAddr string) *DeliveryMonitor {
	dm := &DeliveryMonitor{serverAddr:   serverAddr,
			       metamgr:      metaMgr,
			       nodeId:       nodeId,
			       clockSvrAddr: clockSvrAddr,
			       syncThreshold:5,
			       scheduler:    nil}

	return dm
}

func (dm *DeliveryMonitor) Stop(){
	dm.scheduler.Stop()
}

func (dm *DeliveryMonitor) Start() {
	dm.scheduler = tasks.New()
	// Add a task
	_, err := dm.scheduler.Add(&tasks.Task{
		Interval: time.Duration(time.Duration(dm.syncThreshold) * time.Second),
		TaskFunc: func() (error) {
			dm.Sync()
			dm.UpdateRoutes()
			return nil
		},
	})
	if err != nil {
	  // Do Stuff
		panic(err)
	}

}

func (dm *DeliveryMonitor) Sync(){
	conn, err := grpc.Dial(dm.clockSvrAddr, grpc.WithInsecure())
	if err != nil {
		panic("Could not connect to clock server")
	}
	defer conn.Close()
	clockClient := pb.NewClockServerClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	req := &pb.SyncRequest{NodeId: dm.nodeId}
	resp, err := clockClient.HandleSyncRequest(ctx, req)
	if err != nil{
		glog.Error(err)
	} else{
		dm.timestamp = resp.GetCurTime()
		glog.Infof("Tick tock. Time is %d", dm.timestamp)
	}
}

func (dm *DeliveryMonitor) UpdateRoutes(){
	overdueSegmentsByRoute := dm.metamgr.GetOverdueSegments()
	if overdueSegmentsByRoute == nil || len(overdueSegmentsByRoute) == 0{
		glog.Infof("No routes with overdue segments")
		return
	}
	for route, segments := range overdueSegmentsByRoute {
		missedDeliveryReq := &pb.MissedDeliveryRequest{ TokenId: route, Segments: segments, NodeId: dm.nodeId, Timestamp: dm.timestamp}
		req := &pb.CVRequest{Request: &pb.CVRequest_Misseddeliveryrequest{missedDeliveryReq}}
		conn, err := grpc.Dial(dm.serverAddr, grpc.WithInsecure())
		if err != nil{
			glog.Fatalf("Did not connect to server at %s", dm.serverAddr)
		}
		defer conn.Close()
		c := pb.NewCVServerClient(conn)
		ctx, cancel := context.WithTimeout(context.Background(), time.Second*30)
		defer cancel()
		_, err = c.HandleCVRequest(ctx, req)
		if err != nil{
			glog.Error(err)
		}

	}
}
