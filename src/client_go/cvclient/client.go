package cvclient
import (
    "fmt"
    "time"
    "google.golang.org/grpc"
    "context"
    pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
    cpb "github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver"
//    "sync"
    "math"
    "io/ioutil"
    "net/http"
    "encoding/json"
    "strings"
    "strconv"
    "github.com/golang/glog"
  )

type DlLog struct {
  timestamp int64
  bytes int64
  edgeNode string
}

type DlStats struct {
  pendingBytes int
  receivedBytesCloud int
  receivedBytesEdge int
  dlLogs []DlLog
  contactLogs []DlLog
}

type Buffer struct {
  playback int
  completedUrls []string
  allUrls []string
}

type CurrentDownloadInfo struct {
  availableBits int64
  startContact int64
  endContact int64
  timeOfLastContact int64
  lastEdgeNodeDistance float64
  lastConnectedEdgeNode *EdgeNode
  bufferedData map[string]bool
  tentativeLogs []DlLog
}

type Client struct {
  trajectory *Trajectory
  edgeNodes *EdgeNodes
  videoInfo Video
  stats *DlStats
  buffer *Buffer
  dlInfo *CurrentDownloadInfo
  id string
  token *int64
}

func (client *Client) Id() string{
  return client.id
}

func NewClient(id string, traj *Trajectory, eNodes EdgeNodes, video Video, urls []string) (Client) {
  glog.Infof("Client %s has %d points in journey\n", id, len(traj.points))
  dlLogs := make([]DlLog, 0)
  tdlLogs := make([]DlLog, 0)
  cLogs := make([]DlLog, 0)
  newStats := &DlStats{pendingBytes:0, receivedBytesCloud:0, receivedBytesEdge: 0, dlLogs: dlLogs, contactLogs:cLogs}
  buffer := &Buffer{playback:0, completedUrls:make([]string, 0), allUrls: urls}
  dlInfo := &CurrentDownloadInfo{availableBits: 0,
                                startContact:0,
                                endContact:0,
                                timeOfLastContact:0,
                                bufferedData:make(map[string]bool),
                                lastConnectedEdgeNode:nil,
                                tentativeLogs: tdlLogs}
  client := Client{id:id,
                  trajectory:traj,
                  edgeNodes:&eNodes,
                  videoInfo:video,
                  stats:newStats,
                  buffer:buffer,
                  dlInfo:dlInfo,
                  token: new(int64)}
  return client
}

func (client *Client) RegisterWithCloud(serverAddr string, startTime float64){
  points := make([]*pb.Coordinate, 0)
  for _, p := range client.trajectory.points{
    points = append(points, &pb.Coordinate{X: p.lat, Y:p.lon, Speed: p.speed, Time: p.timestamp})
  }
  route := &pb.Route{Points:points}
  req := pb.VideoRequest{VideoId:client.videoInfo.videoId, Route:route, Timestamp:int64(startTime)}

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
      client.buffer.allUrls = resp.GetVideoreply().Urls
      *client.token = resp.GetVideoreply().TokenId
      glog.Infof("clinet %s Got %d urls in reply token is %d\n", client.id, len(resp.GetVideoreply().Urls), client.token)

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
  glog.Errorf("idx is %d, url is %s filepath is %s", filepathIdx, tmp, tmp[filepathIdx:])
  return string(tmp[filepathIdx:])
}

func (client *Client) doGetGRPC(edgeNode EdgeNode, lastSegment string, shouldResetContact bool) []string {
  address := edgeNode.ip + ":" + "8000"
  conn, err := grpc.Dial(address, grpc.WithInsecure())
  defer conn.Close()
  contentClient := cpb.NewContentClient(conn)

  segmentRequest := cpb.SegmentRequest{
      RouteId: *client.token,
      SegmentId : lastSegment,
      StartTime : client.dlInfo.startContact,
      EndTime : client.dlInfo.endContact,
      Remove : shouldResetContact,
    }

  ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
  defer cancel()
  resp, err := contentClient.GetSegment(ctx, &segmentRequest)
  if err == nil{
    return resp.GetSegments()
  }
  glog.Error(err)
  return  nil
}

