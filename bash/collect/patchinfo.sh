#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null

echo "-------------------------------"
echo $(hostname)
`egrep "crs|grid" /etc/oratab| head -n 1| cut -d: -f2`/bin/cemutlo -n
echo "HOSTYPE=$HOSTTYPE"

DBs=$(running_instances)
if [ "$DBs" ]; then
  for inst in $DBs
  do
    cat /etc/oratab | grep $inst
    run_sql "$inst" "@/stage/oracle/scripts/junk/patchinfo.sql"
  done
else
  echo -n $(hostname)
  echo ":NO_DB"
fi

cd /u04/oracle
df -h |grep u04
