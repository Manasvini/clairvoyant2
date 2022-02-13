package main

import (
	"flag"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/golang/glog"
)

func startDeliveryMonitor(config EdgeConfig, metamgr *MetadataManager) *DeliveryMonitor {
	dm := NewDeliveryMonitor(config.ServerAddress, metamgr, config.NodeID, config.ClockServerAddr)
	dm.Start()
	return dm
}

func startEdgeServer(config EdgeConfig, metamgr *MetadataManager) *EdgeServer {
	edgeServer := &EdgeServer{
		config:  config,
		address: config.EdgeServerAddress,
		metamgr: metamgr,
	}
	edgeServer.start()
	return edgeServer
}

func startContentServer(config EdgeConfig, metamgr *MetadataManager) *ContentServer {
	cserver := &ContentServer{
		address:        config.ContentServerAddress,
		metamgr:        metamgr,
		maxClients:     config.ContentServerMaxClients,
		contactHistory: make(map[int64][]int64),
	}
	cserver.start()
	return cserver
}

func startMonitoring(config EdgeConfig) {
	mclient := NewMonitoringClient(config.ModelFile, config.MonInterval, config.MonServerAddress, config.NodeID)
	go func() {
		for {
			mclient.sendHTTP()
			time.Sleep(time.Duration(mclient.interval) * time.Second)
			glog.Flush()
		}
	}()
}

func waitForUserExit() {
	schan := make(chan os.Signal)
	signal.Notify(schan, os.Interrupt, syscall.SIGTERM)
	<-schan
}

func initEdgeRoutines(configFile string) {

	config := parseConfig(configFile)
	metamgr := newMetadataManager(int64(config.CacheSize), config.CacheType, config.NodeID)
	startMonitoring(config)
	eserver := startEdgeServer(config, metamgr)
	cserver := startContentServer(config, metamgr)
	dmonitor := startDeliveryMonitor(config, metamgr)
	defer dmonitor.Stop()
	waitForUserExit()
	eserver.grpcServer.GracefulStop()
	cserver.grpcServer.GracefulStop()
	metamgr.Close()
}

func main() {

	defer glog.Flush() // flushes buffer, if any

	//parse arguments
	configFile := flag.String("config", "../conf/edge_config.json" /*default*/, "Edge Config file")

	//flag.Set("logtostderr", "true")
	flag.Parse()
	glog.Infof("Loaded flags. config = %s", *configFile)

	initEdgeRoutines(*configFile)
}
