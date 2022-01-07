package main

import (
    "fmt"
    "github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient"
    "time"
    "strconv"
//    "sync"
)
func areAllClientsDone(clients []cvclient.Client) bool {
  for _, client := range clients {
    if !client.IsDone(){
      return false
    }
  }
  return true
}

func main() {
  var video cvclient.Video
  video.LoadFromFile("bbb.csv", "v4")
  var edgeNodes cvclient.EdgeNodes
  edgeNodes.LoadFromFile("5nodes_17min.csv")
  urls := make([]string, 0)
  clients := make([]cvclient.Client, 0)
  for i :=0; i < 1; i++ {
   var trajectory cvclient.Trajectory
    trajectory.LoadFromFile("../../eval/enode_positions/17min_user0/user0_17min.csv")
    client :=  cvclient.NewClient("c" + strconv.Itoa(i), &trajectory, edgeNodes, video, urls)
    client.RegisterWithCloud("0.0.0.0:60050", 0)
    clients = append(clients, client)
  }
  start := time.Now()
  j := 0
  for {
    //wg := new(sync.WaitGroup)
    for _, client := range clients {
//      wg.Add(1)
       client.Move()
       client.FetchSegments(j)
    }
    //wg.Wait()
    if areAllClientsDone(clients) {
      break
    }
    j = j + 1
  }
  fmt.Printf("\nelapsed = %s", time.Since(start))
}
