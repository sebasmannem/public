#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om alle primary dataguard databases op de server over te switchen naar een andere secondary.

  OPTIONS:
     -h        toont dit helpscherm
     -s        Stel het wachtwoord in. Stel liever environment variabele SYS_PW in (' export SYS_PW-...')
     -p        Parallel modus. Alle databases worden tegelijk geswitcht. 

     -x        debug mode                (default uit)
  Overige opties zijn database namen.

  Voorbeeld 1: Configuratie broker D999P
    $0 D999P
EOF
  exit 0
}

function switchover()
{
  echo_head "Checking if $DB is a primary dataguard database"
  DG_UNIQUES=$(run_sql $DB 'select * from v$dataguard_config;')
  [ $(echo "$DG_UNIQUES" | wc -w) -gt 1 ] || { echo_passed 'Not a dataguard database.'; continue; }
  DG_CONFIG=$(run_sql $DB 'select database_role, db_unique_name from v$database;')
  DG_ROLE=$(run_sql $DB 'select database_role from v$database;')
  DB_UNIQUE_NAME=$(run_sql $DB 'select db_unique_name from v$database;')
  DB_BROKER_NAME="$(echo "$DB_UNIQUE_NAME" | tr '[:lower:]' '[:upper:]').$(hostname -d)"
  [ "$DG_ROLE" = "PRIMARY" ] && echo_success || { echo_passed 'Not a primary database.'; continue; }

  unset NEW_TARGET
  echo_head "Selecting New target"
  for TARGET in $(run_dgmgrl $DB 'show configuration;' | awk '/Physical standby database/{print $1}');
  do
   TARGET_STATUS=$(run_dgmgrl $DB 'show database '$TARGET';' | sed -n '/Database Status:/,$p' | sed -n '2p')
   if [ "$TARGET_STATUS" = "SUCCESS" ]; then
     NEW_TARGET=$TARGET
   fi
  done

  [ "$NEW_TARGET" ] && echo_success "Using $NEW_TARGET as new target for primary database." || { echo_failure 'No avalailable target found...' ; continue; }
  echo_head "Switching to $NEW_TARGET"
  run_dgmgrl $DB "SWITCHOVER TO $NEW_TARGET;" | oraLogger

  DG_ROLE=$(run_sql $DB 'select database_role from v$database;')
  if [ "$DG_ROLE" = 'PRIMARY' ]; then
    echo_failure "Could not switch to $NEW_TARGET"
    continue
  fi
  run_sql $DB "startup mount force;" | oraLogger
  echo_success "$DB"
  echo
} ###END-OF-function switchover 


### MAIN ###


if [ $(whoami) != 'oracle' ]; then
  sudo -Eu oracle "$0" $@
  exit
fi

while [ -n "$1" ]; do
case $1 in
  -h) usage; exit 0 ;;
  -s) SYS_PW=$2; shift 2;;
  -p) PARALLEL=TRUE; shift 1;;
  -x) set -vx ; DBG=1; shift 1 ;;
  -*) echo "error: no such option $1" ; exit 1 ;;
  *)  DBs="$DBs $1" ; shift 1 ;;
esac
done

if [[ ! $SYS_PW ]]; then
  echo "Stel het wachtwoord in. Stel liever environment variabele SYS_PW in (' export SYS_PW-...') of optie -p gebruiken."
  exit 1
fi

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

[ "$logfile" ] || logfile=/tmp/$(basename $0 .sh).log
tmpfile=$(mktemp)
. /stage/oracle/scripts/bash/oralib > /dev/null 2>&1
cat "$tmpfile" | oraLogger
rm "$tmpfile"

[ "$DBs" ] && DBs=$(echo "$DBs" | sed 's/,/ /g'|tr 'a-z' 'A-Z') || DBs=$(running_instances|sort|xargs)

for DB in $DBs
 do
  if [ $PARALLEL ];
  then
    switchover &
    sleep 1
  else
    switchover
  fi
 done
wait

