#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options

  Gebruik dit script om de dataguard status uit te lezen. Het script geeft een overzicht van de status van een aantal DG onderdelen.

  OPTIONS:
     -h         toont dit helpscherm
     -DB        De SID van de Databases   (komma gescheiden, default alle draaiende instances)
     -x         debug mode                (default uit)

     Overige opties zijn niet toegestaan
EOF
  exit 0

}

if [ $(whoami) != 'oracle' ]; then
  sudo -u oracle "$0" $@
  exit
fi

while [ -n "$1" ]; do
case $1 in
  -h) usage; exit 0 ;;
  -DB) export DBs=$2 ; shift 2 ;;
  -x) set -vx ; shift 1 ;;
  *) echo "error: no such option $1" ; exit 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

. /stage/oracle/scripts/bash/oralib > /dev/null

[ "$DBs" ] && DBs=$(echo "$DBs" | sed 's/,/ /') || DBs=$(running_instances|sort)
ERRS=0

for inst in $DBs
  do
  echo "------------------------------------------------"
  inst_host="$inst on "$(hostname)
  echo -n "| $inst_host"
  for ((i=${#inst_host};i<45;i++))
    do
    echo -n " "
    done
  echo "|"
  echo "------------------------------------------------"
  echo "select 'DB_UNIQUE_NAME:'||'|'||DB_UNIQUE_NAME from V\$DATABASE;
select 'ROLE:'||'|'||DATABASE_ROLE from V\$DATABASE;
select 'OPEN_MODE:'||'|'||OPEN_MODE from V\$DATABASE;
select 'SO_STATUS:'||'|'||SWITCHOVER_STATUS from V\$DATABASE;
  select 'DEST '||TO_CHAR(D.DEST_ID)||'|'||D.STATUS||'|'||DS.GAP_STATUS
  from V\$ARCHIVE_DEST D INNER JOIN V\$ARCHIVE_DEST_STATUS DS
  ON D.DEST_ID = DS.DEST_ID
  where D.DEST_ID in (2,3);
  select NAME||':'||'|'||VALUE from  V\$DATAGUARD_STATS;" | run_sql $inst | awk 'BEGIN{FS="|"}!/^$/{printf("|%-25s|%-20s|\n",$1,$2)}'
  setoraenv $inst >/dev/null
  dgmgrl /  "show configuration" |grep -q SUCCESS;
  if [[ $? == 0 ]]; then
    echo "dgmgrl show configuration|SUCCESS $ORACLE_SID"| awk '{printf("|%-46s|\n",$0)}' 
  else
    dgmgrl /  "show configuration" |sed -n 's/Configuration -/dgmgrl show configuration|Error ->/;/dgmgrl show configuration/,$p' | awk '!/^$/{printf("|%-46s|\n",$0)}' || awk '{print $0}'
  fi
  echo "------------------------------------------------"

  SOS=$(run_sql $inst 'select DATABASE_ROLE, SWITCHOVER_STATUS from V$DATABASE;')
  echo "$SOS" | grep -Eiq "(PRIMARY.*(SESSIONS ACTIVE|TO STANDBY)|STANDBY.*(RECOVERY NEEDED|NOT ALLOWED))" || ERRS=1
  echo
  done

exit $ERRS
