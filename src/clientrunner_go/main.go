package main

import (
    "fmt"
    "github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient"
    "time"
    "strconv"
    pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
    "google.golang.org/grpc"
    "sync"
    "context"
    "flag"
    "math/rand"
    "io/ioutil"
    "github.com/golang/glog"
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
    panic("Could not connect to clock server")
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

func getFilesInDir(dirName string)([]string){
  files, err := ioutil.ReadDir(dirName)
  if err != nil {
    panic(err)
  }
  fileNames := make([]string, 0)
  for _, file := range files {
    if file.IsDir(){
      continue
    }
    fileNames = append(fileNames, dirName + "/" + file.Name())
  }
  return fileNames
}

func main() {

  defer glog.Flush() // flushes buffer, if any
  numUsers := flag.Int("n", 1 /*default*/,  "number of users default=1")
  trajectoryDir := flag.String("t", "./", "directory containing user trajectories")
  serverAddr := flag.String("a", "0.0.0.0:60050", "cloud server address")
  //outputFile := flag.String("o", "./output.json", "output file name")
  edgeNodesFile := flag.String("e", "./5nodes_17min.csv", "file with x,y,id,ip,model for all edge nodes")
  numVideos := flag.Int("i", 20, "number of videos")
  videoFile := flag.String("f", "./bbb.csv", "video segments file")
  flag.Parse()
  fmt.Printf("Making flags, num users = %d traj dir = %s, server addr = %s, edge nodes file = %s, numVideos = %d, videoFile = %s\n", *numUsers, *trajectoryDir, *serverAddr, *edgeNodesFile, *numVideos, *videoFile)
  //edgeNodes := cvclient.EdgeNodes{}
  //edgeNodes.LoadFromFile(*edgeNodesFile)
  urls := make([]string, 0)
  clients := make([]cvclient.Client, 0)
  glog.Infof("Make %d clients", *numUsers)
  trajectories := getFilesInDir(*trajectoryDir)
  glog.Infof("files= %s, %s\n", trajectories[0], trajectories[1])
  i := 0
  for _, f := range trajectories {
    fmt.Println(f)
    trajectory := cvclient.Trajectory{}
    trajectory.LoadFromFile(f)
    video := cvclient.Video{}
    edgeNodes := cvclient.EdgeNodes{}
    edgeNodes.LoadFromFile(*edgeNodesFile)

    videoId := "v" + strconv.Itoa(rand.Intn(*numVideos - 2) + 2)
    video.LoadFromFile(*videoFile, videoId)
    glog.Infof("file = %s video is %s\n", f, videoId)
      //"../../eval/enode_positions/17min_user0/user0_17min.csv")
    client :=  cvclient.NewClient("c" + strconv.Itoa(i), &trajectory, edgeNodes, video, urls)
    clients = append(clients, client)
    i += 1
    if i  == *numUsers    {
      break
    }
  }
  glog.Infof("Created %d clients\n", len(clients))
  start := time.Now()
  for {

    timestamp := advanceClock()
    if timestamp % 100 == 0 {
      glog.Infof("timestamp is now %d\n", timestamp)
    }
    wg := new(sync.WaitGroup)
    for _, client := range clients {
       if int64(client.GetStartTime()) < int64(timestamp) + int64(100)  && !client.IsRegistered(){
          client.RegisterWithCloud(*serverAddr, float64(timestamp))
       }
       if int64(client.GetStartTime()) < timestamp {
          wg.Add(1)
          go func(timestamp int64, client cvclient.Client) {
            defer wg.Done()
            client.FetchSegments(timestamp)
          }(timestamp, client)
       }
    }
    wg.Wait()
    if areAllClientsDone(clients) {
      break
    }
  }
  fmt.Printf("\nelapsed = %s\n", time.Since(start))
  for _, c := range clients {
    c.PrintStats()
  }
}
