#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c ${CORES:-8-11} $PY code/scripts/n11_forecast.py smoke --cores ${CORES:-8-11} --workers ${WORKERS:-4} > results/n11_forecast/logs/smoke.log 2>&1
echo "smoke exit $? $(date -Iseconds)" >> results/n11_forecast/logs/status.txt
