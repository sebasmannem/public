#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null 2>&1
for i in $(running_instances)
do 
  run_sql $i 'select * from v$dataguard_config;' | while read d
  do 
    [ "$d" ] && run_dgmgrl $i "edit database $d set property LogArchiveMaxProcesses=5;"
  done
done
