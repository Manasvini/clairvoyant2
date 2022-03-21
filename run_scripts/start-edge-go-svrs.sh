num_edge=$1
machine_prefix=$2
if [ -z $num_edge ]; then
  num_edge=10
fi


echo "restart edge svrs"

bash run_scripts/kill-edge-go-svrs.sh $num_edge $machine_prefix

echo "building edge_go.."
curdir=$PWD
cd src/edge_go
go build -o edge_go
cd $curdir

echo "copy & start edge_go.."
for ((i=1;i<=num_edge;i++)); do
  confid=$(($i-1))
  nodeid=$i
  scp conf/scripts/tmp/edge/edgeConfig$confid.json cvuser@${machine_prefix}${nodeid}:~/clairvoyant2/conf/edgeConfig.json
  scp conf/scripts/tmp/download_source_info.json cvuser@${machine_prefix}${nodeid}:~/clairvoyant2/conf/

  rsync src/edge_go/edge_go cvuser@${machine_prefix}${nodeid}:~/clairvoyant2/src/edge_go/edge_go

  ssh ${machine_prefix}$i bash <<EOF
cd clairvoyant2/
mkdir -p logs
bash run_scripts/start_edge_go.sh 
EOF
  echo "Started golang ${machine_prefix}$i"
  done
