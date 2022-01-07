num_vms=$1
machine_prefix=$2
for ((i=1;i<=num_vms;i++)); do
  ssh ${machine_prefix}${i} "redis-cli flushdb"
done
