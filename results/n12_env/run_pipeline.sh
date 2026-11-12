#!/bin/bash
# N12 pipeline: every environment, stage after stage, on cores 8-11 (timed solves exclusive).
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
taskset -c 8-11 python code/scripts/n12_env_sensitivity.py pipeline --envs cal,win050,win150,crew075,crew125
echo "exit $?" > results/n12_env/pipeline_status.txt
