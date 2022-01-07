package cvclient
import (
    "fmt"
    "time"
    "log"
    "google.golang.org/grpc"
    "context"
    pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
//    "sync"
    "math"
    "io/ioutil"
    "net/http"
    "encoding/json"
    "strings"
    "strconv"
  )

type DlStats struct {
  pendingBytes int
  receivedBytesCloud int
  receivedBytesEdge int
}

type Buffer struct {
  playback int
  completedUrls []string
  allUrls []string
}

type CurrentDownloadInfo struct {
  availableBits int
  startContact int
  endContact int
  timeOfLastContact int
  lastEdgeNodeDistance float64
  bufferedData map[string]bool
}

type Client struct {
  trajectory *Trajectory
  edgeNodes EdgeNodes
  lastConnectedEdgeNode *EdgeNode
  videoInfo Video
  stats DlStats
  buffer Buffer
  dlInfo CurrentDownloadInfo
  id string
}

func (client *Client) Id() string{
  return client.id
}

func NewClient(id string, traj *Trajectory, eNodes EdgeNodes, video Video, urls []string) (Client) {
  newStats := DlStats{pendingBytes:0, receivedBytesCloud:0, receivedBytesEdge: 0}
  buffer := Buffer{playback:0, completedUrls:make([]string, 0), allUrls: urls}
  dlInfo := CurrentDownloadInfo{availableBits: 0, startContact:0, endContact:0, timeOfLastContact:0, bufferedData:make(map[string]bool)}
  client := Client{id:id, trajectory:traj, edgeNodes:eNodes, videoInfo:video, stats:newStats, buffer:buffer, dlInfo:dlInfo}
  return client
}

func (client *Client) RegisterWithCloud(serverAddr string, startTime float64){
  points := make([]*pb.Coordinate, 0)
  for _, p := range client.trajectory.points{
    points = append(points, &pb.Coordinate{X: p.lat, Y:p.lon, Speed: p.speed, Time: p.timestamp})
  }
  route := &pb.Route{Points:points}
  req := pb.VideoRequest{VideoId:client.videoInfo.videoId, Route:route}

  cvreq := &pb.CVRequest{Request:&pb.CVRequest_Videorequest{&req}}
  conn, err := grpc.Dial(serverAddr, grpc.WithInsecure())
  if err != nil {
    log.Fatalf("did not connect to " + serverAddr )
  }
  defer conn.Close()
  c := pb.NewCVServerClient(conn)

  ctx, cancel := context.WithTimeout(context.Background(), time.Second * 5)
  defer cancel()
  resp, err := c.HandleCVRequest(ctx, cvreq)
  if err != nil{
    fmt.Println(err)
  }else {
    if resp.GetVideoreply() != nil{
      fmt.Printf("Got %d urls in reply ", len(resp.GetVideoreply().Urls))
      client.buffer.allUrls = resp.GetVideoreply().Urls
    } else{
      fmt.Printf("Invalid response")
    }
  }
}



func (client *Client) IsDone() bool{
  if (len(client.buffer.allUrls) > 0 && len(client.buffer.allUrls) == len(client.buffer.completedUrls)) || client.trajectory.HasEnded() {
    return true
  }
  return false
}

func (client *Client) GetEdgeBandwidth(edgeNode EdgeNode, distance float64) (float64){
  //if !client.IsDone() {
    //nearestEdge, distance := client.edgeNodes.GetNearestEdgeNode(client.trajectory.points[client.trajectory.curIdx])
    bw:= edgeNode.GetDownloadSpeedAtDistance(int(math.Ceil(distance)))

    if distance < 40{
      fmt.Printf("client %s near edge node %s bw = %f distance = %f\n", client.id, edgeNode.id, bw, distance)
      return bw
   }

   return  0
}

func (client *Client) getFilepath(url string) string{
  httpIdx := len([]rune("http://"))
  if strings.Contains(url, "ftp") {
    prefix :=  "http://ftp.itec.aau.at/DASHDataset2014/"
    runeStr := []rune(url)
    return string(runeStr[len([]rune(prefix)):])
  }
  tmp := []rune(url)[httpIdx:]
  filepathIdx := strings.Index(string(tmp), "/")
  return string(tmp[filepathIdx:])
}

