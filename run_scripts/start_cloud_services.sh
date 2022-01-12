#!/bin/bash
num_nodes=$1
conf=$2
node_pos=$3
num_videos=$4
cd
cd clairvoyantedge-metadata

curdir=$(pwd)
#pkill redis
#rm -rf cluster/*
bash scripts/start_redis_cluster.sh 3

sleep 15

echo "adding nodes"
cd ~/clairvoyant2

python3 eval/add_nodes.py -n $num_nodes -p "192.168.160." -s 22 -i 0 -f $node_pos

cd $curdir
pkill clairvoyant
sleep 5
bash scripts/start_meta_svr.sh > ./logs/meta_svr.out 2>&1 &

cd scripts
bash ./video_creator.sh ../build/metadata/scripts/data-uploader $4 bbb.csv
#
pkill python3
cd ~/clairvoyant2
mkdir -p logs
#

#python3 src/CVCloudServer.py -a 0.0.0.0:50059 -c conf/${num_nodes}node_cloudConfig.json  > logs/cloudserver.log 2>&1 &
python3 src/cloud_runner.py -a 0.0.0.0:60050 -c $conf  > logs/cloud.log 2>&1 &
#python3 scripts/start_client_runner.sh
python3 src/clock_runner.py -s 0 -i 1  > logs/clock.log 2>&1 &
