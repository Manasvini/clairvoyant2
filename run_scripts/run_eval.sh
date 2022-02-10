num_users=(400)
num_trials=3
num_edge=10
cur_dir=$PWD
src_dir=$cur_dir/src
trials=(4 5 6)
for num_user in "${num_users[@]}"; do
  for numtrial in "${trials[@]}"; do
    echo "num users =  $num_user  trial num  $numtrial" $PWD
    cd $src_dir
    mkdir -p logs
    
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
    
    echo "start cloud" $cur_dir
    cd $cur_dir
    bash run_scripts/start_cloud_services.sh $num_edge
    #python3 cloud_runner.py -a 0.0.0.0:60050 \
    #                        -c ../conf/${num_edge}node_cloudConfig.json > logs/${act_usr}user_${num_edge}nodes_route-17min_user0_cloud.out 2>&1 &
    
    echo "---"
    echo $PWD
    echo "start edges"
    bash run_scripts/start-edge-svrs.sh $num_edge
    echo "---"
    cd $src_dir
    echo "start client"
    python3 client_runner.py -a localhost:60050  \
                             -f ../eval/edge_routes/final_routes/ \
                             -d ../models/ \
                             -m ../models/model_map.csv \
                             -c ../conf/${num_edge}node_monacoCloudConfig.json \
                             -o ../results/final_evals/last_mile/${num_edge}nodes_${num_user}user_$numtrial.json \
                              -n $num_user
#                             --bench1 $act_usr > logs/${act_usr}user_${num_edge}nodes_route-17min_user0_client.out  2>&1
                             #-u user22 
    
    mv ../results/bench2/all2all_results.csv ../results/final_evals/backhaul/all2all_results_${num_edge}nodes_${num_user}users_$numtrial.csv                         
  done
done
