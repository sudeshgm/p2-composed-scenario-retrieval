#!/bin/bash
# waits for precompute shards, then runs the fixed stage 2 (generate -> export -> verify -> stats)
cd /workspace/p2-composed-scenario-retrieval
[ "$1" = "nowait" ] || while pgrep -f precompute.py >/dev/null; do sleep 30; done
PY=/workspace/p2env/bin/python
$PY -W ignore src/generate.py && $PY -W ignore src/export.py && $PY -W ignore src/verify.py && $PY src/stats.py && echo STAGE2_DONE
