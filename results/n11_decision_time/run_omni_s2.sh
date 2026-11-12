#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 N11_OMNI_REQUIRE_CACHE=1
taskset -c 8-9 python code/scripts/n11_decision_time.py omni > results/n11_decision_time/omni_s2.log 2>&1
echo "omni exit $?" >> results/n11_decision_time/omni_s2_status.txt
