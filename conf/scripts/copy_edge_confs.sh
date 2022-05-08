#!/usr/bin/env bash

#How to use?
# bash gen_confs.sh <NUM_CONFS> <TEMPLATE>
# e.g. bash scripts/gen_confs.sh 5 edgeConfig.json
# For changes to conf, please change in conf_generator.py

# Please specify number of vms as argument
num_vms=$1
if [ -z $num_vms ]; then
  num_vms=1
fi

# Please specify if your macine prefix for ssh is different (cv1 or cv2)
prefix=$2
if [ -z $prefix ]; then
  prefix=cv2
fi

echo "No. of VMs=$num_vms, machine prefix=$prefix"

cur_dir=$(basename $PWD)
if [ ${cur_dir} != "scripts" ]; then
  echo "Please run script from scripts Directory"
  exit 1;
fi

gen_path=$(realpath gen_confs)

for ((i=0; i<${num_vms}; i++)); do
  rsync -avz ${gen_path}/edgeConfig$i.json cv2$((i+1)):~/clairvoyant2/conf/
done
