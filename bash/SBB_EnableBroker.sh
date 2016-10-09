#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om Oracle Dataguard Broker te configureren.

  OPTIONS:
     -h        toont dit helpscherm

     -x        debug mode                (default uit)
  Overige opties zijn database namen.

  Voorbeeld 1: Configuratie broker D999P
    $0 D999P
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
  -x) set -vx ; DBG=1; shift 1 ;;
  -*) echo "error: no such option $1" ; exit 1 ;;
  *)  DBs="$DBs $1" ; shift 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

[ "$logfile" ] || logfile=/tmp/$(basename $0 .sh).log
tmpfile=$(mktemp)
. /stage/oracle/scripts/bash/oralib > "$tmpfile"
cat "$tmpfile" | oraLogger
rm "$tmpfile"

[ "$DBs" ] && DBs=$(echo "$DBs" | sed 's/,/ /g'|tr 'a-z' 'A-Z') || DBs=$(running_instances|sort|xargs)
#if [ ! $SYS_PW ]; then
#  echo_head "Please specify sys password:"
#  read -s SYS_PW
#  [ $SYS_PW ] && echo_success || quitOnError "No password specified"
#fi

for DB in $DBs
  do
  echo "Setting up broker for $DB" | oraLoggerWithOutput

  DG_UNIQUES=$(run_sql $DB 'select * from v$dataguard_config;')
  [ $(echo "$DG_UNIQUES" | wc -w) -gt 1 ] || { echo_failure 'Not a dataguard database.'; continue; }
  DG_CONFIG=$(run_sql $DB 'select database_role, db_unique_name from v$database;')
  DG_ROLE=$(run_sql $DB 'select database_role from v$database;')
  DB_UNIQUE_NAME=$(run_sql $DB 'select db_unique_name from v$database;')
  DB_BROKER_NAME="$(echo "$DB_UNIQUE_NAME" | tr '[:lower:]' '[:upper:]').$(hostname -d)"

  echo_head "Enabling Broker for $DB"
  run_sql $DB 'alter system set DG_BROKER_START=TRUE;' > /dev/null && echo_success || quitOnError 'Could not enable broker...'

  if [ "$DG_ROLE" = 'PRIMARY' ]; then
    echo_head "Creating configuration for $DB"
    run_dgmgrl $DB "CREATE CONFIGURATION $DB AS PRIMARY DATABASE IS $DB_UNIQUE_NAME CONNECT IDENTIFIER IS $DB_UNIQUE_NAME;" > /dev/null && echo_success || quitOnError 'Could create configuration...'

    echo_head "Enabling configuration for $DB"
    run_dgmgrl $DB "ENABLE CONFIGURATION;" > /dev/null && echo_success || quitOnError 'Could enable configuration...'

    for UNIQUE in $DG_UNIQUES
      do
        echo "$UNIQUE" | grep -qi "$DB_UNIQUE_NAME" && continue
        echo_head "Adding secondary database $UNIQUE"
        run_dgmgrl $DB "ADD DATABASE $UNIQUE AS CONNECT IDENTIFIER IS $UNIQUE;" > /dev/null && echo_success || echo_failure 'Could not add secondary database $UNIQUE...'
        echo_head "Enabling secondary database $UNIQUE"
        run_dgmgrl $DB "ENABLE DATABASE $UNIQUE;" > /dev/null && echo_success || echo_failure 'Could not enable secondary database $UNIQUE...'
      done

#  else
#    echo_head "Registering secondary database $DB"
#    run_dgmgrl $DB "ADD DATABASE $DB_UNIQUE_NAME AS CONNECT IDENTIFIER IS $DB_UNIQUE_NAME;" > /dev/null && echo_success || quitOnError 'Could add secondary database...'
  fi
  done
