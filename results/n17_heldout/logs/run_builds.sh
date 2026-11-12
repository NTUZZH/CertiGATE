#!/bin/bash
cd <project>
b() { OMP_NUM_THREADS=1 taskset -c $2 python3 code/scripts/n17_heldout.py build --seed $1 > results/n17_heldout/logs/build_$1.log 2>&1; echo "exit $?" >> results/n17_heldout/logs/build_$1.log; }
b 20261110 10 &
b 20261111 11 &
wait
b 20261112 10
echo "all builds done" > results/n17_heldout/logs/builds_done.txt
