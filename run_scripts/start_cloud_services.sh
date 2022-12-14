#!/bin/bash
num_nodes=$1
conf=$2
node_pos=$3
num_videos=$4
segments_file=$5
purge_redis=$6

echo "starting cloud services..."
echo "options:"
echo "    num_nodes=$1"
echo "    conf=$2"
echo "    node_pos=$3"
echo "    num_videos=$4"
echo "    segments_file=$5"
echo "    purge_redis=$6"

cd
cd clairvoyantedge-metadata
curdir=$(pwd)

if [ $purge_redis = "yes" ]; then
	pkill redis
	rm -rf cluster/*
	sleep 10
    bash scripts/start_redis_cluster.sh 3
    rm logs/*
	sleep 15

	cd $curdir
	pkill clairvoyant
	sleep 5
	bash scripts/start_meta_svr.sh > ./logs/meta_svr.out 2>&1 &

	echo "adding nodes"
	cd ~/clairvoyant2

  ## Old
	#python3 eval/add_nodes.py -n $num_nodes -p "192.168.160." -s 22 -i 0 -f $node_pos
  ## New: use ipinfo file
  python3 eval/scripts/add_nodes.py -n $num_nodes\
                                    -f $node_pos\
                                    --ipinfo conf/ipinfo.csv

	cd $curdir
	cd scripts
	echo "num videos = " $num_videos " video file =  " $segments_file
	bash ./video_creator.sh ../build/metadata/scripts/data-uploader $num_videos $segments_file
else
	pkill clairvoyant
	sleep 5
    rm logs/*
	bash scripts/start_meta_svr.sh > ./logs/meta_svr.out 2>&1 &
fi;

pkill python3
cd ~/clairvoyant2
mkdir -p logs


#TODO: change this ip to be configurable via command line, better still use conf file
rm src/clientrunner_go/clientrunner.*
rm -rf results/bench2/cloud/*
python3 src/cloud_runner.py -a 0.0.0.0:60050 -c $conf  > logs/cloud.log 2>&1 &
python3 src/clock_runner.py -s 0 -i 1 -c $conf  > logs/clock.log 2>&1 &
