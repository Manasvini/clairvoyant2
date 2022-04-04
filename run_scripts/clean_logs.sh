echo "Deleting logs for cloud cv0"
ssh cv0 rm /home/cvuser/clairvoyant2/src/clientrunner_go/clientrunner_go.INFO
ssh cv0 rm /home/cvuser/clairvoyant2/src/clientrunner_go/clientrunner_go.WARNING
ssh cv0 rm /home/cvuser/clairvoyant2/src/clientrunner_go/clientrunner_go.ERROR

ssh cv0 rm /home/cvuser/clairvoyant2/logs/cloud.log
ssh cv0 rm /home/cvuser/clairvoyant2/logs/clock.log

for i in {1..10};
do
    echo "Deleting logs for edge cv$i"
    ssh cv$i rm /home/cvuser/clairvoyant2/src/edge_go/edge_go.INFO
    ssh cv$i rm /home/cvuser/clairvoyant2/src/edge_go/edge_go.WARNING
    ssh cv$i rm /home/cvuser/clairvoyant2/src/edge_go/edge_go.ERROR
    ssh cv$i rm /home/cvuser/clairvoyant2/src/edge_go/edge_go.FATAL
done
