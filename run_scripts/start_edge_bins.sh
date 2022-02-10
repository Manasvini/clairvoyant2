num_edge=$1
machine_pfx=cv2

build_and_copy=1

if [ $build_and_copy -eq 1 ]; then
  echo "build edge once"
  cd ~/clairvoyant2/src/edge_go
  go build
fi

echo "copy edge binary"
for ((i=0; i<num_edge; i++))
do
  id=$((i+1))
  if [ $build_and_copy -eq 1 ]; then
    rsync edge_go ${machine_pfx}$id:~/clairvoyant2/src/edge_go/
  fi
  ssh ${machine_pfx}$id bash << EOF
cd clairvoyant2/src/edge_go/
./edge_go --config ../../conf/edgeConfig$i.json > ../../logs.edge.out 2>&1 &
EOF
done
