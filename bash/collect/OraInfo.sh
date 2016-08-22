#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null

OAS=$(awk 'BEGIN {IGNORECASE=1;FS=":"}{sub(/#.*/,"",$0)}$1~/(mt|im)/{sub("#.*","","$0");print $1}' /etc/oratab)
DBs=$(running_instances)
if [ "$OAS" -o "$DBs" ]; then
  for inst in $OAS
  do
    echo -n $(hostname)
    ORACLE_HOME=$(homeFromOratab "$inst")
    echo -n ":$inst:OAS:"
    $ORACLE_HOME/opmn/bin/opmnctl status | awk 'BEGIN{ORS=","}$7~/(Alive|Down)/&&$1~/(OC4J|OID)/{sub(/.*:/,"",$3);print $3}'
    echo
  done
  for inst in $DBs
  do
    echo -n $(hostname)
    echo -n ":$inst:DB:"
    run_sql "$inst" "select distinct OWNER from dba_objects where OWNER NOT LIKE '%SYS%' AND OWNER NOT IN ('PUBLIC','SCOTT','DBSNMP','XDB','SI_INFORMTN_SCHEMA', 'ORADBA','ORDDATA','ORDPLUGINS','OUTLN','ORACLE_OCM','GDU', 'ORASSO_PA','BAM','OCA','WK_TEST','DSGATEWAY','ORASSO_DS','OWF_MGR','INTERNET_APPSERVER_REGISTRY','DCM','WIRELESS','ORASSO_PS','ODS');" | awk 'BEGIN{ORS=","}/rows selected/{$0=""}!/^$/{print $0}'
    echo
  done
else
  echo -n $(hostname)
  echo ":NO_OAS/DB"
fi

