#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c 8-9 $PY code/scripts/n11_decision_time.py census --reading primary > results/n11_decision_time/census.log 2>&1
echo "primary exit $?" >> results/n11_decision_time/census_s2_status.txt
taskset -c 8-9 $PY code/scripts/n11_decision_time.py census --reading late > results/n11_decision_time/late/census.log 2>&1
echo "late exit $?" >> results/n11_decision_time/census_s2_status.txt
