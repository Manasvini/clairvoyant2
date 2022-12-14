module github.gatech.edu/cs-epl/clairvoyant2/src/clientrunner_go

go 1.17

require (
	github.com/golang/glog v1.0.0
	github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant v0.0.0-00010101000000-000000000000
	github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient v0.0.0-00010101000000-000000000000
	google.golang.org/grpc v1.43.0
)

require (
	github.com/golang/protobuf v1.5.0 // indirect
	github.com/umahmood/haversine v0.0.0-20151105152445-808ab04add26 // indirect
	github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver v0.0.0-00010101000000-000000000000 // indirect
	golang.org/x/net v0.0.0-20210405180319-a5a99cb37ef4 // indirect
	golang.org/x/sys v0.0.0-20210510120138-977fb7262007 // indirect
	golang.org/x/text v0.3.3 // indirect
	google.golang.org/genproto v0.0.0-20200526211855-cb27e3aa2013 // indirect
	google.golang.org/protobuf v1.27.1 // indirect
)

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/clairvoyant => ../client_go/clairvoyant

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/clairvoyantmeta => ../client_go/clairvoyantmeta

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient => ../client_go/cvclient

replace github.gatech.edu/cs-epl/clairvoyant2/cvclient => ../client_go/cvclient

replace github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant => ../client_go/clairvoyant

replace github.gatech.edu/cs-epl/clairvoyant2/edge_go/contentserver => ../edge_go/contentserver
