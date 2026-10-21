#!/bin/bash
# waits for precompute shards, then runs the fixed stage 2 (generate -> export -> verify -> stats)
cd "$(dirname "$(readlink -f "$0")")/.."
[ "$1" = "nowait" ] || while pgrep -f precompute.py >/dev/null; do sleep 30; done
PY=python
$PY -W ignore src/generate.py && $PY -W ignore src/export.py && $PY -W ignore src/verify.py && $PY src/stats.py && echo STAGE2_DONE
