package main

import (
    "fmt"
    "github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient"
    "time"
    "strconv"
    pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
    "google.golang.org/grpc"
    //    "sync"
    "log"
    "context"
  )
func areAllClientsDone(clients []cvclient.Client) bool {
  for _, client := range clients {
    if !client.IsDone(){
      return false
    }
  }
  return true
}

func advanceClock() (int64) {
  conn, err := grpc.Dial("0.0.0.0:8383", grpc.WithInsecure())
  if err != nil{
    log.Fatalf("Could not connect to clock server")
  }
  defer conn.Close()
  clockClient := pb.NewClockServerClient(conn)
  ctx, cancel := context.WithTimeout(context.Background(), time.Second)
  defer cancel()
  req := pb.AdvanceClock{}
  resp, err := clockClient.HandleAdvanceClock(ctx, &req)
  if err != nil{
    fmt.Println(err)
  } else{
      if resp != nil {
        return resp.CurTime
      }
  }
  return -1
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
    //client.RegisterWithCloud("0.0.0.0:60050", 0)
    clients = append(clients, client)
  }
  start := time.Now()
  for {
    timestamp := advanceClock()
    //wg := new(sync.WaitGroup)
    if timestamp % 100 == 0 {
      fmt.Printf("timestamp is now %d\n", timestamp)
    }
    for _, client := range clients {
//      wg.Add(1)
       if int64(client.GetStartTime()) < int64(timestamp) + int64(100)  && !client.IsRegistered(){
          client.RegisterWithCloud("0.0.0.0:60050", float64(timestamp))
       }
       if int64(client.GetStartTime()) < timestamp {
          client.Move()
          client.FetchSegments(timestamp)
       }
    }
    //wg.Wait()
    if areAllClientsDone(clients) {
      break
    }
  }
  fmt.Printf("\nelapsed = %s", time.Since(start))
  clients[0].PrintStats()
}
