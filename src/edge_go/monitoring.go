package main

import (
  "encoding/csv"
  "encoding/json"
  "os"
  "github.com/golang/glog"
  "fmt"
  "net/http"
  "io"
  "strconv"
  "bytes"
)


type BwInfo struct {
  Mean float64 `json:"mean"`
  Sdev float64 `json:"sdev"`
}


func parseModelFile(modelFile string) map[string]BwInfo {
  csvfile, err := os.Open(modelFile)
  if err != nil {
    glog.Exitf("Unable to read Model File = %s", modelFile)
  }

  modelMap := make(map[string]BwInfo)
  csvreader := csv.NewReader(csvfile)
  for {
    record, err := csvreader.Read()
    if err == io.EOF {
      break
    }
    if err != nil {
      glog.Fatalf("Unable to parse model file, err = %s", err)
    }

    bwInfo := BwInfo{}
    bwInfo.Mean, err = strconv.ParseFloat(record[1], 64)
    if err != nil {
      glog.Fatalf("Unable to parse model file, err = %s", err)
    }

    bwInfo.Sdev, err = strconv.ParseFloat(record[2], 64)
    if err != nil {
      glog.Fatalf("Unable to parse model file, err = %s", err)
    }

    modelMap[record[0]] = bwInfo
  }

  return modelMap
}

type MonitoringClient struct {
  model_dict map[string]BwInfo
  interval int
  url string
  nodeId string
}

func NewMonitoringClient(modelFile string,
                         interval  int,
                         address   string,
                         nodeId    string) *MonitoringClient {
  client := MonitoringClient{
    model_dict: parseModelFile(modelFile),
    interval: interval,
    url: fmt.Sprintf("http://%s", address),
    nodeId: nodeId,
  }
  return &client
}

func (mclient *MonitoringClient) getCurrentBw() map[string]float64{
  distBwMap := map[string]float64{}
  for dist,info := range mclient.model_dict{
    distBwMap[dist] = info.Mean
  }
  return distBwMap
}

func (mclient *MonitoringClient) sendHTTP() {

  postBody := struct {
    NodeId string `json:"nodeid"`
    Model map[string]float64 `json:"model"`
  }{
    NodeId : mclient.nodeId,
    Model : mclient.getCurrentBw(),
  }

  postBodyStr, err := json.Marshal(postBody)
  if err != nil {
    glog.Error(err)
  }
  //glog.Infof("postBody=%s", postBodyStr)

  //fmt.Println(string(modelbstr))
  //for k,v := range mclient.model_dict {
  //  fmt.Println(k, "value is", v.Mean, " and ", v.Sdev)
  //}

  responseBody := bytes.NewBuffer(postBodyStr)
  resp, err := http.Post(fmt.Sprintf("%s/post", mclient.url),
                         "application/json", responseBody)
  if err != nil {
    glog.Fatalf("Unable to Post %v", err)
  }
  defer resp.Body.Close()
  glog.Infof("status=%d", resp.StatusCode)
}
