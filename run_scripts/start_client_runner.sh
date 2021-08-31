cd src
python3 client_runner.py -a localhost:50058  \
                         -f ../eval/user_trajectories/ \
                         -d ../models/ \
                         -m ../models/model_map.csv \
                         -c ../conf/cloudConfig.json \
                         -u user12 \
                         -o results/test.json 
