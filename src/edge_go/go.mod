module github.gatech.edu/cs-epl/clairvoyant2/edge_go

go 1.17

replace github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant => ../client_go/clairvoyant

require (
	github.com/bluele/gcache v0.0.2
	github.com/golang/glog v1.0.0
	github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant v0.0.0-00010101000000-000000000000
	github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver v0.0.0-00010101000000-000000000000
	google.golang.org/grpc v1.43.0
)

require (
	github.com/golang/protobuf v1.5.0 // indirect
	github.com/madflojo/tasks v1.0.1 // indirect
	github.com/rs/xid v1.3.0 // indirect
	golang.org/x/net v0.0.0-20200822124328-c89045814202 // indirect
	golang.org/x/sys v0.0.0-20200323222414-85ca7c5b95cd // indirect
	golang.org/x/text v0.3.0 // indirect
	google.golang.org/genproto v0.0.0-20200526211855-cb27e3aa2013 // indirect
	google.golang.org/protobuf v1.27.1 // indirect
)

replace github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver => ../edge_go/contentserver

replace github.com/bluele/gcache => ../gcache-master
