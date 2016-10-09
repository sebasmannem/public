#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null

#OAS=$(awk 'BEGIN {IGNORECASE=1;FS=":"}{sub(/#.*/,"",$0)}$1~/(mt|im)/{sub("#.*","","$0");print $1}' /etc/oratab)
DBs=$(running_instances)
if [ "$DBs" ]; then
  for inst in $DBs
  do
    echo -n $(hostname)
    echo -n ":$inst:"
    run_sql "$inst" "select CS.VALUE||':'||NCCS.VALUE from nls_database_parameters CS inner join nls_database_parameters NCCS on CS.parameter = 'NLS_CHARACTERSET' and NCCS.parameter='NLS_NCHAR_CHARACTERSET';"| awk '!/$^/{print $0}'
  done
else
  echo -n $(hostname)
  echo ":NO_DB"
fi

