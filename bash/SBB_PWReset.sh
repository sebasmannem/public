#!/bin/bash
function ora_changepw()
{
  echo_head "Changing password voor $2"

  run_sql $1 "alter user $2 identified by $3;
             alter user $2 account unlock;" > /dev/null && echo_success || echo_failure
}

function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om een Oracle database aan te maken.

  OPTIONS:
     -h        toont dit helpscherm
     -x        debug mode                (default uit)
  Overige opties zijn database namen.

  Voorbeeld 1: Password reset van alle databases
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
  -home) export ORACLE_HOME=$2 ; shift 2 ;;
  -agsid) AG_SID=$2 ; shift 2 ;;
  -template) TEMPLATE=$2 ; shift 2;;
  -dg) DG=_1 ; shift 1;;
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

DBs=$(echo "$DBs" | tr 'a-z' 'A-Z')
[ "$DBs" ] || usage

echo_head "Setting gapw binary"
[ -x "$GAPW" ] || GAPW=/usr/local/bin/gapw
[ -x "$GAPW" ] || quitOnError "Please set GAPW to location of gapw binary and try again."
echo_success "$GAPW"

unset failures
[ "$ORADBA_PW" ] || { echo_head 'Checking $ORADBA_PW'; echo_failure "No password for ORADBA was specifed. Please set ORADBA_PW to the right password."; }
[ "$RMAN_DBA_PW" ] || { echo_head 'Checking $RMAN_DBA_PW'; echo_failure "No password for RMAN_DBA was specifed. Please set RMAN_DBA_PW to the right password."; }
[ "$DBSNMP_PW" ] || { echo_head 'Checking $DBSNMP_PW'; echo_failure "No password for DBSNMP was specifed. Please set DBSNMP_PW to the right password."; }
[ "$failures" ] && { echo_head "Checking for Passwords"; quitOnError "Not alle passwords are set correctly."; }

for DB in $DBs
  do
  echo "Processing $DB" | oraLoggerWithOutput
  LOGCH="$(basename $0 .sh) $DB"
  echo_head "Registering oradba to gapw"
  ORADBA_PW_GETPW=$(getpw oradba ${DB})
  if [ "$ORADBA_PW" != "$ORADBA_PW_GETPW" ]; then
    chmod +w /usr/local/bin/ini/gapw.ini
    if [ $(grep -c "\[${DB}-DBA]" /usr/local/bin/ini/gapw.ini) -eq 0 ]; then
      #Hoofdstuk toevoegen
      echo "[${DB}-DBA]" >> /usr/local/bin/ini/gapw.ini
      echo "ORADBA=${ORADBA_PW}" >> /usr/local/bin/ini/gapw.ini
      echo >> /usr/local/bin/ini/gapw.ini
    elif [ $(sed -n "/\[${DB}-DBA\]/I,/\[/p" /usr/local/bin/ini/gapw.ini | grep -ic oradba) -eq 0 ]; then
      #oradba toevoegen
      sed -i "/\[${DB}-DBA\]/IaORADBA=${ORADBA_PW}" /usr/local/bin/ini/gapw.ini
    else
      #oradba aanpassen
      sed -i "/\[${DB}-DBA\]/I,/\[/{s/ORADBA=.*/ORADBA=${ORADBA_PW}/I}" /usr/local/bin/ini/gapw.ini
    fi
    chmod -w /usr/local/bin/ini/gapw.ini
  fi

  getpw oradba ${DB} > /dev/null && echo_success || quitOnError "Could not set ORADBA password to gapw.ini"

  [ "$DBG" ] || DONTLOG=1
  ora_changepw ${DB} ORADBA "$ORADBA_PW"
  ora_changepw ${DB} RMAN_DBA "$RMAN_DBA_PW"
  ora_changepw ${DB} DBSNMP "$DBSNMP_PW"
  unset DONTLOG
  done
