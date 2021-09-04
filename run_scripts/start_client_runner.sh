cd src
python3 client_runner.py -a localhost:60050  \
                         -f ../eval/user_trajectories/ \
                         -d ../models/ \
                         -m ../models/model_map.csv \
                         -c ../conf/cloudConfig.json \
                         -u user22 \
                         -o results/test.json 
