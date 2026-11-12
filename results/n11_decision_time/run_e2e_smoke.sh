#!/bin/bash
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-9 python code/scripts/n11_stage2.py e2e --readings primary --instances c10_replay_400_0002,c09_storm2_w80_u100_0005 > results/n11_decision_time/e2e_smoke.log 2>&1
echo "smoke exit $?" >> results/n11_decision_time/e2e_smoke_status.txt
