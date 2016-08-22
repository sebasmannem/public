#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options DB1 [DB2 ...]

  Dit script wordt gebruikt om een Oracle database aan te maken.

  OPTIONS:
     -h        toont dit helpscherm
     -home     De database home          (default Laatste dir in:  /u01/app/oracle/product/*/db*)
     -agsid    Voor oms integratie       (default geen)
     -template Keuze van template        (default standaard)
     -dg       Maak een database         (default uit)
               voorbereid voor Dataguard.
               LET OP. Draai daarna SBB_SetupDataguard.sh voor de 
               nieuw aangemaakte database en daarna pas aan de secondary zijde.
     -m        de waarde van de MEMORY_TARGET. indien niet ingesteld wordt deze uit de template gehaald (in bytes, of met eenheid [BKMG]).

     -x        debug mode                (default uit)
  Overige opties zijn database namen.

  Voorbeeld 1: Aanmaken standaard dataguard database
    $0 -dg D999P
  Voorbeeld 2: Aanmaken dataguard database dmv template DECOS
    $0 -dg -template DECOS D998P
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
  -m) MEM_TARGET=$2 ; shift 2 ;;
  -x) set -vx ; DBG=1; shift 1 ;;
  -*) echo "error: no such option $1" ; exit 1 ;;
  *)  DBs="$DBs $1" ; shift 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

#Om ervoor te zorgen dat alle scripts uit dezelfdee repository worden gebruikt...
cd $(dirname $0)/..
[ -f ./bash/oralib ] || cd /stage/oracle/scripts/

[ "$logfile" ] || logfile=/tmp/$(basename $0 .sh).log
tmpfile=$(mktemp)
. bash/oralib > "$tmpfile"
cat "$tmpfile" | oraLogger
rm "$tmpfile"

DBs=$(echo "$DBs" | tr 'a-z' 'A-Z')
inValidDBs=$(echo $DBs | xargs -n1 | awk '$0!~/D[0-9][0-9][0-9][A-Z]/{print $0}')
[ "$inValidDBs" ] && quitOnError "There are invalid DB names specified: $inValidDBs"
if [ ! "$DBs" ]; then
  echo "Specificeer een of meerdere database namen."
  usage
fi

echo_head "Detecting ORACLE_HOME"
[ $ORACLE_HOME ] || ORACLE_HOME=$(ls -d /u01/app/oracle/product/*/db* | tail -n1)
[ -d $ORACLE_HOME ] || quitOnError "Couldn't detect ORACLE_HOME. Please set manualy and retry"
echo_success "$ORACLE_HOME"

echo_head "Checking home version"
HOME_VERSION=$(DBHomeVersion "$ORACLE_HOME")
[ $HOME_VERSION ] && echo_success "$HOME_VERSION" || quitOnError

echo_head "Checking for template"
[ $TEMPLATE ] || TEMPLATE=standaard
[ -f templates/$TEMPLATE.dbt ] || quitOnError "Could not find ${TEMPLATE}.dbt in $PWD/templates/"
TEMPLATE="$PWD/templates/$TEMPLATE.dbt"
echo_success "$TEMPLATE"

if [ ! $(echo $HOME_VERSION | grep -E '^10') ]; then
  echo_head "Checking for memory_target"
  #Template wordt geheel verwerkt (cat)
  #Alle spaties worden regeleindes (xargs)
  #Er wordt gefilterd op blokken beginnende met een regel met <InitParms> en eindigende met een regel met </InitParams> (sed)
  #En daarbinnen naar de regels beginnende met memory_target en eindigende met een regel met value= (ook nog de sed)
  #Daarna wordt de regel met value eruit gehaald en de tweede kolom (na de =) eruit gehaald, waarbij alleen getallen, letters en = geldige characters zijn (awk).
  if [ "$MEM_TARGET" ]; then
    MEM_TARGET=$(echo $MEM_TARGET | sed 's/[bB]//;s/[kK]/*2**10/;s/[mM]/*2**20/;s/[gG]/*2**30/')
  else
    MEM_TARGET=$(cat "$TEMPLATE" | xargs -n1 | sed -n '/<InitParams>/,/<\/InitParams>/{/memory_target/,/value=/{p}}' | awk 'BEGIN{FS="="}/value/{gsub(/[^a-zA-Z=0-9]/,"");print $2}')
  fi
  if [ "$MEM_TARGET" ]; then
    #omzetten in MB's
    MEM_TARGET=$(($MEM_TARGET/1024/1024))
    [ $MEM_TARGET -lt 512 ] && MEM_TARGET=512
    echo_success "$MEM_TARGET"
  else
    MEM_TARGET=1024
    echo_passed "Not detected. Using ${MEM_TARGET}M."
  fi
