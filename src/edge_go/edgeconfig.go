package main

import (
	"encoding/json"
	"github.com/golang/glog"
	"io/ioutil"
//    "os"
)

type EdgeConfig struct {
	ModelFile               string   `json:"modelFile"`
	MissedDeliveryThreshold int      `json:"missedDeliveryThreshold"`
	TimeScale               int      `json:"timeScale"`
	RedisHost               string   `json:"redisHost"`
	RedisPort               int      `json:"redisPort"`
	NodeID                  string   `json:"nodeId"`
	IntervalSeconds         int      `json:"intervalSeconds"`
	ServerAddress           string   `json:"serverAddress"`
	MonServerAddress        string   `json:"monServerAddress"`
	MonInterval             int      `json:"monInterval"`
	DownloadSourceFile      string   `json:"downloadSourceFile"`
	ContentServerAddress    string   `json:"contentServerAddress"`
	ContentServerMaxClients int      `json:"contentServerMaxClients"`
	EdgeServerAddress       string   `json:"edgeServerAddress"`
	CacheSize               int      `json:"cacheSize"`
	CacheType               string   `json:"cacheType"`
	ClockServerAddr		string	 `json:"clockServerAddr"`
	ProcastinationProportion float64      `json:"procastinationProportion"`
}

type DownloadSource struct {
    SrcId          string          `json:"src_id"`
    SrcIp          string          `json:"src_ip"`
    Bandwidth       int64           `json:"bandwidth"`
}

func parseConfig(configFile string) EdgeConfig {

	config := EdgeConfig{}
	bstr, err := ioutil.ReadFile(configFile)
	if err != nil {
		glog.Exitf("Unable to read Edge Config = %s, err=%v", configFile, err)
	}

	json.Unmarshal(bstr, &config)
	return config
}

func parseSources(dlSourceFile string) map[string]int64 {
    var dlSources []DownloadSource
    fstr, err := ioutil.ReadFile(dlSourceFile)
    glog.Infof("file is :%s", dlSourceFile)
    if err != nil {
        glog.Exitf("Unable to read download source file %s err=%v", dlSourceFile, err)
    }
    glog.Infof("fstr is %s", fstr)
    json.Unmarshal([]byte(fstr), &dlSources)
    dlSourceMap := make(map[string]int64)
    for _, dlSource := range dlSources {
        glog.Infof("dlSource is %s", dlSource.SrcIp)
        dlSourceMap[dlSource.SrcIp] = dlSource.Bandwidth
    }
    return dlSourceMap
}
