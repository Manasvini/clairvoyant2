rm -rf all_logs
mkdir all_logs
cp out.txt ./all_logs/out.txt

scp cvuser@cv1:~/clairvoyant2/logs/edge.out ./all_logs/edge1.out
scp cvuser@cv2:~/clairvoyant2/logs/edge.out ./all_logs/edge2.out
scp cvuser@cv3:~/clairvoyant2/logs/edge.out ./all_logs/edge3.out
scp cvuser@cv4:~/clairvoyant2/logs/edge.out ./all_logs/edge4.out
scp cvuser@cv5:~/clairvoyant2/logs/edge.out ./all_logs/edge5.out
scp cvuser@cv6:~/clairvoyant2/logs/edge.out ./all_logs/edge6.out
scp cvuser@cv7:~/clairvoyant2/logs/edge.out ./all_logs/edge7.out
scp cvuser@cv8:~/clairvoyant2/logs/edge.out ./all_logs/edge8.out
scp cvuser@cv9:~/clairvoyant2/logs/edge.out ./all_logs/edge9.out
scp cvuser@cv10:~/clairvoyant2/logs/edge.out ./all_logs/edge10.out

scp cvuser@cv1:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go1.INFO
scp cvuser@cv2:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go2.INFO
scp cvuser@cv3:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go3.INFO
scp cvuser@cv4:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go4.INFO
scp cvuser@cv5:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go5.INFO
scp cvuser@cv6:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go6.INFO
scp cvuser@cv7:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go7.INFO
scp cvuser@cv8:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go8.INFO
scp cvuser@cv9:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go9.INFO
scp cvuser@cv10:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go10.INFO


scp cvuser@cv1:~/clairvoyant2/logs.edge.out ./all_logs/edge_go1.out
scp cvuser@cv2:~/clairvoyant2/logs.edge.out ./all_logs/edge_go2.out
scp cvuser@cv3:~/clairvoyant2/logs.edge.out ./all_logs/edge_go3.out
scp cvuser@cv4:~/clairvoyant2/logs.edge.out ./all_logs/edge_go4.out
scp cvuser@cv5:~/clairvoyant2/logs.edge.out ./all_logs/edge_go5.out
scp cvuser@cv6:~/clairvoyant2/logs.edge.out ./all_logs/edge_go6.out
scp cvuser@cv7:~/clairvoyant2/logs.edge.out ./all_logs/edge_go7.out
scp cvuser@cv8:~/clairvoyant2/logs.edge.out ./all_logs/edge_go8.out
scp cvuser@cv9:~/clairvoyant2/logs.edge.out ./all_logs/edge_go9.out
scp cvuser@cv10:~/clairvoyant2/logs.edge.out ./all_logs/edge_go10.out

scp cvuser@cv0:~/clairvoyant2/logs/cloud.log ./all_logs/cloud.log
scp cvuser@cv0:~/clairvoyant2/logs/clock.log ./all_logs/clock.log

scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.INFO ./all_logs/clientrunner_go.INFO
scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.WARNING ./all_logs/clientrunner_go.WARNING
scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.ERROR ./all_logs/clientrunner_go.ERROR
