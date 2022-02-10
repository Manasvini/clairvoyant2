#set -x
#trap read debug

num_edge=10
act_user=30
mode="local"

for mode in "local" "all2all" "curRouteNbr" "allRouteNbr"; do

  rm /tmp/bench2.json
  sed "s/WHATMODE/$mode/g" conf/bench2_10node_cloudConfig.json > /tmp/bench2.json

  echo "kill edge"
  bash run_scripts/kill-edge-svrs.sh $num_edge
  echo "---"

  sleep 2;

  echo $PWD

  pid=$(ps -ax | grep "python3 src/cloud_runner.py" | head -n 1 | awk '{print $1}')
  echo "kill cloud"
  kill $pid
  echo "---"

  sleep 2;

  echo "start cloud"
  mkdir -p logs/bench2
  template=logs/bench2/${act_usr}user_${num_edge}nodes_${mode}mode

  python3 src/cloud_runner.py -a 0.0.0.0:60050 \
                              -c /tmp/bench2.json > ${template}_cloud.out 2>&1 &

  sleep 2;
  echo "---"

  echo "start edges"
  bash run_scripts/start-edge-svrs.sh $num_edge
  echo "---"

  sleep 5;

  echo "start client"
  cd src
  python3 client_runner.py -a localhost:60050  \
                           -f ../eval/user_trajectories/ \
                           -d ../models/ \
                           -m ../models/model_map.csv \
                           -c /tmp/bench2.json \
                           -o results/bench2_${act_usr}user_${num_edge}nodes.json \
                           --bench2 200 2>&1
  cd ..
                           #--bench1 $act_usr > logs/bench2/${act_usr}user_${num_edge}nodes_${mode}mode_client.out  2>&1
                           #-u user22 

done
