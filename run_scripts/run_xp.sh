cd ~

rm -rf all_logs/
rm -rf results_dir/
rm out.txt
rm out_err.txt

echo "deleted logs"

cd ~/clairvoyant2
bash run_scripts/clean_logs.sh
bash run_scripts/sync_with_vm.sh 10 cv
python3 run_scripts/run_eval.py $1 ../results_dir >> ../out.txt 2>> ../out_err.txt

echo "getting logs"

cd ~
bash clairvoyant2/run_scripts/get_logs.sh