fi

echo_head "Setting gapw binary"
[ -x "$GAPW" ] || GAPW=/usr/local/bin/gapw
[ -x "$GAPW" ] || quitOnError "Please set GAPW to location of gapw binary and try again."
echo_success "$GAPW"

echo_head "Checking agent"
if [ $AG_SID ]; then
  export AG_HOME=`awk 'BEGIN{FS=":"}/^#/{$0=""}$1~/^'$AG_SID'$/{print $2}' /etc/oratab | head -n1`
  [ ! $AG_HOME ]
  quitOnError "Couldn't detect agent home. Wrong AG_SID ($AG_SID) specified."
  echo_success "$AG_SID:$AG_HOME"
else
  echo_passed
fi

FQDN=$(hostname -f)
DOMAIN=$(hostname -d)
TNSEDIT=$(dirname $(dirname $0))/python/tnsedit.py
[ -x "$TNSEDIT" ] || TNSEDIT=/stage/oracle/scripts/python/tnsedit.py
tnsfile=$TNS_ADMIN/tnsnames.ora

[ "$SYS_PW" ] || SYS_PW=`randpass 18`
[ "$DBSNMP_PW" ] || DBSNMP_PW=$SYS_PW
[ "$RMAN_DBA_PW" ] || RMAN_DBA_PW=$(randpass 10)
#ORADBA wordt uit gapw gelezen en/of erin gezet. Is DB afhankelijk...
#[ "$ORADBA_PW" ] || ORADBA_PW=$(randpass 10)
[ "$ORABEH_PW" ] || ORABEH_PW=$(randpass 10)

for DB in $DBs
  do
  echo_head "Creating $DB"

  #Met 10g dbca moet de data en fra folder voor de database bestaan. Beter aanmaken.
  mkdir -p {/u02/oradata,/u03/fra}/${DB}${DG}


  if [ $(echo $HOME_VERSION | grep -E '^10') ]; then
    $ORACLE_HOME/bin/dbca -silent -createDatabase -templateName $TEMPLATE -gdbname "$DB.$DOMAIN" -sid $DB -responseFile NO_VALUE -emConfiguration CENTRAL  -sysPassword $SYS_PW -systemPassword $SYS_PW -dbsnmpPassword $DBSNMP_PW -sysmanPassword $SYS_PW $([ $AG_HOME ] && echo "-centralAgent $AG_HOME") -datafileDestination /u02/oradata -recoveryAreaDestination /u03/fra -initParams db_name=$DB,db_unique_name=${DB}${DG} | oraLogger
  elif [ $(echo $HOME_VERSION | grep -E '^11') ]; then
    $ORACLE_HOME/bin/dbca -silent -createDatabase -templateName $TEMPLATE -gdbname "$DB.$DOMAIN" -sid $DB -responseFile NO_VALUE -automaticMemoryManagement true -totalMemory $MEM_TARGET -emConfiguration CENTRAL  -sysPassword $SYS_PW -systemPassword $SYS_PW -dbsnmpPassword $DBSNMP_PW -sysmanPassword $SYS_PW $([ $AG_HOME ] && echo "-centralAgent $AG_HOME") -datafileDestination /u02/oradata -recoveryAreaDestination /u03/fra -initParams db_name=$DB,db_unique_name=${DB}${DG} | oraLogger
  else
    $ORACLE_HOME/bin/dbca -silent -createDatabase -templateName $TEMPLATE -gdbname "$DB.$DOMAIN" -sid $DB -responseFile NO_VALUE -automaticMemoryManagement true -totalMemory $MEM_TARGET -sysPassword $SYS_PW -systemPassword $SYS_PW -datafileDestination /u02/oradata -recoveryAreaDestination /u03/fra -initParams db_name=$DB,db_unique_name=${DB}${DG} | oraLogger
  fi

  [ ${PIPESTATUS[0]} -eq 0 ] && { echo_success "SYS password: $SYS_PW"; } || quitOnError "Please check $logfile"

  echo_head "Creating new services if needed"; echo
  SERVICES=" $(run_sql $DB 'select NETWORK_NAME from v$services;' | xargs) "
  for svc in $( echo ${DB}${DG} $DB | sort -u)
  do
    echo_head "$svc"
    echo "$SERVICES" | grep -iq " $svc.$DOMAIN " && { echo_passed "Already existing" ; continue; }
    echo "exec dbms_service.create_service('$svc','$svc.$DOMAIN');
    exec dbms_service.start_service('$svc');" | run_sql $DB >/dev/null && echo_success || echo_failure
  done

  echo_head "Configuring TNS"
  echo "$DB =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = ${FQDN})(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = $DB.${DOMAIN})
    )
  )

  ${DB}_RMAN =
  (DESCRIPTION =
    (ADDRESS = (PROTOCOL = TCP)(HOST = ${FQDN})(PORT = 1521))
    (CONNECT_DATA =
      (SERVER = DEDICATED)
      (SERVICE_NAME = ${DB}${DG}.${DOMAIN})
    )
  )" | "$TNSEDIT" -o "$tnsfile" | oraLogger
  [ $? -eq 0 ] && echo_success || quitOnError "Could not change $tnsfile"

  echo_head "Setting remote_listener"
  run_sql $DB "alter system set remote_listener='REMOTE_LISTENERS';" 2>&1 > /dev/null && echo_success || quitOnError "Please check $logfile"

  if [ "$DOMAIN" = "domain.org" ]; then
    CATALOG_PW_GETPW=$(getpw rman rman_catalog)
    if [ ! "$CATALOG_PW_GETPW" ]; then
      echo "
