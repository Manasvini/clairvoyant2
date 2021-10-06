num_edge=$1
if [ -z $num_edge ]; then
  num_edge=10
fi

for ((i=1;i<=num_edge;i++)); do
  ssh cv2$i bash <<EOF 
pid=\$(ps -ax | grep "python3 src/edge_runner.py" | head -n 1 | awk '{print \$1}')
echo \$pid
kill \$pid
EOF
  echo "Killed cv2$i"
  done
