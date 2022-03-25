cd ~
rm -rf all_logs
mkdir all_logs

cp out.txt ./all_logs/out.txt
cp out_err.txt ./all_logs/out_err.txt
cp out_xp.txt ./all_logs/out_xp.txt
cp out_xp_err.txt ./all_logs/out_xp_err.txt

echo "Getting logs from cloud cv0"
scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.INFO ./all_logs/clientrunner_go.INFO
scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.WARNING ./all_logs/clientrunner_go.WARNING
scp cvuser@cv0:~/clairvoyant2/src/clientrunner_go/clientrunner_go.ERROR ./all_logs/clientrunner_go.ERROR


for i in {1..10};
do
    echo "Getting logs from edge cv$i"
    scp cvuser@cv$i:~/clairvoyant2/src/edge_go/edge_go.INFO ./all_logs/edge_go$i.INFO
    scp cvuser@cv$i:~/clairvoyant2/src/edge_go/edge_go.WARNING ./all_logs/edge_go$i.WARNING
    scp cvuser@cv$i:~/clairvoyant2/src/edge_go/edge_go.ERROR ./all_logs/edge_go$i.ERROR
    scp cvuser@cv$i:~/clairvoyant2/src/edge_go/edge_go.FATAL ./all_logs/edge_go$i.FATAL
    
    scp cvuser@cv$i:~/clairvoyant2/logs.edge.out ./all_logs/edge_go$i.out
done
