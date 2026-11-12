#!/bin/bash
cd <project>
OMP_NUM_THREADS=1 taskset -c 11 python3 code/scripts/n17_heldout.py build --check-published > results/n17_heldout/logs/build_check.log 2>&1
echo "exit $?" >> results/n17_heldout/logs/build_check.log