func (client *Client) doGet(edgeNode EdgeNode, lastSegment string, shouldResetContact bool) string {
  ip := edgeNode.ip
  port := "8000"
  url := "http" + ip + ":" + port
  req, err := http.NewRequest("GET", url, nil)
  fmt.Printf("Make req to %s\n", ip)
  if err != nil {
    fmt.Println("Got error in making req")
  }
  query := req.URL.Query()
  if shouldResetContact {
   query.Add("reset", "true")
  } else if lastSegment == "" {
    filepath := client.getFilepath(client.buffer.allUrls[0])
    query.Add("key", filepath)
    query.Add("start_time", strconv.Itoa(client.dlInfo.startContact))
    query.Add("end_time", strconv.Itoa(client.dlInfo.endContact))
  } else {
    query.Add("segment", lastSegment)
  }
  req.URL.RawQuery = query.Encode()
  httpclient := &http.Client{}
  resp, err := httpclient.Do(req)
  if err != nil {
    fmt.Println(err)
    return ""
  }
  defer resp.Body.Close()
  respBody, _ := ioutil.ReadAll(resp.Body)
  if strings.Contains(string(respBody), "{}") {
    return ""
  }
  return string(respBody)
}

func (client *Client) getAvailableSegments(edgeNode EdgeNode)[]string {
  response:= client.doGet(edgeNode, "", false)
  fmt.Println(response)
  var segmentInfo map[string]interface{}
  json.Unmarshal([]byte(response), &segmentInfo)
  val, exists := segmentInfo["segments"]
  if exists {
    var segments []string
    json.Unmarshal([]byte(fmt.Sprintf("%v",val)), &segments)
    return segments
  }
  return nil
}

func (client *Client) getSegment(edgeNode EdgeNode, segment string) string {
  return client.doGet(edgeNode, segment, false)
}

func (client *Client) disconnectFromCurrentEdgeNode(edgeNode EdgeNode){
  _ = client.doGet(edgeNode, "", true)
}

func (client *Client) pretendDownload(edgeNode EdgeNode, segments []string, totalBytes int) {
  bytesAvailable := totalBytes
  curSegmentIdx := 0
  for {
    curSegment := segments[curSegmentIdx]
    val, exists := client.videoInfo.segments[curSegment]
    if !exists {
      panic("mismatch between client video and segment fetched")
    }
    fileSize := val.size
    if int(fileSize) < bytesAvailable {
      response := client.doGet(edgeNode, curSegment, false)
      if response != "" {
        bytesAvailable -= int(fileSize)
        client.dlInfo.bufferedData[curSegment] = true
        client.stats.receivedBytesEdge += int(fileSize)
      }
    } else {
      totalBytes = -1
    }
    curSegmentIdx += 1
  }
  fmt.Printf("Downloaded %d segments from node %s\n", curSegmentIdx, edgeNode.id)

}

func (client *Client) MakeEdgeRequest(edgeNode EdgeNode, bw float64) {
  if bw > 0 && &edgeNode != nil {
    client.dlInfo.availableBits += int(bw) // bps
    fmt.Printf("can download %d bits from %s\n", bw, edgeNode.id)
    totalBytes := client.dlInfo.availableBits / 8
    segments := client.getAvailableSegments(edgeNode)
    segmentsToDownload := make([]string, 0)
    if segments != nil {
      for _, seg := range segments {
        _, exists := client.dlInfo.bufferedData[seg]
        if !exists{
          segmentsToDownload = append(segmentsToDownload, seg)
        }
      }
    }
    if len(segmentsToDownload) == 0 {
      fmt.Printf("No segments available from %s\n", edgeNode.id)
      client.disconnectFromCurrentEdgeNode(edgeNode)
    }

    fmt.Printf("Pretending to download %d segments from %s", len(segmentsToDownload), edgeNode.id)
    client.pretendDownload(edgeNode, segmentsToDownload, totalBytes)
  }

}

func (client *Client) IsCloudRequestNecessary(segment string) bool {
  _, exists := client.dlInfo.bufferedData[segment]
  if exists {
    return false
  }
  return true
}

