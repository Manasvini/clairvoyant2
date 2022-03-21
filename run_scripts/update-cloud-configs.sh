cloud_machine=$1
cloud_config=$2
clientrunner_config=$3
clientrunner_dir=$4
# update cloud config
scp conf/scripts/tmp/$cloud_config cvuser@$cloud_machine:~/clairvoyant2/conf/
# update client runner configs
scp src/clientrunner_go/input/$clientrunner_dir/tmp/$clientrunner_config cvuser@$cloud_machine:~/clairvoyant2/src/clientrunner_go/input/$clientrunner_dir/

