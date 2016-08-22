#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null
mkdir -p /home/oracle/perf/

[ $CRS_HOME ] && name=`$CRS_HOME/bin/cemutlo -n` || name=`hostname`
DB=`running_instances`
if [ "$DB" ]; then
  for inst in $DB
  do 
    [ -f "/home/oracle/perf/${inst}_sysstat_ioworkload.csv" ] || run_sql "$inst" '@/tmp/awr_info.sql;' > /dev/null
    sed 's/ *$//' /home/oracle/perf/${inst}_sysstat_ioworkload.csv
  done
else
  echo $name NO_DBs
fi