//NOTE: Changing to grpc based content server!
func (client *Client) doGet(edgeNode EdgeNode, lastSegment string, shouldResetContact bool) []string {
  return client.doGetGRPC(edgeNode, lastSegment, shouldResetContact)
}

func (client *Client) doGetNormal(edgeNode EdgeNode, lastSegment string, shouldResetContact bool) []string {
  ip := edgeNode.ip
  port := "8000"
  url := "http://" + ip + ":" + port
  req, err := http.NewRequest("GET", url, nil)
  req.Header.Set("token", strconv.FormatInt(*client.token, 10))
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
      if strings.Contains(part, "BigBuckBunny") || strings.Contains(part, "bbb"){
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
    return nil
  }
  defer resp.Body.Close()
  respBody, _ := ioutil.ReadAll(resp.Body)
  if strings.Contains(string(respBody), "{}") {
    return nil
  }

  respBodyStr := string(respBody)
  if strings.Contains(respBodyStr, "segments"){
    //this is first request
    var segmentInfo map[string][]string
    json.Unmarshal([]byte(respBodyStr), &segmentInfo)
    if val, exists := segmentInfo["segments"]; exists {
      return val
    }
    return nil
  } else {
    return []string{respBodyStr}
  }
}

func (client *Client) getAvailableSegments(edgeNode EdgeNode)[]string {
  segments:= client.doGet(edgeNode, "", false)

  if len(segments) > 0 {
    glog.Infof("Client %s got %d segments from %s\n", client.id, len(segments), edgeNode.id)
    return segments
  }

  glog.Infof("client %s did not get any segments from %s\n", client.id, edgeNode.id)
  return nil
}


func (client *Client) disconnectFromCurrentEdgeNode(edgeNode EdgeNode){
  _ = client.doGet(edgeNode, "", true)
}

func (client *Client) pretendDownload(edgeNode EdgeNode, segments []string, totalBytes int64) int64 {
  bytesAvailable := int64(totalBytes)
  curSegmentIdx := 0
  var bytesDl int64
  bytesDl = 0
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
    if int64(fileSize) < bytesAvailable {
      segments := client.doGet(edgeNode, curSegment, false)
      if len(segments) > 0 {
        bytesAvailable -= int64(fileSize)
        client.dlInfo.bufferedData[curSegment] = true
        client.stats.receivedBytesEdge += int(fileSize)
        bytesDl += int64(fileSize)
      }
    } else {
      break
    }
    curSegmentIdx += 1
  }
  glog.Infof("Downloaded %d segments from node %s for client %s bytes dl = %d\n", curSegmentIdx, edgeNode.id, client.id, bytesDl)
  return bytesDl
}

