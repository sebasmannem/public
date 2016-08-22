#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options

  Gebruik dit script om de dataguard gap van een database te fixen.

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

for inst in $DBs
  do
  echo_head "Checking for need"
  RESTORE_CMD=$(run_sql $inst "SELECT 'restore archivelog sequence between '||LOW_SEQUENCE#||' and '||HIGH_SEQUENCE#||' device type sbt_tape;' FROM V\$ARCHIVE_GAP;")
  if [ $(echo "$RESTORE_CMD" | grep -Ec 'restore archivelog sequence between [0-9]+ and [0-9]+ device type sbt_tape;') -gt 0 ]; then
    echo_success
    echo_head "Fixing as needed"
    run_rman $inst "$RESTORE_CMD" > /dev/null && echo_success || echo_failure
  else
    echo_passed "No need (nothing in  V\$ARCHIVE_GAP)"
  fi
  done
