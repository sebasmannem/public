#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null

DBs=$(running_instances)
if [ "$DBs" ]; then
  for inst in $DBs
  do
    run_sql "$inst" "select owner, round(sum(bytes)/(1024*1024)) table_size_meg from dba_segments group by owner order by 1;" | awk '{print "'$(hostname)'","'$inst'",$0}'
  done
else
  echo -n $(hostname)
  echo ":DB"
fi

