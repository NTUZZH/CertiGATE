#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
PY=python
taskset -c 8-11 $PY code/scripts/n11_forecast.py direct --cores 8-11 --workers 4 > results/n11_forecast/logs/direct.log 2>&1
echo "direct exit $? $(date -Iseconds)" >> results/n11_forecast/logs/status.txt
