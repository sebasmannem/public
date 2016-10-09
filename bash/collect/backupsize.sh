#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null
export NLS_DATE_FORMAT="dd-mm-yyyy hh24:mi:ss"

DBs=$(running_instances)
if [ "$DBs" ]; then
  for inst in $DBs
  do
    run_sql "$inst" "select to_char(ctime, 'YYYY-MM-DD') Datum, decode(backup_type, 'L', 'Archive Log', 'D', 'Full', 'Incremental') backup_type, bsize Size_MB
from (select trunc(bp.completion_time) ctime, backup_type, round(sum(bp.bytes/1024/1024),2) bsize
  from v\$backup_set bs, v\$backup_piece bp   
  where bs.set_stamp = bp.set_stamp   
  and bs.set_count  = bp.set_count   
  and bp.status = 'A'  
  group by trunc(bp.completion_time), backup_type)   
order by 1, 2;" | awk '{print "'$(hostname)'","'$inst'",$0}'
  done
else
  echo -n $(hostname)
  echo ":NO_DB"
fi

