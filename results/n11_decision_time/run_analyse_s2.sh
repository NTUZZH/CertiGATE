#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-9 python code/scripts/n11_decision_time.py analyse --reading primary > results/n11_decision_time/analyse_s2.log 2>&1
echo "analyse exit $?" >> results/n11_decision_time/analyse_s2_status.txt
