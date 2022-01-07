module github.gatech.edu/cs-epl/clairvoyant2/src/clientrunner_go

go 1.17

require github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient v0.0.0-00010101000000-000000000000

require (
	github.com/golang/protobuf v1.4.3 // indirect
	github.com/umahmood/haversine v0.0.0-20151105152445-808ab04add26 // indirect
	github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant v0.0.0-00010101000000-000000000000 // indirect
	golang.org/x/net v0.0.0-20200822124328-c89045814202 // indirect
	golang.org/x/sys v0.0.0-20200323222414-85ca7c5b95cd // indirect
	golang.org/x/text v0.3.0 // indirect
	google.golang.org/genproto v0.0.0-20200526211855-cb27e3aa2013 // indirect
	google.golang.org/grpc v1.43.0 // indirect
	google.golang.org/protobuf v1.25.0 // indirect
)

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/clairvoyant => ../client_go/clairvoyant

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/clairvoyantmeta => ../client_go/clairvoyantmeta

replace github.gatech.edu/cs-epl/clairvoyant2/src/client_go/cvclient => ../client_go/cvclient

replace github.gatech.edu/cs-epl/clairvoyant2/cvclient => ../client_go/cvclient

replace github.gatech.edu/cs-epl/clairvoyant2/client_go/clairvoyant => ../client_go/clairvoyant
