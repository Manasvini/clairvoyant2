package main
import (
	"errors"
	"sync"
	"github.com/golang/glog"
)

type LinkStateTracker struct {
    mu                      sync.Mutex
    sourceDlSpeeds          map[string]int64 // edge node id : bits per second
    latestDlCompletionTime  map[string]int64 // edge node id: timestamp
    linkUtilization         map[string]int64 // how much of available bw is used
    startTime               int64
    currentTime             int64
}

func NewLinkStateTracker(sourceDlSpeeds map[string]int64) *LinkStateTracker {
    linkStateTracker := &LinkStateTracker{
                                    sourceDlSpeeds: sourceDlSpeeds,
                                    latestDlCompletionTime: make(map[string]int64),
                                    linkUtilization:make(map[string]int64),
                                    startTime:0,
                                    currentTime: 0,
                                }
    glog.Infof("Link state tracking %d nodes\n", len(sourceDlSpeeds))
    return linkStateTracker
}

func (lst *LinkStateTracker) GetLinkStates() map[string]float64 {
    utils := make(map[string]float64)
    for node, bytes := range lst.linkUtilization{
        utils[node] = float64(bytes)/ float64(lst.currentTime - lst.startTime)
    }
    return utils
}

func (lst *LinkStateTracker) IsDownloadPossible(dlSizeBytes int64, currentTime int64, deadline int64, source string) (bool, error) {
    //glog.Infof("bytes = %d, curtime = %d deadline=%s, src=%s", dlSizeBytes, currentTime, deadline, source)
    lst.mu.Lock()
    defer lst.mu.Unlock()
    bw, ok := lst.sourceDlSpeeds[source]
    if lst.startTime == 0{
        lst.startTime = currentTime
    }
    lst.currentTime = currentTime
    if !ok {
        return false, errors.New("Source " + source + " is invalid")
    }
    val, exists := lst.latestDlCompletionTime[source]
    dlTime := bw * dlSizeBytes * bw * 8 // to bits 
    if !exists {
        if currentTime + dlTime < deadline {
            return true, nil
        }
    } else {
       if val + dlTime < deadline {
            return true, nil
        }
    }
    return false, nil
}

func (lst *LinkStateTracker) UpdateDownloads(dlSizeBytes int64, currentTime int64, source string) error {
    lst.mu.Lock()
    defer lst.mu.Unlock()
    bw, ok := lst.sourceDlSpeeds[source]
    lst.currentTime = currentTime
    if !ok {
        return errors.New("Source " + source + " is invalid")
    }
    val, exists := lst.latestDlCompletionTime[source]
    dlTime := bw * dlSizeBytes * bw * 8 // to bits 
    if !exists {
        lst.latestDlCompletionTime[source] = currentTime + dlTime
        lst.linkUtilization[source] = dlSizeBytes
    } else {
        lst.latestDlCompletionTime[source] = val + dlTime
        lst.linkUtilization[source] += dlSizeBytes
    }
    return nil

}


