## Clienrunner in golang!  
This document walks through the setup for getting the golang client runner to work. (It's at least 2x faster than the python client runner, probably a lot more).  
## Setup  
__step 1__: Install golang  
Follow the instructions [here](https://go.dev/doc/install). Additionally you can add `export PATH=$PATH:/usr/local/go/bin` to ~/.bashrc to make your life easier.  
  
__step 2__: Install protoc and related packages for golang  
Follow instructions listed in the [grpc website](https://grpc.io/docs/languages/go/quickstart/). Again, make sure you add `export PATH="$PATH:$(go env GOPATH)/bin"` to ~/.bashrc.  
  
__step 3__: Pull the `client_go` branch of this repo.  
  
__step4__: Try to run the client  
Start the client runner like so:  
```shell  
$ cd clientrunner_go  
$ go run . -log_dir="."  
```  
If you come across errors complaining about modules that need to be download, just do `go get <module name>` for the modules that it's complaining about.  
The above commands will start the client runner with the defaults (listed in main.go). Here's an example working command:  
```shell  
$ go run . -log_dir="." -t ../../eval/user_trajectories/ -e input/5node_17min.csv -i 20 -n 500    
``` 
The command starts client runner with 500 users, 20 videos and 5 nodes.  
## Edge Node Format  
The python client runner takes in separate arguments for the model directory, edge node positions and edge ids/ips. All of these inputs are combined into one file for golang client runner. An example is in `input/5node_17min.csv`.  
## Other gotchas  
Here are a few issues I ran into while developing the client.  
### CSV parsing   
CSV parsing in golang is not as intuitive as python. You have to declare the mapping of column indices to the data they represent. Change client\_go/cvclient/trajectory.go if you run into errors like "invalid lat/long"  being thrown from clairvoyantedge-meta.   
### Modifying protos/adding modules to client\_go    
#### New Module Creation  
If you're adding a new module, e.g, client\_go/util, first you need to declare the source for the module like this:  
```shell  
$ cd client_go/util  
$ go mod init github.gatech.edu/cs-epl/clairvoyant2/client_go/util  
```  
Whenever you're using `util` you can just `import ("github.gatech.edu/cs-epl/clairvoyant2/client_go/util")`  
#### Module Replacement  
Golang needs packages to be go-gettable, so anything you declare in the `import` section should have a valid URL. This is not always possible, so we can do module replacement so that the go.mod file lists the local sources for various packages. For example, if you're creating a new module client\_go/util and you're referring to util in clientrunner\_go, you can do module replacement like this:  
```shell  
$ cd clientrunner_go  
$ go mod edit -replace github.gatech.edu/cs-epl/clairvoyant2/client_go/util=../client_go/util  
```  
Note that you need to be in clientrunner\_go directory, and the go.mod in clientrunner\_go will have the link to util pointing to `../client_go/util`.  
#### Proto file changes    
If you're changing the proto files, you have to regenerate the corresponding golang files. For example, if you change clock.proto, you can regenerate the .go files like so:  
```shell  
#assuming you're in the project root,  
$ cd protos/  
$ protoc --go_out=../src/client_go/clairvoyant -I. --go_opt=paths=source_relative --go-grpc_out=../src/src/client_go/clairvoyant --go-grpc_opt=paths=source_relative clock.proto  
```   
Once you do this, you might still have to do module replacement to use the .go files corresponding to grpc/protobuf in your other go files.  
 

