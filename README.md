### Running the code  
At the project root directory, start the edge and cloud servers as follows:  
Start cloud server  
```shell
$ python3 src/CVCloudServer.py -a localhost:50058 -c conf/cloudConfig.json  
```
Start edge server 
 ```shell
$ python3 src/EdgeDownloadServer.py -a localhost:50056 -c conf/edgeConfig.json  
```  
To test the setup, use the test client like so:  
```shell  
$ python3 src/CVCloudClient.py  
```
If the metadata server is not up, start it as usual from clairvoyanedge-comm/ repo on port 50051
```shell  
$ cd clairvoyantedge-comm/ && bash scripts/start_meta_svr.sh  
```  
Start evaluation on cloud server 
```shell   
$ cd clairvoyant2/ && python3 client_runner.py -a localhost:50058 -f ../eval/user_trajectories/ -d ../models/ -m ../models/model_map.csv -c ../conf/cloudConfig.json -i 0  
```
