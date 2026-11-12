#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c 8-9 $PY code/scripts/n11_decision_time.py census --reading late > results/n11_forecast/logs/late_census.log 2>&1
echo "late census exit $? $(date -Iseconds)" >> results/n11_forecast/logs/status.txt
