num_edge=$1
machine_pfx=cv2

for ((i=0; i<num_edge; i++))
do
  id=$((i+1))
  ssh ${machine_pfx}$id bash << EOF
pkill edge_go
EOF
done
