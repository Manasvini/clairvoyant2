
num_vms=$1
machine_prefix=$2
for ((i=1;i<=num_vms;i++)); do
  ssh ${cv}${i} bash <<EOF 
pid=\$(ps -ax | grep "python3 src/edge/content_server.py" | head -n 1 | awk '{print \$1}')
echo \$pid
kill \$pid
cd clairvoyant2
python3 src/edge/content_server.py > /tmp/cshttp.out 2>&1 &
EOF
  echo "started on cv2$i"
  done
