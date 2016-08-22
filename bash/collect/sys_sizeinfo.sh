#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null

[ $CRS_HOME ] && name=`$CRS_HOME/bin/cemutlo -n` || name=`hostname`
DB=`running_instances`
if [ "$DB" ]; then
  for inst in $DB
  do
    db=${inst:0:5}
#    echo $db:total
    run_sql "$inst" "select t.tablespace_name, sum(t.bytes),sum(f.bytes) from (select file_id, sum(bytes) bytes from dba_free_space group by file_id) f inner join dba_data_files t on f.file_id = t.file_id where t.tablespace_name in('SYSTEM','SYSAUX') group by t.tablespace_name;" | awk '!/^$/{print "'$name'","'$db'",$1,$2,$3}'
#    echo $db:free
#    run_sql "$inst" 'select tablespace_name, sum(bytes) from dba_free_space where tablespace_name in('SYSTEM','SYSAUX') group by tablespace_name;'
#    sga=`run_sql "$inst" 'select sum(value)/1024/1024 "Megabytes" from v$sga;'`
#    pga=`run_sql "$inst" 'select value/1024/1024 Megabytes from v$pgastat where name = '"'aggregate PGA target parameter';"`
#    echo "$name $db $total $(($total-$free)) $sga $pga"
  done
else
  echo $name NO_DBs
fi
