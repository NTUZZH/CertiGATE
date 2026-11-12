#!/bin/bash
cd <project>
until [ -f results/n17_heldout/logs/builds_done.txt ]; do sleep 10; done
for s in 20261110 20261111 20261112; do
  grep -q "^exit 0" results/n17_heldout/logs/build_$s.log || { echo "build $s failed" > results/n17_heldout/logs/replays_done.txt; exit 1; }
done
for s in 20261110 20261111 20261112; do
  results/n17_heldout/logs/run_replay.sh $s primary 10,11 2
done
results/n17_heldout/logs/run_replay.sh published issue_uniform 10,11 2
results/n17_heldout/logs/run_replay.sh published issue_mid 10,11 2
echo "replays done" > results/n17_heldout/logs/replays_done.txt
