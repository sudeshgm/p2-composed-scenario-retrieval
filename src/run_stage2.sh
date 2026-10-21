#!/bin/bash
cd /workspace/p2-composed-scenario-retrieval
while pgrep -f precompute.py >/dev/null; do sleep 30; done
PY=/workspace/p2env/bin/python
$PY -W ignore src/generate.py && $PY -W ignore src/export.py && $PY -W ignore src/verify.py && echo STAGE2_DONE
