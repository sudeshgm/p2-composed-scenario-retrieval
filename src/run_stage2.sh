#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")/.."
while pgrep -f precompute.py >/dev/null; do sleep 30; done
PY=python
$PY -W ignore src/generate.py && $PY -W ignore src/export.py && $PY -W ignore src/verify.py && echo STAGE2_DONE
