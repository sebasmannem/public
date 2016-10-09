#!/bin/bash
function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om een Oracle database te verwijderen.

  OPTIONS:
     -h        toont dit helpscherm
     -x        debug mode                (default uit)

     Overige opties zijn database namen.
EOF
  exit 0
}

if [ $(whoami) != 'oracle' ]; then
  sudo -Eu oracle "$0" $@
  exit
fi

while [ -n "$1" ]; do
case $1 in
  -h) usage; exit 0 ;;
  -x) set -vx ; shift 1 ;;
  -*) echo "error: no such option $1" ; exit 1 ;;
  *)  DBs="$DBs $1" ; shift 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

logfile=/tmp/`basename $0 .sh`.log
touch $logfile 2>/dev/null
if [ ! -w "$logfile" ]; then
  echo "no write permissions to $logfile. logging to /dev/null"
  logfile=/dev/null
fi
. /stage/oracle/scripts/bash/oralib >> $logfile

DBs=$(echo "$DBs" | tr 'a-z' 'A-Z')
if [ ! "$DBs" ]; then
  echo "Specificeer een of meerdere database namen."
  usage
fi

for DB in $DBs
  do
  echo_head "Checking for running database $DB"
  ps -ef | grep -q [o]ra_pmon_${DB} && quitOnError "Database is still running. Please stop by hand first..." || echo_success

  echo_head "Cleaning /u01, /u02 and /u03 for database $DB"
  for d in /u01/app/oracle /u02/oradata /u03/fra
  do
    find "$d" -type f -iname '*'${DB}'*' -delete
    find "$d" -type d -iname '*'${DB}'*' | sort -r | while read d; do rm -r "$d"; done
  done
  echo_success

  echo_head "Cleaning oratab for database $DB"
  sed "/$DB/d" /etc/oratab > /tmp/tmp.oratab && cat /tmp/tmp.oratab > /etc/oratab
  [ $? -eq 0 ] && echo_success || echo_failure 

  echo_head "Cleaning tnsnames for database $DB"
  [ -f /u01/app/oracle/admin/network/tnsnames.$(date +%Y%m%d) ] || cp /u01/app/oracle/admin/network/tnsnames.ora /u01/app/oracle/admin/network/tnsnames.$(date +%Y%m%d)
  [ $? -eq 0 ] && sed -i '/'${DB}'/,/^$/d' /u01/app/oracle/admin/network/tnsnames.ora 
  [ $? -eq 0 ] && echo_success || echo_failure

  echo_head "Cleaning listener for database $DB"
  [ -f /u01/app/oracle/admin/network/listener.$(date +%Y%m%d) ] || cp /u01/app/oracle/admin/network/listener.ora /u01/app/oracle/admin/network/listener.$(date +%Y%m%d)
  [ $? -eq 0 ] && sed -i '/'${DB}'/d' /u01/app/oracle/admin/network/listener.ora
  [ $? -eq 0 ] && echo_success || echo_failure

  echo "Don't forget to remove from GC and CommVault..."
  done


