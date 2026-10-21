#!/bin/bash
# Waits for all precompute shards, then regenerates Exp -1 with fixes, writes SUMMARY, commits and pushes.
cd "$(dirname "$(readlink -f "$0")")/.."
[ "$1" = "nowait" ] || while pgrep -f "src/precompute.py" >/dev/null; do sleep 60; done
echo "precompute finished $(date); tables: $(ls ${WORKDIR:-.}/data/p2_cache/tables | wc -l)"
PY=python
set -e
$PY -W ignore src/generate.py
$PY -W ignore src/export.py
$PY -W ignore src/verify.py
$PY src/stats.py
$PY src/make_summary.py
git add -A results src
git commit -qm "Exp -1 post-fix run on $(ls ${WORKDIR:-.}/data/p2_cache/tables | wc -l)/150 val logs: 1000 triplets, verify_100, user_sample, map-check agreement, SUMMARY"
git push -q
echo "STAGE2_DONE $(date)"
