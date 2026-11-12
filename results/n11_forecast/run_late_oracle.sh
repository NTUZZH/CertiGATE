#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c 8-11 $PY code/scripts/n11_decision_time.py oracle --phase relaxed --cores 8-11 --workers 4 --extra-inputs <project>/results/n11_decision_time/late,<project>/results/n11_forecast/late_e2e > results/n11_forecast/logs/late_oracle.log 2>&1
echo "late oracle exit $? $(date -Iseconds)" >> results/n11_forecast/logs/status.txt
