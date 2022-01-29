num_vms=$1
machine_prefix=$2
if [ -z $num_vms ]; then
  num_vms=10
fi

for ((i=0;i<=num_vms;i++)); do
  #rsync -avz --exclude ".git" --exclude "*.sw*" \
  #      --exclude="conf" \
  #      $HOME/clairvoyant2 cv2$i:~/

  rsync -avz --exclude ".git" \
             --exclude "*.sw*" \
             --exclude="/clairvoyant2/conf" \
             --exclude="*pycache*"\
             --exclude="results"\
             --exclude="localenv"\
        $HOME/clairvoyant2 ${machine_prefix}${i}:~/
done

#echo "restart content-servers"
#bash $HOME/clairvoyant2/run_scripts/start-content-svr.sh $num_vms
#
#echo "clear redis"
#bash $HOME/clairvoyant2/run_scripts/clear-redis.sh $num_vms

