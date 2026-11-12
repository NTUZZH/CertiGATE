#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-9 python code/scripts/n11_stage2.py analyse2 > results/n11_decision_time/analyse2.log 2>&1
echo "analyse2 exit $?" >> results/n11_decision_time/analyse2_status.txt
