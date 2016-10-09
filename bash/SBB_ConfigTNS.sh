#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om de TNS configuratie op een server juist in te stellen, als deze nog niet goed is ingesteld.

  OPTIONS:
     -h        toont dit helpscherm
     -home     De database home          (default Laatste dir in:  /u01/app/oracle/product/*/db*)

     -x        debug mode                (default uit)

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
  -x) set -vx ; DBG=1; shift 1 ;;
  -*) echo "error: no such option $1" ; exit 1 ;;
esac
done

export TNS_ADMIN=/u01/app/oracle/admin/network
[ "$logfile" ] || logfile=/tmp/$(basename $0 .sh).log
tmpfile=$(mktemp)
. /stage/oracle/scripts/bash/oralib > "$tmpfile"
cat "$tmpfile" | oraLogger
rm "$tmpfile"
tnsfile="$TNS_ADMIN/tnsnames.ora"
lsnfile="$TNS_ADMIN/listener.ora"
sqlnetfile="$TNS_ADMIN/sqlnet.ora"
dbsdir="/u01/app/oracle/admin/dbs"
HN=$(hostname | tr '[:lower:]' '[:upper:]')
FQDN=$(hostname -f)

echo_head "Detecting ORACLE_HOME"
[ $ORACLE_HOME ] || export ORACLE_HOME=$(ls -d /u01/app/oracle/product/*/db* | tail -n1)
[ -d $ORACLE_HOME ] || quitOnError "Couldn't detect ORACLE_HOME. Please set manualy and retry"
echo_success "$ORACLE_HOME"

#Check for valid tnsnames
echo_head "Creating symbolic links for tns, sqlnet and listener files."

mkdir -p "$TNS_ADMIN"
mkdir -p "$dbsdir"
touch "$tnsfile"
touch "$sqlnetfile"
touch "$lsnfile"

if [ ! -L $ORACLE_HOME/dbs ]; then
  [ -e $ORACLE_HOME/dbs ] && mv $ORACLE_HOME/dbs $ORACLE_HOME/dbs.old
  ln -s "$dbsdir" "$ORACLE_HOME/dbs"
  ln -sf "$tnsfile" "$ORACLE_HOME/network/admin"
  ln -sf "$lsnfile" "$ORACLE_HOME/network/admin"
  ln -sf "$sqlnetfile" "$ORACLE_HOME/network/admin"
fi
echo_success

[ -f /etc/profile.d/datacenter.sh ] && . /etc/profile.d/datacenter.sh #Work around, om DATACENTER variabele te laden als hij niet al is geladen...

echo_head "Checking for REMOTE_LISTENERS"
if $ORACLE_HOME/bin/tnsping REMOTE_LISTENERS > /dev/null; then
  echo_passed
else
  echo
  echo_head "Adding REMOTE_LISTENERS to tnsnames."
  MSG="tnsedit.py raised an error..."
  case "$DATACENTER" in
  "DC01")
    echo 'REMOTE_LISTENERS = (ADDRESS_LIST = (ADDRESS = (PROTOCOL = TCP)(HOST = srvp401.domain.org)(PORT = 1521)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  "DC02")
    if [ ${HN:3:1} = 'A' ]; then
      echo 'REMOTE_LISTENERS = (ADDRESS_LIST = (ADDRESS = (PROTOCOL = TCP)(HOST = srva401.domain.org)(PORT = 1521)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    else
      echo 'REMOTE_LISTENERS = (ADDRESS_LIST = (ADDRESS = (PROTOCOL = TCP)(HOST = srva401.domain.org)(PORT = 1521)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    fi
    ;;
  "DC04")
      echo 'REMOTE_LISTENERS = (ADDRESS_LIST = (ADDRESS = (PROTOCOL = TCP)(HOST = srvo401.domain.org)(PORT = 1521)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  # Voor DC04 is een aparte situatie van toepassing aangezien hier geen Connection Manager is.
  *)
      echo "REMOTE_LISTENERS = (ADDRESS_LIST = (ADDRESS = (PROTOCOL = TCP)(HOST = $FQDN)(PORT = 1521)))" | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  esac
  [ $? -eq 0 ] && echo_success || echo_failure "$MSG"
fi

echo_head "Checking for RMAN_CAT"
if $ORACLE_HOME/bin/tnsping RMAN_CAT > /dev/null; then
  echo_passed
