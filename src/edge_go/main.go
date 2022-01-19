package main

import (
  "flag"
  "github.com/golang/glog"
  "os"
  "os/signal"
  "syscall"
  "time"
)

func startEdgeDaemon(config EdgeConfig, metamgr *MetadataManager) (*EdgeDaemon) {
  edgeDaemon := &EdgeDaemon{
    config : config,
    address : config.EdgeServerAddress,
    metamgr : metamgr,
  }
  edgeDaemon.start()
  return edgeDaemon
}

func startContentServer(config EdgeConfig, metamgr *MetadataManager) (*ContentServer) {
  cserver := &ContentServer{
    address : config.ContentServerAddress,
    metamgr : metamgr,
    maxClients : config.ContentServerMaxClients,
    contactHistory: make(map[int64][]int64),
  }
  cserver.start()
  return cserver
}

func startMonitoring(config EdgeConfig) {
  mclient := NewMonitoringClient(config.ModelFile, config.MonInterval, config.MonServerAddress, config.NodeID)
  go func(){
    for {
      mclient.sendHTTP()
      time.Sleep(time.Duration(mclient.interval)*time.Second)
      glog.Flush()
    }
  }()
}

func waitForUserExit() {
  schan := make(chan os.Signal)
  signal.Notify(schan, os.Interrupt, syscall.SIGTERM)
  <-schan
}

func initEdgeRoutines(address string, configFile string) {

  config := parseConfig(configFile)
  metamgr := newMetadataManager(config.CacheSize, config.CacheType)

  startMonitoring(config)
  edaemon := startEdgeDaemon(config, metamgr)
  cserver := startContentServer(config, metamgr)
  //dmonitor :=startDeliverMonitor(config, metamgr, &wg, ctx)

  waitForUserExit()
  edaemon.grpcServer.GracefulStop()
  cserver.grpcServer.GracefulStop()
}


func main() {

  defer glog.Flush() // flushes buffer, if any

  //parse arguments
  configFile := flag.String("config", "../conf/edge_config.json" /*default*/,  "Edge Config file")
  edgeDaemonAddress := flag.String("address", "0.0.0.0:60050", "Edge Daemon address listening for download assignments from the cloud")

  flag.Set("logtostderr", "true")
  flag.Parse()
  glog.Infof("Loaded flags. config = %s, edgeDaemon = %s", *configFile, *edgeDaemonAddress)

  initEdgeRoutines(*edgeDaemonAddress, *configFile)
}
