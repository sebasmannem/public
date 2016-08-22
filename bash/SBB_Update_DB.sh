#!/bin/bash
for SID in $(ps -ef | awk '$8~/^ora_pmon_/{sub(/^ora_pmon_/,"",$8);print $8}')
do
  export ORACLE_SID=$SID
  export ORACLE_HOME=$(awk 'BEGIN{FS=":"}{sub(/#.*/,"")}$1~/^'$SID'$/{print $2}' /etc/oratab)

  for script in /stage/oracle/scripts/sql/Deploy/*
  do
    sqlplus -s / as sysdba <<EOF 
@$script;
EOF
  done
done
