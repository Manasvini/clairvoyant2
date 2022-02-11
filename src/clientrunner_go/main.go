package main

import (
	"context"
	"flag"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/golang/glog"
	pb "github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant"
	"github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient"
	"google.golang.org/grpc"
)

func areAllClientsDone(clients []cvclient.Client) bool {
	for _, client := range clients {
		if !client.IsDone() {
			return false
		}
	}
	return true
}

func advanceClock() int64 {
	conn, err := grpc.Dial("0.0.0.0:8383", grpc.WithInsecure())
	if err != nil {
		panic("Could not connect to clock server")
	}
	defer conn.Close()
	clockClient := pb.NewClockServerClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	req := pb.AdvanceClock{}
	resp, err := clockClient.HandleAdvanceClock(ctx, &req)
	if err != nil {
		fmt.Println(err)
	} else {
		if resp != nil {
			return resp.CurTime
		}
	}
	return -1
}

func getFilesInDir(dirName string, isBench2 bool) []string {
	files, err := ioutil.ReadDir(dirName)
	if err != nil {
		panic(err)
	}
	fileNames := make([]string, 0)
	for _, file := range files {
		if file.IsDir() {
			continue
		}
		fileNames = append(fileNames, dirName+"/"+file.Name())
	}
	if isBench2 {
		return fileNames
	}

	rand.Seed(time.Now().UnixNano())
	rand.Shuffle(len(fileNames), func(i, j int) {
		fileNames[i], fileNames[j] = fileNames[j], fileNames[i]
	})
	return fileNames
}

func writeLogs(filename string, records []string) {
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		panic(err)
	}
	for _, record := range records {
		_, err = f.WriteString(record + "\n")
		if err != nil {
			panic(err)
		}
	}
}

