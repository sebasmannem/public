#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options

  Gebruik dit script om periodiek een aantal belangrijke database kenmerken voor alle draaiende databases op te slaan.

  OPTIONS:
     -h         toont dit helpscherm
     -DB        De SID van de Databases   (komma gescheiden, default alle draaiende instances)
     -o         Outputfile om de resultaten heen te schrijven.
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
  -o) export outputfile=$2 ; shift 2 ;;
  -x) set -vx ; shift 1 ;;
  *) echo "error: no such option $1" ; exit 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

[ "$outputfile" ] || export outputfile=/u01/app/oracle/logs/capacity_$(date +%Y%m%d).log

. /stage/oracle/scripts/bash/oralib > /dev/null
[ "$DBs" ] && DBs=$(echo "$DBs" | sed 's/,/ /') || DBs=$(running_instances|sort)
[ "$outputfile" ] || export outputfile=/u01/app/oracle/log/capacity_$(date +%Y%m%d).log
if [ ! -f "$outputfile" ]; then
  mkdir -p $(dirname "$outputfile")
  echo "#inst Date Time DB_UQ DB_Role DBTime MemTarget MemTargetAdvice MaxSize Size Used Redo FRA_Size FRA_Used Gap_Days Gap_Time StartTime" >> "$outputfile"
  echo >> "$outputfile"
fi

#v$osstat

QRY=@/stage/oracle/scripts/sql/capacity.sql
for inst in $DBs
  do
  echo "$QRY" | run_sql $inst | sed '/^$/d;/PL\/SQL/d;s/^/'$inst' /' | tee -a $outputfile
  done