func (client *Client) MakeEdgeRequest(edgeNode EdgeNode, bw float64) {
  var bytesDownloaded int64
  bytesDownloaded = 0
  if  &edgeNode != nil {
    client.dlInfo.availableBits += int64(bw) // bps
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
      bytesDownloaded = client.pretendDownload(edgeNode, segmentsToDownload, totalBytes)
    }
  }
  glog.Infof("client %s has %d urls so far", client.id, len(client.buffer.completedUrls))
  if len(client.buffer.allUrls) > len(client.buffer.completedUrls){
    client.stats.contactLogs = append(client.stats.contactLogs, client.dlInfo.tentativeLogs...)
  }
  if bytesDownloaded > 0{
    client.stats.dlLogs = append(client.stats.dlLogs, client.dlInfo.tentativeLogs...)
    glog.Infof("Client %s has %d dl logs", client.id, len(client.stats.dlLogs))
    client.dlInfo.tentativeLogs = make([]DlLog, 0)
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
     if client.dlInfo.lastConnectedEdgeNode != nil {
      lastBw := client.GetEdgeBandwidth(*(client.dlInfo.lastConnectedEdgeNode), client.dlInfo.lastEdgeNodeDistance)
   glog.Infof("Client %s about to stop. Will finish edge actions with node %s\n", client.id, client.dlInfo.lastConnectedEdgeNode.id)
      client.MakeEdgeRequest(*(client.dlInfo.lastConnectedEdgeNode), float64(lastBw))
      client.dlInfo.lastConnectedEdgeNode = nil
    }
    return
  }
  edgeNode, distance := client.edgeNodes.GetNearestEdgeNode(client.trajectory.points[client.trajectory.curIdx])
  bw := 4e7 // LTE b/w
  var edgeNodePtr *EdgeNode
  edgeNodePtr = new(EdgeNode)
  if distance < 40 /*metres*/ {
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
      if !exists {
	glog.Errorf("segment %s not found in video of client %s", filepath, client.id);
        panic("segment not found in client video...")
      }
      filesize := val.size
      client.stats.receivedBytesCloud += int(filesize)
      client.buffer.completedUrls = append(client.buffer.completedUrls, nextUrl)
      client.dlInfo.bufferedData[filepath] = true
    }
  } else {
    if client.dlInfo.lastConnectedEdgeNode == nil {
      glog.Infof("New request, will just set contact with node %s\n", edgeNode.id)
      client.dlInfo.availableBits = int64(bw)
      client.dlInfo.startContact = timestamp
      client.dlInfo.endContact = timestamp
      client.dlInfo.timeOfLastContact = timestamp
      client.dlInfo.lastEdgeNodeDistance = distance
      client.dlInfo.lastConnectedEdgeNode = edgeNodePtr
      dlLog := DlLog{timestamp:timestamp, edgeNode:client.dlInfo.lastConnectedEdgeNode.id, bytes:int64(bw)/8}
      client.dlInfo.tentativeLogs = append(client.dlInfo.tentativeLogs, dlLog)
      glog.Infof("tentaive logs for client %s has %d entries", client.id, len(client.dlInfo.tentativeLogs))
    } else if client.dlInfo.lastConnectedEdgeNode.id != edgeNodePtr.id {
      glog.Infof("Client %s Changing contact from %s to %s\n", client.id, client.dlInfo.lastConnectedEdgeNode.id, edgeNode.id)
      client.dlInfo.endContact = timestamp
      glog.Infof("tentaive logs for client %s has %d entries", client.id, len(client.dlInfo.tentativeLogs))
      client.MakeEdgeRequest(*(client.dlInfo.lastConnectedEdgeNode), float64(lastBw))
      client.dlInfo.availableBits = 0
      client.dlInfo.lastConnectedEdgeNode = edgeNodePtr
      client.dlInfo.lastEdgeNodeDistance = distance
      client.dlInfo.timeOfLastContact = timestamp
      client.dlInfo.tentativeLogs = make([]DlLog, 0)
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
        client.dlInfo.availableBits += int64(bits)
        client.dlInfo.lastEdgeNodeDistance = distance
        client.dlInfo.timeOfLastContact = timestamp
        client.dlInfo.endContact = timestamp
        dlLog := DlLog{timestamp:timestamp, edgeNode:client.dlInfo.lastConnectedEdgeNode.id, bytes:int64(bits)/8}
        client.dlInfo.tentativeLogs = append(client.dlInfo.tentativeLogs, dlLog)
       glog.Infof("tentaive logs for client %s has %d entries", client.id, len(client.dlInfo.tentativeLogs))
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
  glog.Infof("printing for client %s token %d", client.id, client.token)
  return fmt.Sprintf( "%d,%s,%d,%d\n",*client.token, client.id, client.stats.receivedBytesCloud, client.stats.receivedBytesEdge)

}

func (client *Client) Move() {
  if client.trajectory.HasEnded() {
    return
  }
  client.trajectory.Advance()

  if client.trajectory.curIdx % 100 == 0 {
    glog.Infof("Client at idx %d\n", client.trajectory.curIdx)
  }
}

func (client *Client) getLogs(logs []DlLog)[]string{
  loglines := make([]string, 0)
  for _, dlLog := range logs {
      loglines = append(loglines, client.id + "," + dlLog.edgeNode + "," + strconv.FormatInt(dlLog.timestamp, 10) +","+ strconv.FormatInt(dlLog.bytes, 10))
  }
  return loglines

}

func (client *Client) GetDlLogs()[]string{
  return client.getLogs(client.stats.dlLogs)
}

func (client *Client) GetContactLogs()[]string{
  return client.getLogs(client.stats.contactLogs)
}
