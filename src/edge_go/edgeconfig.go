package main

import (
	"encoding/json"
	"github.com/golang/glog"
	"io/ioutil"
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
}

type DownloadSource struct {
    src_id          string
    bandwidth       int64
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
    dlSources := make([]DownloadSource, 0)
    fstr, err := ioutil.ReadFile(dlSourceFile)
    if err != nil {
        glog.Exitf("Unable to read download source file %s err=%v", dlSourceFile, err)
    }
    json.Unmarshal([]byte(fstr), &dlSources)
    dlSourceMap := make(map[string]int64)
    for _, dlSource := range dlSources {
        dlSourceMap[dlSource.src_id] = dlSource.bandwidth
    }
    return dlSourceMap
}
