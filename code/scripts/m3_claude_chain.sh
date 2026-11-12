#!/usr/bin/env bash
# design M3 (2026-11-11): one Claude configuration, in sequence:
#   1. the five-prompt probe (known-board prompts, 2 repeats; must pass: every answer
#      parses, validates against the frozen schema and reports the pinned model id),
#   2. the same-day whole-window control (the frozen 200 items, 1 repeat),
#   3. the full known-board run (1,723 items, 2 repeats).
# Restartable: run the same command again. Logged keys are never re-sent and keys that
# end in an API error are retried. A stage whose keys still end in an API error (runner
# exit 5) is retried up to four times, one minute apart. Any other non-zero exit stops the
# chain: 2 refused to start, 3 model-id mismatch, 4 probe failed, 130 interrupted.
#
# Usage (from anywhere):
#   code/scripts/m3_claude_chain.sh sonnet|opus_default|opus_disabled
set -u
cd "$(dirname "$0")/../.." || exit 2
PY="${PYTHON:-python}"
CFG="${1:-}"
case "$CFG" in
  sonnet)        ARGS=(--hosted sonnet) ;;
  opus_default)  ARGS=(--hosted opus --thinking default) ;;
  opus_disabled) ARGS=(--hosted opus --thinking disabled) ;;
  *) echo "usage: $0 sonnet|opus_default|opus_disabled"; exit 2 ;;
esac

run() {
  OMP_NUM_THREADS=1 taskset -c 15 "$PY" -u code/scripts/grid_e1_known.py "${ARGS[@]}" \
      --i-have-approval-to-spend "$@"
}

stage() {
  local name=$1; shift
  local attempt rc
  for attempt in 1 2 3 4; do
    echo "== $(date '+%F %T') $CFG: $name, attempt $attempt"
    run "$@"; rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "== $(date '+%F %T') $CFG: $name complete"
      return 0
    fi
    if [ "$rc" -ne 5 ]; then
      echo "== $(date '+%F %T') $CFG: $name stopped with exit $rc"
      exit "$rc"
    fi
    sleep 60
  done
  echo "== $(date '+%F %T') $CFG: $name still has API-error keys after 4 attempts"
  exit 5
}

stage probe --limit 5
stage control --control
stage known-board
echo "== $(date '+%F %T') $CFG: DONE"
