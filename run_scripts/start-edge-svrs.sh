num_edge=$1
machine_prefix=$2
if [ -z $num_edge ]; then
  num_edge=10
fi


echo "flush edge redis"
bash run_scripts/clear-redis.sh $num_edge $machine_prefix

echo "restart-content svrs"
bash run_scripts/start-content-svr.sh $num_edge $machine_prefix

echo "restart edge svrs"
bash run_scripts/kill-edge-svrs.sh $num_edge $machine_prefix
for ((i=1;i<=num_edge;i++)); do
  id=$(($i-1))
  ssh ${machine_prefix}$i bash <<EOF
cd clairvoyant2
mkdir -p logs
bash run_scripts/start_edge.sh $id > logs/edge.out 2>&1 &
EOF
  echo "Started cv$i"
  done
