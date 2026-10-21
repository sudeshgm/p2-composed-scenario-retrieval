#!/bin/bash
# Every 30 min: import GPU Bot tables from branch gpu-run, back up tables to /home/box/p2_backup and branch tables-backup.
T=/workspace/data/p2_cache/tables; W=/home/box/p2_backup/wt; R=https://github.com/sudeshgm/p2-composed-scenario-retrieval
while true; do
  if [ ! -d $W/.git ]; then git clone -q $R $W && cd $W && (git checkout -q tables-backup 2>/dev/null || git checkout -q --orphan tables-backup && git rm -rqf . ); fi
  cd $W
  git fetch -q origin gpu-run 2>/dev/null && for f in $(git ls-tree --name-only FETCH_HEAD gpu_tables/ 2>/dev/null); do b=$(basename $f); if [ ! -e $T/$b ]; then git show FETCH_HEAD:$f > $T/$b.tmp && mv -n $T/$b.tmp $T/$b; fi; done
  mkdir -p tables; mkdir -p /home/box/p2_backup/tables; cp -n $T/*.pkl /home/box/p2_backup/tables/; cp -n $T/*.pkl tables/
  git add tables && git commit -qm "tables backup $(ls tables|wc -l)/150 $(date)" && git push -q origin tables-backup
  echo "sync $(date) tables=$(ls $T/*.pkl|wc -l)"
  sleep 1800
done
