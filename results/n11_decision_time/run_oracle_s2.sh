#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-11 python code/scripts/n11_decision_time.py oracle --phase relaxed --extra-inputs <project>/results/n11_e2e > results/n11_decision_time/oracle_s2.log 2>&1
echo "oracle exit $?" >> results/n11_decision_time/oracle_s2_status.txt
