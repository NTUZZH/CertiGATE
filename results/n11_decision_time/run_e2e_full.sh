#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-9 python code/scripts/n11_stage2.py e2e --readings primary > results/n11_decision_time/e2e_full.log 2>&1
echo "e2e exit $?" >> results/n11_decision_time/e2e_full_status.txt
