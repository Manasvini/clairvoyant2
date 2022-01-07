cd src
echo "start client"
#act_usr=16

python3 client_runner.py -a localhost:60050  \
                         -f ../eval/17mintrajectory/ \
                         -u user0_17min \
                         -d ../models/ \
                         -m ../models/model_map.csv \
                         -c ../conf/5node_cloudConfigCV1.json \
                         -o ../results/enhancements/single_user.json \
                         -n 1  #> logs/client.log 2>&1 & | tee logs/scale_10nodes_1user.out 