else
  echo
  echo_head "Adding RMAN_CAT to tnsnames."
  MSG="tnsedit.py raised an error..."
  case "$DATACENTER" in
  "DC01")
    echo 'RMAN_CAT = (DESCRIPTION = (ADDRESS_LIST = (LOAD_BALANCE = OFF) (FAILOVER = ON) (ADDRESS = (PROTOCOL = TCP) (HOST = srvpdb01.domain.org) (PORT = 1521)) (ADDRESS = (PROTOCOL = TCP) (HOST = srvpdb02.domain.org) (PORT = 1521))) (CONNECT_DATA = (SERVICE_NAME = rmancatm.domain.org) (FAILOVER_MODE = (FAILOVER = ON) (TYPE = SELECT) (METHOD = BASIC) (RETRIES = 10) (DELAY = 10)) (SERVER = DEDICATED)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  "DC02")
    echo 'RMAN_CAT = (DESCRIPTION = (ADDRESS_LIST = (LOAD_BALANCE = OFF) (FAILOVER = ON) (ADDRESS = (PROTOCOL = TCP) (HOST = srvadb01.domain.org) (PORT = 1521)) (ADDRESS = (PROTOCOL = TCP) (HOST = srvadb02.domain.org) (PORT = 1521))) (CONNECT_DATA = (SERVICE_NAME = rmancatw.domain.org) (FAILOVER_MODE = (FAILOVER = ON) (TYPE = SELECT) (METHOD = BASIC) (RETRIES = 10) (DELAY = 10)) (SERVER = DEDICATED)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  "DC03")
    echo 'RMAN_CAT = (DESCRIPTION = (ADDRESS_LIST = (LOAD_BALANCE = OFF) (FAILOVER = ON) (ADDRESS = (PROTOCOL = TCP) (HOST = srvtdb01.domain.org) (PORT = 1521)) (ADDRESS = (PROTOCOL = TCP) (HOST = srvtdb01.domain.org) (PORT = 1521))) (CONNECT_DATA = (SERVICE_NAME = rmancatg.domain.org) (FAILOVER_MODE = (FAILOVER = ON) (TYPE = SELECT) (METHOD = BASIC) (RETRIES = 10) (DELAY = 10)) (SERVER = DEDICATED)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  # Voor DC04 is een aparte situatie van toepassing aangezien hier geen Connection Manager is.
  "DC04")
    echo 'RMAN_CAT = (DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = srvodb01.domain.org)(PORT = 1521))(CONNECT_DATA = (SERVER = DEDICATED)(SERVICE_NAME = rmancate.domain.org)))' | /stage/oracle/scripts/python/tnsedit.py -o "$tnsfile" | oraLogger
    ;;
  *)
    echo_passed "Unknown location '$DATACENTER'... not succesfully setup RMAN_CAT in $tnsfile."
    ;;
  esac
  [ $? -eq 0 ] && echo_success || echo_failure "$MSG"
fi

if [ $(grep -cE "^LISTENER_$HN" "$lsnfile") -eq 0 ]; then
    echo_head "Creating named listener"
    echo "LISTENER_$HN =" >> "$lsnfile"
    echo "  (DESCRIPTION_LIST =" >> "$lsnfile"
    echo "    (DESCRIPTION =" >> "$lsnfile"
    echo "      (ADDRESS = (PROTOCOL = TCP)(HOST = $FQDN)(PORT = 1521))" >> "$lsnfile"
    echo "    )" >> "$lsnfile"
    echo "  )" >> "$lsnfile"
    echo >> "$lsnfile"
    echo "ADR_BASE_LISTENER_$HN = /u01/app/oracle" >> "$lsnfile"
    echo >> "$lsnfile"
    echo "VALID_NODE_CHECKING_REGISTRATION_LISTENER_$HN=ON" >> "$lsnfile"
    echo >> "$lsnfile"
    echo_success
else
    #Check entry in existing listener.ora
    grep -iq "VALID_NODE_CHECKING_REGISTRATION" "$lsnfile" && sed -i "s|VALID_NODE_CHECKING_REGISTRATION.*|VALID_NODE_CHECKING_REGISTRATION_LISTENER_$HN = ON|" $lsnfile || echo -e "\nVALID_NODE_CHECKING_REGISTRATION_LISTENER_$HN = ON" >> $lsnfile
fi

#Check for valid sqlnet
grep -iq "DIAG_ADR_ENABLED=" "$sqlnetfile" && sed -i 's/DIAG_ADR_ENABLED=.*/DIAG_ADR_ENABLED=ON/I' $sqlnetfile || echo "DIAG_ADR_ENABLED=ON" >> $sqlnetfile
grep -iq "ADR_BASE=" "$sqlnetfile" && sed -i 's|ADR_BASE=.*|ADR_BASE=/u01/app/oracle|I' $sqlnetfile || echo "ADR_BASE=/u01/app/oracle" >> $sqlnetfile
grep -iq "KEEPALIVE=" "$sqlnetfile" && sed -i 's|KEEPALIVE=.*|KEEPALIVE=10|I' $sqlnetfile || echo "KEEPALIVE=10" >> $sqlnetfile


