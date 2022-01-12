package cvclient
import (
    "fmt"
    "time"
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
    "github.com/golang/glog"
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
  startContact int64
  endContact int64
  timeOfLastContact int64
  lastEdgeNodeDistance float64
  lastConnectedEdgeNode *EdgeNode
  bufferedData map[string]bool
}

type Client struct {
  trajectory *Trajectory
  edgeNodes *EdgeNodes
  videoInfo Video
  stats *DlStats
  buffer *Buffer
  dlInfo *CurrentDownloadInfo
  id string
}

func (client *Client) Id() string{
  return client.id
}

func NewClient(id string, traj *Trajectory, eNodes EdgeNodes, video Video, urls []string) (Client) {
  glog.Infof("Client %s has %d points in journey\n", id, len(traj.points))
  newStats := &DlStats{pendingBytes:0, receivedBytesCloud:0, receivedBytesEdge: 0}
  buffer := &Buffer{playback:0, completedUrls:make([]string, 0), allUrls: urls}
  dlInfo := &CurrentDownloadInfo{availableBits: 0, startContact:0, endContact:0, timeOfLastContact:0, bufferedData:make(map[string]bool), lastConnectedEdgeNode:nil}
  client := Client{id:id, trajectory:traj, edgeNodes:&eNodes, videoInfo:video, stats:newStats, buffer:buffer, dlInfo:dlInfo }
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
  glog.Infof("client %s make req to cloud server at %s for video %s", client.id, serverAddr, client.videoInfo.videoId)
  conn, err := grpc.Dial(serverAddr, grpc.WithInsecure())
  if err != nil {
    glog.Fatalf("did not connect to " + serverAddr )
  }
  defer conn.Close()
  c := pb.NewCVServerClient(conn)

  ctx, cancel := context.WithTimeout(context.Background(), time.Second * 15)
  defer cancel()
  resp, err := c.HandleCVRequest(ctx, cvreq)
  if err != nil{
    glog.Error(err)
  }else {
    if resp.GetVideoreply() != nil{
      glog.Infof("clinet %s Got %d urls in reply\n", client.id, len(resp.GetVideoreply().Urls))
      client.buffer.allUrls = resp.GetVideoreply().Urls
    } else{
      glog.Errorf("client %s got invalid response for video request", client.id)
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
      glog.Infof("client %s near edge node %s bw = %f distance = %f\n", client.id, edgeNode.id, bw, distance)
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
  url := "http://" + ip + ":" + port
  req, err := http.NewRequest("GET", url, nil)
  if err != nil {
    glog.Error("Got error in making req")
  }
  query := req.URL.Query()
  if shouldResetContact {
   query.Add("reset", "true")
  } else if lastSegment == "" {
    glog.Infof("buffer has %d urls\n", len(client.buffer.allUrls))
    filepath := client.getFilepath(client.buffer.allUrls[0])
    parts := strings.Split(filepath, "/")
    key := ""
    for _, part := range parts {
      if strings.Contains(part, "BigBuckBunny") {
        key = part
        break
      }
    }
    if key == "" {
      panic("Could not create key for edge query")
    }
    query.Add("key", key)
    query.Add("start_time", strconv.FormatInt(client.dlInfo.startContact, 10))
    query.Add("end_time", strconv.FormatInt(client.dlInfo.endContact, 10))
  } else {
    query.Add("segment", lastSegment)
  }
  req.URL.RawQuery = query.Encode()
  httpclient := &http.Client{}
  resp, err := httpclient.Do(req)
  if err != nil {
    glog.Info(err)
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
  var segmentInfo map[string][]string
  json.Unmarshal([]byte(response), &segmentInfo)
  val, exists := segmentInfo["segments"]
  if exists {
    var segments []string
    segments = val
    glog.Infof("got %d segments", len(segments))
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
    if len(segments) == curSegmentIdx {
      break
    }
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
  glog.Infof("Downloaded %d segments from node %s for client %s\n", curSegmentIdx, edgeNode.id, client.id)

}

func (client *Client) MakeEdgeRequest(edgeNode EdgeNode, bw float64) {
  if  &edgeNode != nil {
    client.dlInfo.availableBits += int(bw) // bps
    glog.Infof("client %s can download %d bits from %s\n", client.id, client.dlInfo.availableBits, edgeNode.id)
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
      glog.Infof("No segments available from %s for client %s\n", edgeNode.id, client.id)
      client.disconnectFromCurrentEdgeNode(edgeNode)
    } else {
      glog.Infof("client %s pretending to download %d segments from %s\n", client.id, len(segmentsToDownload), edgeNode.id)
      client.pretendDownload(edgeNode, segmentsToDownload, totalBytes)
    }
  }

}

func (client *Client) IsCloudRequestNecessary(segment string) bool {
  _, exists := client.dlInfo.bufferedData[segment]
  if exists {
    return false
  }
  return true
}

func (client *Client) FetchSegments(timestamp int64) {
  client.Move()
  if client.trajectory.HasEnded(){
    return
  }
  edgeNode, distance := client.edgeNodes.GetNearestEdgeNode(client.trajectory.points[client.trajectory.curIdx])
  bw := 4e7 // LTE b/w
  var edgeNodePtr *EdgeNode
  edgeNodePtr = new(EdgeNode)
  if distance < 40 {
    bw = client.GetEdgeBandwidth(edgeNode, distance)
    edgeNodePtr = &edgeNode
  } else{
    edgeNodePtr = nil
  }
  if edgeNodePtr != nil{
  }
  lastBw := 0.0
  if client.dlInfo.lastConnectedEdgeNode != nil {
    lastBw = client.GetEdgeBandwidth(*(client.dlInfo.lastConnectedEdgeNode), client.dlInfo.lastEdgeNodeDistance)
    glog.Infof("for client %s last edge node = %s bw = %f\n", client.id, client.dlInfo.lastConnectedEdgeNode.id, lastBw)
  }
  if edgeNodePtr == nil {
    if timestamp % 100 == 0 {
      glog.Infof("time = %d will maybe do cloud fetch\n", timestamp)
    }
    if client.dlInfo.lastConnectedEdgeNode != nil {
      glog.Infof("Client %s Losing contact with %s, will update dl bytes now\n", client.id, client.dlInfo.lastConnectedEdgeNode.id)
      client.MakeEdgeRequest(*(client.dlInfo.lastConnectedEdgeNode), float64(lastBw))
      client.dlInfo.lastConnectedEdgeNode = nil
    }
    for {
      // all data downloaded
      if len(client.buffer.completedUrls) >= len(client.buffer.allUrls) {
        break
      }
      // sufficient data downloaded such that there isn't a stall
      if client.buffer.playback + 30 /* 30 sec buffer ahead */  <= len(client.buffer.completedUrls) {
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
      //glog.Infof("clietn %s segment is %s\n", client.id, filepath)
      if !exists {
        panic("segment not found in client video...")
      }
      filesize := val.size
      client.stats.receivedBytesCloud += int(filesize)
      client.buffer.completedUrls = append(client.buffer.completedUrls, nextUrl)
      client.dlInfo.bufferedData[filepath] = true
    }
  } else {
    glog.Infof("Will maybe contact edge nodes at time %d\n", timestamp)
    if client.dlInfo.lastConnectedEdgeNode == nil {
      glog.Infof("New request, will just set contact with node %s\n", edgeNode.id)
      client.dlInfo.availableBits = int(bw)
      client.dlInfo.startContact = timestamp
      client.dlInfo.endContact = timestamp
      client.dlInfo.timeOfLastContact = timestamp
      client.dlInfo.lastEdgeNodeDistance = distance
      client.dlInfo.lastConnectedEdgeNode = edgeNodePtr
    } else if client.dlInfo.lastConnectedEdgeNode.id != edgeNodePtr.id {
      glog.Infof("Client %s Changing contact from %s to %s\n", client.id, client.dlInfo.lastConnectedEdgeNode.id, edgeNode.id)
      client.dlInfo.endContact = timestamp
      client.MakeEdgeRequest(*(client.dlInfo.lastConnectedEdgeNode), float64(lastBw))
      client.dlInfo.availableBits = 0
      client.dlInfo.lastConnectedEdgeNode = edgeNodePtr
      client.dlInfo.lastEdgeNodeDistance = distance
      client.dlInfo.timeOfLastContact = timestamp
    } else {
      if distance != client.dlInfo.lastEdgeNodeDistance {
        contactTime := timestamp - client.dlInfo.timeOfLastContact
        glog.Infof("Update contact with %s to %d\n", client.dlInfo.lastConnectedEdgeNode.id, contactTime)
        bits := 0
        if contactTime == 0{
          bits = int(lastBw)
        } else{
          bits = int(lastBw) * int(contactTime)
        }
        client.dlInfo.availableBits += bits
        client.dlInfo.lastEdgeNodeDistance = distance
        client.dlInfo.timeOfLastContact = timestamp
        client.dlInfo.endContact = timestamp
      }
    }
    if client.dlInfo.lastConnectedEdgeNode == nil {
      glog.Warningf("something fishy going on with %s\n", client.id)
    }
  }
  if float64(timestamp) > client.trajectory.points[0].timestamp {
    client.buffer.playback += 1
  }
}

func (client *Client) GetStartTime() float64 {
  return client.trajectory.points[0].timestamp
}

func (client *Client) IsRegistered() bool {
  return len(client.buffer.allUrls) > 0
}

func (client *Client) PrintStats()(string) {
  return fmt.Sprintf( "%s,%d,%d\n",client.id, client.stats.receivedBytesCloud, client.stats.receivedBytesEdge)

}

func (client *Client) Move()/*wg *sync.WaitGroup)*/ {
 // defer wg.Done()
  if client.trajectory.HasEnded() {
    return
  }
  client.trajectory.Advance()

  if client.trajectory.curIdx % 100 == 0 {
    glog.Infof("Client at idx %d\n", client.trajectory.curIdx)
  }
}
