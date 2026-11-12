#!/bin/bash
# N14 pipeline: census (deterministic) -> oracle (timed, cores 8-11 exclusive) -> analyse.
# Stages run one after another; a failed stage stops the pipeline.
cd <project>
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
PY=python
R=<project>/results/n14_altdispatch
ST=$R/pipeline_status.txt
mkdir -p $R/logs
for stage in census oracle analyse; do
  echo "$stage start $(date -Iseconds) load $(cut -d' ' -f1-3 /proc/loadavg)" >> $ST
  t0=$(date +%s)
  taskset -c 8-11 $PY code/scripts/n14_alt_dispatch.py $stage > $R/logs/$stage.log 2>&1
  rc=$?
  echo "$stage exit $rc $(date -Iseconds) wall $(( $(date +%s) - t0 ))s" >> $ST
  if [ $rc -ne 0 ]; then echo "pipeline FAILED at $stage" >> $ST; exit $rc; fi
done
echo "pipeline DONE $(date -Iseconds)" >> $ST
