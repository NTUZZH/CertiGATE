#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c 8-9 $PY code/scripts/n11_stage2.py e2e --readings primary,late --out-dir <project>/results/n11_forecast/late_e2e > results/n11_forecast/logs/late_e2e.log 2>&1
echo "late e2e exit $? $(date -Iseconds)" >> results/n11_forecast/logs/status.txt