func (client *Client) FetchSegments(timestamp int) {
  if client.trajectory.HasEnded(){
    return
  }
  //fmt.Printf("Have %d urls in buffer \n", len(client.buffer.completedUrls))
  edgeNode := new(EdgeNode)
  edgeNode, distance := client.edgeNodes.GetNearestEdgeNode(client.trajectory.points[client.trajectory.curIdx])
  bw := 4e7 // LTE b/w
  if distance < 40 {
    bw = client.GetEdgeBandwidth(*edgeNode, distance)
  }
  lastBw := 0.0
  if client.lastConnectedEdgeNode != nil {
    lastBw = client.GetEdgeBandwidth(*client.lastConnectedEdgeNode, client.dlInfo.lastEdgeNodeDistance)
    fmt.Printf("last edge node = %s bw = %f\n", client.lastConnectedEdgeNode.id, lastBw)
  }
  if edgeNode == nil {
    if timestamp % 100 == 0 {
      fmt.Printf("time = %d will maybe do cloud fetch\n", timestamp)
    }
    if client.lastConnectedEdgeNode != nil {
      fmt.Printf("Losing contact with %s, will update dl bytes now\n", client.lastConnectedEdgeNode.id)
      client.MakeEdgeRequest(*client.lastConnectedEdgeNode, float64(lastBw))
      client.lastConnectedEdgeNode = nil
    }
    for {
      // all data downloaded
      if len(client.buffer.completedUrls) >= len(client.buffer.allUrls) {
        break
      }
      // sufficient data downloaded such that there isn't a stall
      if client.buffer.playback + 30 /* 30 sec buffer ahead */  >= len(client.buffer.completedUrls) {
        break
      }
      nextUrl :=  client.buffer.allUrls[len(client.buffer.completedUrls)]
      filepath := client.getFilepath(nextUrl)
      if !client.IsCloudRequestNecessary(filepath) {
        // client already buffered this data from the edge, so just add to downloaded list
        client.buffer.completedUrls = append(client.buffer.completedUrls, nextUrl)
        continue
      }
      // need to get data from cloud now
      val, exists := client.videoInfo.segments[filepath]
      if !exists {
        panic("segment not found in client video...")
      }
      filesize := val.size
      client.stats.receivedBytesCloud += int(filesize)
      client.buffer.completedUrls = append(client.buffer.completedUrls, nextUrl)
      client.dlInfo.bufferedData[filepath] = true
    }
  } else {
    fmt.Printf("Will contact edge nodes at time %d\n", timestamp)
    if client.lastConnectedEdgeNode == nil {
      fmt.Printf("New request, will just set contact with node %s\n", edgeNode.id)
      client.dlInfo.availableBits = int(bw)
      client.dlInfo.startContact = timestamp
      client.dlInfo.endContact = timestamp
      client.dlInfo.timeOfLastContact = timestamp
      client.lastConnectedEdgeNode = edgeNode
    } else if client.lastConnectedEdgeNode.id != edgeNode.id {
      fmt.Printf("Changing contact from %s to %s\n", client.lastConnectedEdgeNode.id, edgeNode.id)
      client.dlInfo.endContact = timestamp
      client.MakeEdgeRequest(*client.lastConnectedEdgeNode, float64(lastBw))
      client.dlInfo.availableBits = 0
      client.lastConnectedEdgeNode = edgeNode
      client.dlInfo.lastEdgeNodeDistance = distance
      client.dlInfo.timeOfLastContact = timestamp
    } else {
      if distance != client.dlInfo.lastEdgeNodeDistance {
        contactTime := timestamp - client.dlInfo.timeOfLastContact
        fmt.Printf("Update contact with %s to %d\n", client.lastConnectedEdgeNode.id, contactTime)
        bits := 0
        if contactTime == 0{
          bits = int(lastBw)
        } else{
          bits = int(lastBw) * contactTime
        }
        client.dlInfo.availableBits += bits
        client.dlInfo.lastEdgeNodeDistance = distance
        client.dlInfo.timeOfLastContact = timestamp
        client.dlInfo.endContact = timestamp
      }
    }
  }
}

func (client *Client) Move()/*wg *sync.WaitGroup)*/ {
 // defer wg.Done()
  client.trajectory.Advance()
  if client.trajectory.curIdx % 100 == 0 {
    fmt.Printf("Client at idx %d\n", client.trajectory.curIdx)
  }
  if client.trajectory.HasEnded() {
    fmt.Printf("Client %s finished at time %s\n", client.id, time.Now().String())
  }
}