func main() {

	defer glog.Flush() // flushes buffer, if any
	numUsers := flag.Int("n", 1 /*default*/, "number of users default=1")
	trajectoryDir := flag.String("t", "./", "directory containing user trajectories")
	serverAddr := flag.String("a", "0.0.0.0:60050", "cloud server address")
	//outputFile := flag.String("o", "./output.json", "output file name")
	edgeNodesFile := flag.String("e", "./input/5nodes_17min.csv", "file with x,y,id,ip,model for all edge nodes")
	numVideos := flag.Int("i", 20, "number of videos")
	videoFile := flag.String("f", "./input/bbb.csv", "video segments file")
	ofilename := flag.String("o", "output.txt", "output file name")
	bench2 := flag.String("b", "no", "benchmark 2(yes/no)")
	flag.Parse()
	fmt.Printf("Making flags, num users = %d traj dir = %s, server addr = %s, edge nodes file = %s, numVideos = %d, videoFile = %s\n", *numUsers, *trajectoryDir, *serverAddr, *edgeNodesFile, *numVideos, *videoFile)
	//edgeNodes := cvclient.EdgeNodes{}
	//edgeNodes.LoadFromFile(*edgeNodesFile)
	isBench2 := false
	if *bench2 == "yes" {
		isBench2 = true
	}
	urls := make([]string, 0)
	clients := make([]cvclient.Client, 0)
	glog.Infof("Make %d clients", *numUsers)
	trajectories := getFilesInDir(*trajectoryDir, isBench2)
	glog.Infof("files= %s, %s\n", trajectories[0], trajectories[1])
	i := 0
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	zipf := rand.NewZipf(r, 1.1, 1, uint64(*numVideos)-1)
	edgeNodes := cvclient.EdgeNodes{}
	edgeNodes.LoadFromFile(*edgeNodesFile)
	trajectories = []string{"../../eval/routes/user1917.csv"}
	/*trajectories = []string{"../../eval/enode_positions/microbenchmark/bench2/30users_new/user0.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user1.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user2.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user3.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user4.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user5.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user6.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user7.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user8.csv",
		"../../eval/enode_positions/microbenchmark/bench2/30users_new/user9.csv"}
	//trajectories = trajectories[:20]
	*/
	for _, f := range trajectories {
		fmt.Println(f)
		trajectory := cvclient.Trajectory{}
		trajectory.LoadFromFile(f)
		video := cvclient.Video{}

		//videoId := "v" + strconv.Itoa(rand.Intn(*numVideos - 2) + 2)
		videoId := "v" + strconv.Itoa(int(zipf.Uint64()+2))
		video.LoadFromFile(*videoFile, videoId)
		glog.Infof("file = %s video is %s\n", f, videoId)
		//"../../eval/enode_positions/17min_user0/user0_17min.csv")
		client := cvclient.NewClient(f, &trajectory, edgeNodes, video, urls)
		//client := cvclient.NewClient(f, &trajectory, edgeNodes, video, urls)
		clients = append(clients, client)
		i += 1
		if i == *numUsers {
			break
		}
	}
	glog.Infof("Created %d clients\n", len(clients))
	start := time.Now()
	for {

		timestamp := advanceClock()
		if timestamp%1000 == 0 {
			glog.Infof("timestamp is now %d\n", timestamp)
		}

		wg := new(sync.WaitGroup)
		for i, _ := range clients {
			if int64(clients[i].GetStartTime()) < int64(timestamp)+int64(100) && !clients[i].IsRegistered() {
				clients[i].RegisterWithCloud(*serverAddr, float64(timestamp))

				//For benchmark2
				//clients[i].ExplicitClose = true

			} else if !clients[i].IsDone() && int64(clients[i].GetStartTime()) < timestamp {
				wg.Add(1)
				go func(timestamp int64, client *cvclient.Client) {
					defer wg.Done()
					clientTimeAdvanced := false
					for {
						clientTimeAdvanced = client.FetchSegments(timestamp)
						if clientTimeAdvanced {
							break
						}
					}
				}(timestamp, &clients[i])
			}
		}
		wg.Wait()
		if areAllClientsDone(clients) {

			break
		}
	}
	fmt.Printf("\nelapsed = %s\n", time.Since(start))

	/*f, err := os.Create(*ofilename)
	ef, err := os.Create(*ofilename + ".edge")
	cf, err := os.Create(*ofilename + ".contact")
	if err != nil {
		panic(err)
	}
	_, err = f.WriteString("token,id,receivedBytesCloud,receivedBytesEdge\n")
	if err != nil {
		panic(err)
	}
	_, err = ef.WriteString("client,token,edgenode,timestamp,bytes\n")
	_, err = cf.WriteString("client,token,edgenode,timestamp,bytes\n")
	*/
	offloadFile := *ofilename
	edgeDlFile := *ofilename + ".edge"
	edgeContactFile := *ofilename + ".contact"
	edgeUtilityFile := *ofilename + ".utility"

	offloadHeader := []string{"token,id,receivedBytesCloud,receivedBytesEdge"}
	dlHeader := []string{"client,token,edgenode,timestamp,bytes"}
	utilHeader := []string{"client,token,edgenode,usefulSegCount,uselessSegCount,usefulBytes"}
	writeLogs(offloadFile, offloadHeader)
	writeLogs(edgeDlFile, dlHeader)
	writeLogs(edgeContactFile, dlHeader)
	writeLogs(edgeUtilityFile, utilHeader)

	for _, c := range clients {
		line := []string{c.PrintStats()}
		writeLogs(offloadFile, line)
		writeLogs(edgeDlFile, c.GetDlLogs())
		writeLogs(edgeContactFile, c.GetContactLogs())
		writeLogs(edgeUtilityFile, c.GetUtilLogs())
		/*_, err = f.WriteString(line)
		if err != nil {
			panic(err)
		}
		for _, dlLog := range c.GetDlLogs() {
			_, err = ef.WriteString(dlLog + "\n")
			if err != nil {
				panic(err)
			}
		}
		for _, dlLog := range c.GetContactLogs() {
			_, err = cf.WriteString(dlLog + "\n")
			if err != nil {
				panic(err)
			}
		}*/

	}

}