[RMAN_CATALOG-DBA]
RMAN=pac1f1ca" >> /usr/local/bin/ini/gapw.ini
    fi
    echo_head "Coupling with catalog"
    run_rman $DB "REGISTER DATABASE;" && echo_success || echo_failure "Please check $logfile"
  fi

  echo_head "Registering database to catalog and Setting RMAN parameters"
  SS_FILE="/u01/app/oracle/admin/dbs/snapcf_$DB.f"
  mkdir -p $(dirname "$SS_FILE")

  run_rman $DB "CONFIGURE CONTROLFILE AUTOBACKUP FORMAT FOR DEVICE TYPE DISK TO '%F';
CONFIGURE DATAFILE BACKUP COPIES FOR DEVICE TYPE DISK TO 1;
CONFIGURE DEFAULT DEVICE TYPE TO 'SBT_TAPE';
CONFIGURE BACKUP OPTIMIZATION ON;
CONFIGURE CONTROLFILE AUTOBACKUP ON;
CONFIGURE CONTROLFILE AUTOBACKUP FORMAT FOR DEVICE TYPE 'SBT_TAPE' TO '%F';
CONFIGURE DEVICE TYPE DISK PARALLELISM 1 BACKUP TYPE TO COMPRESSED BACKUPSET;
CONFIGURE DEVICE TYPE 'SBT_TAPE' PARALLELISM 1 BACKUP TYPE TO BACKUPSET;
CONFIGURE DATAFILE BACKUP COPIES FOR DEVICE TYPE 'SBT_TAPE' TO 1;
CONFIGURE ARCHIVELOG BACKUP COPIES FOR DEVICE TYPE DISK TO 1;
CONFIGURE ARCHIVELOG BACKUP COPIES FOR DEVICE TYPE 'SBT_TAPE' TO 1;
CONFIGURE CHANNEL DEVICE TYPE 'SBT_TAPE' PARMS  'SBT_LIBRARY=/opt/simpana10/simpana2/Base/libobk.so,ENV=(CvInstanceName=Instance002,CVOraDBName=$DB)';
CONFIGURE MAXSETSIZE TO UNLIMITED;
CONFIGURE ENCRYPTION FOR DATABASE OFF;
CONFIGURE ENCRYPTION ALGORITHM 'AES128';
CONFIGURE ARCHIVELOG DELETION POLICY TO NONE;
CONFIGURE SNAPSHOT CONTROLFILE NAME TO '$SS_FILE';
CONFIGURE COMPRESSION ALGORITHM 'BASIC' AS OF RELEASE 'DEFAULT' OPTIMIZE FOR LOAD TRUE;
CONFIGURE RETENTION POLICY TO RECOVERY WINDOW OF 14 DAYS;" > /dev/null && echo_success || quitOnError "Please check $logfile"

  #$ORACLE_HOME/rdbms/admin/utlmail.sql en $ORACLE_HOME/rdbms/admin/prvtmail.plb zijn nodig voor GDU (UTL_MAIL).
  #$PWD/sql/Deploy/* bevat alle scripts die gedraaid moeten worden.
  for SCRIPT in $ORACLE_HOME/rdbms/admin/utlmail.sql $ORACLE_HOME/rdbms/admin/prvtmail.plb $PWD/sql/Deploy/*
  do
    echo_head "Applying $SCRIPT"
    run_sql $DB "@$SCRIPT;" > /dev/null && echo_success || echo_failure
  done

  ORADBA_PW_GETPW=$(getpw oradba ${DB})
  [ "$ORADBA_PW" ] || ORADBA_PW=$ORADBA_PW_GETPW
  [ "$ORADBA_PW" ] || ORADBA_PW=$(randpass 10)
  if [ "$ORADBA_PW" != "$ORADBA_PW_GETPW" ]; then
    echo_head "Registering oradba to gapw"
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
    getpw oradba ${DB} > /dev/null && echo_success || echo_failure
  fi

  echo_head "Changing passwords"

  export ORACLE_SID=$DB
  $ORACLE_HOME/bin/sqlplus / as sysdba <<EOF 2>&1 >/dev/null
     ALTER USER ORABEH IDENTIFIED BY ${ORABEH_PW} ACCOUNT UNLOCK;
     ALTER USER RMAN_DBA IDENTIFIED BY ${RMAN_DBA_PW} ACCOUNT UNLOCK;
EOF

  [ $? -eq 0 ] && echo_success || echo_failure

  if [ ! $(echo $HOME_VERSION | grep -E '^10') ]; then
    echo_head "Setting AMM"
    echo "alter system set memory_target=${MEM_TARGET}M scope=spfile;" | run_sql $DB > /dev/null && echo_success || echo_failure
    #Resetten als de parameters bestaan. Resultaat niet belangrijk...
    echo "alter system reset sga_target scope=spfile;
alter system reset pga_aggregate_target scope=spfile;" | run_sql $DB > /dev/null

    echo_head "Setting audit_file_dest"
    AUDIT_DEST=$ORACLE_BASE/diag/rdbms/$(echo "${DB}${DG}" | tr '[:upper:]' '[:lower:]' )/$DB/adump
    mkdir -p "$AUDIT_DEST"
    run_sql $DB "alter system set audit_file_dest='$AUDIT_DEST' scope=spfile;" > /dev/null && echo_success "$AUDIT_DEST" || echo_failure

    echo_head "Detecting FILESYSTEMIO_OPTION"
#  FS=$(df /u02/oradata | awk '{sub(/.* /,"",$0);print $0}' | tail -n1)
    FS_TYPE=$(mount | awk '$3~/^\/u02$/{print $5}')
    echo_success $FSTYPE
    if [ "$FS_TYPE" == 'ext4' ]; then
      echo_head "Setting FILESYSTEMIO_OPTIONS=SETALL"
       run_sql $DB 'alter system set FILESYSTEMIO_OPTIONS=SETALL scope=spfile;' > /dev/null && echo_success || echo_failure "Could not set FILESYSTEMIO_OPTIONS=SETALL"
    fi
    echo_head "Restarting database with new parameters"
    run_sql $DB "shutdown immediate;" > /dev/null 
    rm /u01/app/oracle/admin/dbs/init$DB.ora 
    run_sql $DB "startup;" > /dev/null && echo_success || echo_failure
  fi
  echo
  done
