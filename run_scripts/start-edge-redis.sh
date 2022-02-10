num_edge=$1
if [ -z $num_edge ]; then
  num_edge=10
fi

for ((i=1;i<=num_edge;i++)); do
  echo "start redis on cv2$i"
  ssh cv2$i "redis-server --daemonize yes"
done
