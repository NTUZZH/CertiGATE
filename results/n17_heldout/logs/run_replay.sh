#!/bin/bash
# usage: run_replay.sh <suite> <reading> <cores> <workers>
cd <project>
LOG=results/n17_heldout/logs/replay_$1_$2.log
OMP_NUM_THREADS=1 taskset -c 8-11 python3 code/scripts/n17_heldout.py replay --suite $1 --reading $2 --cores $3 --workers $4 >> $LOG 2>&1
echo "exit $?" >> $LOG
