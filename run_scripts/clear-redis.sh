num_vms=$1
for ((i=1;i<=num_vms;i++)); do
  ssh cv2$i "redis-cli flushdb"
done
