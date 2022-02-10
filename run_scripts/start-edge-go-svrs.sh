num_edge=$1
machine_prefix=$2
if [ -z $num_edge ]; then
  num_edge=10
fi


echo "restart edge svrs"

bash run_scripts/kill-edge-go-svrs.sh $num_edge $machine_prefix
for ((i=1;i<=num_edge;i++)); do
  confid=$(($i-1))
  nodeid=$i
  scp conf/gen_conf/edgeConfig$confid.json cvuser@${machine_prefix}${nodeid}:~/clairvoyant2/conf/edgeConfig.json
  ssh ${machine_prefix}$i bash <<EOF
cd clairvoyant2/
mkdir -p logs
bash run_scripts/start_edge_go.sh 
EOF
  echo "Started golang cv$i"
  done
