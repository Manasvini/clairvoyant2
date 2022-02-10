num_users=$1
num_edge=10
if [ -z $num_users ]; then
  num_users=1
fi

cd src
mkdir -p logs

for ((i=1;i<=num_users;i++)); do
  act_usr=$i 
  act_usr=16
  echo "clean redis"
  bash ../run_scripts/clear-redis.sh $num_edge
  echo "---"

  echo "clean and start content-svr" 
  bash ../run_scripts/start-content-svr.sh $num_edge
  echo "---"

  echo "kill edge"
  bash ../run_scripts/kill-edge-svrs.sh $num_edge
  echo "---"

  pid=$(ps -ax | grep "python3 cloud_runner.py" | head -n 1 | awk '{print $1}')
  echo "kill cloud"
  kill $pid
  echo "---"

  echo "start cloud"
  python3 cloud_runner.py -a 0.0.0.0:60050 \
                          -c ../conf/${num_edge}node_cloudConfig.json > logs/${act_usr}user_${num_edge}nodes_route-17min_user0_cloud.out 2>&1 &
  echo "---"

  echo "start edges"
  bash ../run_scripts/start-edge-svrs.sh $num_edge
  echo "---"

  echo "start client"
  python3 client_runner.py -a localhost:60050  \
                           -f ../eval/user_trajectories/ \
                           -d ../models/ \
                           -m ../models/model_map.csv \
                           -c ../conf/${num_edge}node_cloudConfig.json \
                           -o results/${act_usr}user_${num_edge}nodes_route-17min_user0.json \
                           --bench1 $act_usr > logs/${act_usr}user_${num_edge}nodes_route-17min_user0_client.out  2>&1
                           #-u user22 
done
