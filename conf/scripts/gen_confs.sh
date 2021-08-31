#!/usr/bin/env bash

#How to use?
# bash gen_confs.sh <NUM_CONFS> <TEMPLATE>
# e.g. bash scripts/gen_confs.sh 5 edgeConfig.json
# For changes to conf, please change in conf_generator.py

# Please specify number of vms as argument
num_vms=$1

# Please specify template file
template=$2

cur_dir=$(basename $PWD)
if [ ${cur_dir} == "scripts" ]; then
  echo "Please run script from Parent"
  exit 1;
fi

mkdir -p gen_conf
gen_path=$(realpath gen_conf)

if [ ! -f $HOME/.ssh/config ]; then
  cp scripts/sshconfig $HOME/.ssh/config
elif [ -z $(grep cv0 $HOME/.ssh/config) ]; then
  cat scripts/sshconfig >> $HOME/.ssh/config
fi


python3 scripts/conf_generator.py -n $num_vms -t $template -p ${gen_path}

for ((i=0; i<${num_vms}; i++)); do
  rsync -avz ${gen_path}/edgeConfig$i.json cv$((i+1)):~/clairvoyant2/conf/
done
