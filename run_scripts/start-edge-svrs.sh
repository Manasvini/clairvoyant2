num_edge=$1
if [ -z $num_edge ]; then
  num_edge=10
fi

echo "flush edge redis"
bash run_scripts/clear-redis.sh $num_edge

echo "restart-content svrs"
bash run_scripts/start-content-svr.sh $num_edge

for ((i=1;i<=num_edge;i++)); do
  id=$(($i-1))
  ssh cv2$i bash <<EOF
cd clairvoyant2
mkdir -p logs
bash run_scripts/start_edge.sh $id > logs/edge.out 2>&1 &
EOF
  echo "Started cv2$i"
  done
