num_edge=$1
machine_prefix=$2
if [ -z $num_edge ]; then
  num_edge=10
fi

for ((i=1;i<=num_edge;i++)); do
  ssh ${machine_prefix}${i} bash <<EOF 
pid=\$(lsof -t -i:50056 | head -n 1 | awk '{print \$1}')
echo \$pid
kill  \$pid
EOF
  echo "Killed ${machine_prefix}$i"
  done
