cd src
echo "start client"
#act_usr=16

python3 client_runner.py -a localhost:60050  \
                         -f ../eval/user_trajectories/ \
                         -d ../models/ \
                         -m ../models/model_map.csv \
                         -c ../conf/bench3_5node_cloudConfig.json \
                         -o results/bench3_5nodes.json \
                         --bench3 1 2>&1 | tee logs/bench3_5nodes.out
                         #--bench2 200 2>&1 | tee logs/bench2_10nodes.out
                         #-c ../conf/bench2_10node_cloudConfig.json \
                         #--bench1 $act_usr 2>&1 | tee logs/${act_usr}user_client.out
                         #-u user22 
