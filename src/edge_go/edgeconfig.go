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
	DownloadSources         []string //*FIXME*
	ContentServerAddress    string   `json:"contentServerAddress"`
	ContentServerMaxClients int      `json:"contentServerMaxClients"`
	EdgeServerAddress       string   `json:"edgeServerAddress"`
	CacheSize               int      `json:"cacheSize"`
	CacheType               string   `json:"cacheType"`
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
