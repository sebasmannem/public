#!/bin/bash
function addToString()
{
lead=$(echo "$1" | sed 's/[0-9]\+$//')
number=$(echo "$1" | sed 's/'$lead'//')
len=${#number}
number=$(($number + $2))
len2=${#number}
echo -n $lead
if [ $len -gt $len2 ]; then
  for ((i=$len;i<$len2;i++))
  do
    echo -n "0"
  done
fi
echo $number
}

function reconfigureDG()
{
unset failures
DB=$1
PW=$2
DOMAIN=$(hostname -d)

[ $3 ] && UNIQUE_P=${DB}$3 || UNIQUE_P=${DB}_1
[ $4 ] && UNIQUE_S=${DB}$4 || UNIQUE_S=${DB}_2

CUR_UNIQUE=$(run_sql $DB 'show parameter DB_UNIQUE_NAME' | awk '{print $3}')
if [ "$CUR_UNIQUE" = ${DB}_P ]; then
  FNC="'"$DB"_P','"$DB"_2'"
elif [ "$CUR_UNIQUE" = ${DB}_S ]; then
  FNC="'"$DB"_S','"$DB"_1'"
elif [ "$CUR_UNIQUE" = ${DB} ]; then
  FNC="'"$DB"','"$DB"_2'"
elif [ "$CUR_UNIQUE" = ${DB}_1 ]; then
  FNC="'"$DB"_1','"$DB"_2'"
elif [ "$CUR_UNIQUE" = ${DB}_2 ]; then
  FNC="'"$DB"_2','"$DB"_1'"
else
  FNC="'"$DB"_1','"$DB"_2'"
fi

#Zie http://docs.oracle.com/cd/B19306_01/server.102/b14239/rcmbackp.htm#CHDDDICH
#Voor OMF dus geen log_file_name_convert en db_file_name_convert gebruiken...
echo_head "Reconfiguring database parameters"
echo "alter system reset DB_FILE_NAME_CONVERT scope=spfile;
alter system reset LOG_FILE_NAME_CONVERT scope=spfile;" | run_sql $DB >/dev/null && echo_success || echo_failure

echo "alter system set fal_server='"$UNIQUE_S"' scope=spfile;
alter system set log_archive_config='DG_CONFIG=("$UNIQUE_P","$UNIQUE_S")' scope=spfile;
alter system set log_archive_dest_1='LOCATION=USE_DB_RECOVERY_FILE_DEST VALID_FOR=(ALL_LOGFILES, ALL_ROLES) DB_UNIQUE_NAME="$UNIQUE_P"' scope=spfile;
alter system set db_unique_name='"$UNIQUE_P"' scope=spfile;
alter database disable block change tracking;" | run_sql $DB >/dev/null && echo_success || echo_failure

echo_head "Creating new services if needed"; echo
SERVICES=$(run_sql $DB 'select NAME from v$services;')
for svc in $UNIQUE_P $DB $UNIQUE_S
do
  echo_head "$svc"
  echo "$SERVICES" | grep -q $svc && { echo_passed "Already existing" ; continue; }
  echo "exec dbms_service.create_service('$svc','$svc.$DOMAIN');
  exec dbms_service.start_service('$svc');" | run_sql $DB >/dev/null && echo_success || echo_failure
done

[ "$DBG" ] || DONTLOG=1
echo "alter user sys identified by $PW;
alter user sys account unlock;" | run_sql $DB >/dev/null && echo_success || echo_failure
unset DONTLOG

echo_head "Setting DELETION POLICY to 'SHIPPED TO ALL STANDBY'"
run_rman $inst 'CONFIGURE ARCHIVELOG DELETION POLICY TO SHIPPED TO ALL STANDBY;' > /dev/null && echo_success || echo_failure

echo_head "Reconfiguring tnsnames.ora"
tnsfile=$TNS_ADMIN/tnsnames.ora
sed -i "s/${DB}_P/${UNIQUE_P}/
s/${DB}_S/${UNIQUE_S}/" $tnsfile && echo_success || echo_failure

if [ "$UNIQUE_P" != "$CUR_UNIQUE" ]; then
  echo
  echo "Database must be restarted with new parameters"
  echo "Should I restart it now?"
  read ret
  [ $(echo $ret | tr '[:lower:]' '[:upper:]') != "Y" ] && echo_failure "Please restart the instance and retry." || run_sql $DB "startup force;" >/dev/null || quitOnError "Could not restart database"
fi

echo "Reconfigure dataguard result"
[ "$failures" ] && echo_success || quitOnError
}

function configPrimaryDG()
{
unset failures
#  configPrimaryDG $DB $SECONDARY $PASSWORD
DB=$1
inst=$(sidFromOratab ${DB})
SECONDARY=$2
PW=$3
DOMAIN=$(hostname -d)
PRIMARY=$(hostname -s)
UNIQUE_P=${DB}_1
UNIQUE_S=${DB}_2

echo_head "Setting up $DB as Primary database"; echo

export ORACLE_HOME=$(homeFromOratab ${inst})

if [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -eq 0 ]; then
  echo_head "Instance is not running. Starting instance..."
  run_sql "$inst" "startup;"
  [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -eq 0 ] && echo_success || quitOnError "Could not start instance"
fi

echo_head "Creating new services if needed"; echo
SERVICES=" $(run_sql $DB 'select NETWORK_NAME from v$services;' | xargs) "
for svc in $UNIQUE_P $DB
do
  echo_head "$svc"
  echo "$SERVICES" | grep -iq " $svc.$DOMAIN " && { echo_passed "Already existing" ; continue; }
  echo "exec dbms_service.create_service('$svc','$svc.$DOMAIN');
  exec dbms_service.start_service('$svc');" | run_sql $DB >/dev/null && echo_success || echo_failure
done

echo_head "Setting up listener.ora"
lsnrfile=$TNS_ADMIN/listener.ora
bakfile="$lsnrfile".$(date +%Y%m%d%H%M%S)
cp "$lsnrfile" "$bakfile"
LSNR_NAME=$(awk 'BEGIN{IGNORECASE=1}/^listener/{sub(/ .*/,"",$0);print $0}' $lsnrfile)
if [ $(grep -c "SID_LIST_${LSNR_NAME}" "$lsnrfile") -gt 0 ]; then
  if [ $(grep -c "SID_DESC=(GLOBAL_DBNAME=${UNIQUE_P}.${DOMAIN})" "$lsnrfile") -eq 0  ]; then
    #Voeg een regel toe bij SID_LIST_ hoofdstuk aan het SID_LIST deel
    #Dit verzorgt meteen een juiste spatie format aan het begin van de regel
    sed "/SID_LIST_${LSNR_NAME} *=/,$ {/SID_LIST *=/ a\
\ (SID_DESC=(GLOBAL_DBNAME=${UNIQUE_P}.${DOMAIN})(SID_NAME=${DB})(ORACLE_HOME = ${ORACLE_HOME}))
}" "$bakfile" > "$lsnrfile"
  fi
else
  echo "
SID_LIST_${LSNR_NAME}=
  (SID_LIST=
    (SID_DESC=(GLOBAL_DBNAME=${UNIQUE_P}.${DOMAIN})(SID_NAME=${DB})(ORACLE_HOME = ${ORACLE_HOME}))
  )
" >> $lsnrfile
fi
{ $ORACLE_HOME/bin/lsnrctl status | oraLogger; }
[ ${PIPESTATUS[0]} -eq 0 ] && { $ORACLE_HOME/bin/lsnrctl reload | oraLogger; } || { $ORACLE_HOME/bin/lsnrctl start | oraLogger; }
[ $? -eq 0 ] && echo_success || echo_failure

echo_head "Setting up tnsnames.ora"
tnsfile=$TNS_ADMIN/tnsnames.ora

  echo "
${UNIQUE_P} =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${PRIMARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_P}.${DOMAIN})
    )
  )

${UNIQUE_S} =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${SECONDARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_S}.${DOMAIN})
    )
  )

${DB} =
(DESCRIPTION =
      (ADDRESS_LIST =
          (LOAD_BALANCE = OFF)
          (FAILOVER = ON)
          (ADDRESS =
              (PROTOCOL = TCP)
              (HOST = ${PRIMARY}.${DOMAIN})
              (PORT = 1521))
          (ADDRESS =
              (PROTOCOL = TCP)
              (HOST = ${SECONDARY}.${DOMAIN})
              (PORT = 1521)))
      (CONNECT_DATA =
          (SERVICE_NAME = ${DB}.${DOMAIN})
          (FAILOVER_MODE =
              (FAILOVER = ON)
              (TYPE = SELECT)
              (METHOD = BASIC)
              (RETRIES = 10)
              (DELAY = 10))
          (SERVER = DEDICATED)))

"  | "$TNSEDIT" -o "$tnsfile" | oraLogger
[ $? -eq 0 ] && echo_success || echo_failure "Could not write to $tnsfile"

echo_head "Checking logmode"
LOGMODE=$(run_sql $inst 'SELECT log_mode FROM v$database;')
[ "$LOGMODE" = "ARCHIVELOG" ] && echo_success || echo_warning "Please ALTER DATABASE ARCHIVELOG (Instance restart is required)."

if [ $(run_sql $inst 'select FORCE_LOGGING from v$database;') != 'YES' ]; then
  echo_head "Force logging"
  run_sql $inst 'ALTER DATABASE FORCE LOGGING;' >/dev/null && echo_success || echo_failure
fi

echo "Setting default parameters" | oraLoggerWithOutput
run_sql $inst "ALTER SYSTEM SET DG_BROKER_START=TRUE;" >/dev/null || { echo_head "set dg_brokker_start" ; echo_failure; }
DBUNIQUENAME=$(run_sql $inst "select UPPER(value) from v\$parameter where name = 'db_unique_name';")
RLPWF=$(run_sql $inst "select UPPER(value) from v\$parameter where name = 'remote_login_passwordfile';")
if [ $DBUNIQUENAME != "${UNIQUE_P}" -o $RLPWF != 'EXCLUSIVE' ]; then
  run_sql $inst "alter system set db_unique_name='${UNIQUE_P}' scope=spfile;" >/dev/null || { echo_head "set db_unique_name" ; echo_failure; }
  run_sql $inst "ALTER SYSTEM SET REMOTE_LOGIN_PASSWORDFILE=EXCLUSIVE SCOPE=SPFILE;" >/dev/null || { echo_head "set remot_login_password_file" ; echo_failure; }

  echo
  echo "Database must be restarted with new parameter for db_unique_name"
  echo "Should I restart it now?"
  read ret
  [ $(echo ${ret:0:1} | tr '[:lower:]' '[:upper:]') == "Y" ] && { run_sql $inst "startup force;" >/dev/null || echo_failure "Could not restart database."; } || echo_failure "Please restart the instance before using this configuration."
fi
run_sql $inst "grant sysdba to DBSNMP;" >/dev/null || { echo_head "grant sysdba to DBSNMP" ; echo_failure; }

run_sql $inst "alter system set archive_lag_target = 7200;" >/dev/null || { echo_head "set archive_lag_target" ; echo_failure; }

run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_CONFIG='DG_CONFIG=(${UNIQUE_P},${UNIQUE_S})';" >/dev/null || { echo_head "set log_archive_config" ; echo_failure; }

run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_DEST_1='LOCATION=USE_DB_RECOVERY_FILE_DEST VALID_FOR=(ALL_LOGFILES, ALL_ROLES) DB_UNIQUE_NAME=${UNIQUE_P}';" >/dev/null || { echo_head "set log_archive_dest_1" ; echo_failure; }
#run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_DEST_2='SERVICE=${UNIQUE_S} ASYNC VALID_FOR=(ONLINE_LOGFILE,PRIMARY_ROLE) db_unique_name=${UNIQUE_S}';" >/dev/null || { echo_head "set log_archive_dest_2" ; echo_failure; }
run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_DEST_STATE_2=ENABLE;" >/dev/null || { echo_head "set log_archive_state_2" ; echo_failure; }

#run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_FORMAT='%t_%s_%r.arc' SCOPE=SPFILE; " >/dev/null || quitOnError "Could not set LOG_ARCHIVE_FORMAT"
run_sql $inst "ALTER SYSTEM SET LOG_ARCHIVE_MAX_PROCESSES=5;" >/dev/null || { echo_head "set log_archive_max_processes" ; echo_failure; }

run_sql $inst "ALTER SYSTEM SET FAL_SERVER=${UNIQUE_S};" >/dev/null || { echo_head "set fal_server" ; echo_failure; }
run_sql $inst "ALTER SYSTEM SET FAL_CLIENT=${UNIQUE_P};" >/dev/null || { echo_head "set fal_client" ; echo_failure; }

#Zie http://docs.oracle.com/cd/B19306_01/server.102/b14239/rcmbackp.htm#CHDDDICH
#Voor OMF dus geen log_file_name_convert en db_file_name_convert gebruiken...

run_sql $inst "select a.ksppinm ||'='||b.ksppstvl from sys.x\$ksppi a, sys.x\$ksppcv b where a.indx = b.indx and a.ksppinm like '%_file_name_convert' order by ksppinm;
select 'BCT='||status from v\$block_change_tracking;" |  tr '[:lower:]' '[:upper:]' | while read line; do
  P=$(echo "$line" | awk 'BEGIN{FS="="}{print $1}')
  V=$(echo "$line" | awk 'BEGIN{FS="="}{print $2}')
  if [ "$P" = "DB_FILE_NAME_CONVERT" -a "$V" ]; then
    run_sql $inst "ALTER SYSTEM RESET DB_FILE_NAME_CONVERT SCOPE=SPFILE;" >/dev/null
    if [ $? -ne 0 ]; then
      echo_head "reset db_file_name_convert"
      echo_failure
    fi
  elif [ "$P" = "LOG_FILE_NAME_CONVERT" -a "$V" ]; then
    run_sql $inst "ALTER SYSTEM RESET LOG_FILE_NAME_CONVERT SCOPE=SPFILE;" >/dev/null
    if [ $? -ne 0 ]; then
      echo_head "reset log_file_name_convert"
      echo_failure
    fi
  elif [ "$P" = "BCT" -a "$V" != 'DISABLED' ]; then
    run_sql $inst "alter database disable block change tracking;" >/dev/null
    if [ $? -ne 0 ]; then
      echo_head "disable block change tracking"
      echo_failure
    fi
  fi
done

run_sql $inst "ALTER SYSTEM SET STANDBY_FILE_MANAGEMENT=AUTO;" >/dev/null || { echo_head "set standby_file_management" ; echo_failure; }

DBRFDS=$(run_sql $inst "select value from v\$parameter where name = 'db_recovery_file_dest_size';")
[ $DBRFDS -gt $((20*1024*1024*1025)) ] || run_sql $inst "alter system set db_recovery_file_dest_size=20g;" >/dev/null || echo_failure "Could not set DB_RECOVERY_FILE_DEST_SIZE"
FBState=$(run_sql $inst 'select FLASHBACK_ON from v$database;')
[ $FBState = 'YES' ] ||  run_sql $inst "alter database flashback on;" >/dev/null || { echo_head "flashback on" ; echo_failure; }

[ "$DBG" ] || DONTLOG=1
run_sql $inst "alter user sys identified by $PW;" >/dev/null || { echo_head "user sys identified by" ; echo_failure; }
unset DONTLOG
run_sql $inst "alter user sys account unlock;" >/dev/null || { echo_head "user sus account unlock" ; echo_failure; }

echo_head "Ping primary database"
$ORACLE_HOME/bin/tnsping ${UNIQUE_P} | oraLogger
[ "${PIPESTATUS[0]}" -eq 0 ] && echo_success || echo_failure "Could not ping primary database."

echo "Setting up standby logfiles" | oraLoggerWithOutput
StdByLogCount=$(run_sql "$inst" "select count(*) from (select distinct group# from v\$logfile where type='STANDBY') tmp;")
NormalLogCount=$(run_sql "$inst" "select count(*) from (select distinct group# from v\$logfile where type='ONLINE') tmp;")
[ $StdByLogCount -gt 0 ] && GroupNr=$(run_sql $inst "select max(group#)+1 from v\$logfile where type='STANDBY';") || GroupNr=$((($NormalLogCount/10+1)*10))
StdbyRedoSize=$(run_sql "$inst" "select max(bytes) from V\$LOG;")
for ((i=$GroupNr;i<($GroupNr+$NormalLogCount-$StdByLogCount);i++))
do
   echo_head "Creating loggroup $i"
   run_sql $inst "ALTER DATABASE ADD STANDBY LOGFILE GROUP $i SIZE $StdbyRedoSize;" >/dev/null && echo_success || echo_failure "Could not create group $i"
done

echo_head "Setting DELETION POLICY to 'SHIPPED TO ALL STANDBY'"
run_rman $inst 'CONFIGURE ARCHIVELOG DELETION POLICY TO SHIPPED TO ALL STANDBY;' > /dev/null && echo_success || echo_failure

echo_head "Creating DG configuration"
run_dgmgrl $inst "CREATE CONFIGURATION $DB AS PRIMARY DATABASE IS ${DB}_1 CONNECT IDENTIFIER IS ${DB}_1;" > /dev/null
if [ $? -eq 0 ]; then
  echo_success
  echo_head "Enabling DG configuration"
  run_dgmgrl $inst "ENABLE CONFIGURATION;" > /dev/null && echo_success || echo_failure 'Could not enable configuration...'
else
  echo_failure 'Could not create configuration...'
fi

echo_head "Setting up primary Dataguard database result"
[ ! "$failures" ] && echo_success || quitOnError
#CREATE PFILE='/tmp/initD139T_s.ora' FROM SPFILE;
}

function configSecondaryDG()
{
unset failures
DB=$1
PRIMARY=$2
PW=$3
[ $4 ] && UNIQUE_P=${DB}$4 || UNIQUE_P=${DB}_1
[ $5 ] && UNIQUE_S=${DB}$5 || UNIQUE_S=${DB}_2

#LET OP: configSecondaryDG wordt standaard gebruikt om een Secondary database te koppelen aan een Primaire database.
#in Sommige gevallen kan echter de _2 database de Primary database zijn en in dat geval wordt (bij gebruik maken van -recreate)
#$UNIQUE_P ingesteld op ${DB}_2 en $UNIQUE_S ingesteld op ${DB}_2. 
#Dit gaat nogal tegen het gevoel in, maar levert wel het gewenste resultaat...

DOMAIN=$(hostname -d)
SECONDARY=$(hostname -s)
inst=$(sidFromOratab $DB)

echo_head "Setting up $DB as Secondary database"; echo

if [ ! $inst ]; then
  #Hoop maar dat deze het is...
  export ORACLE_HOME=$(ls -d /u01/app/oracle/product/*/db* | tail -n1)
  echo "$DB:$ORACLE_HOME:Y" >> /etc/oratab
  inst=$DB
else
  export ORACLE_HOME=$(homeFromOratab $inst | sort -u | tail -n1)
fi

if [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -gt 0 ]; then
  echo_head "Instance is running. Shutting down."
  run_sql "$inst" "shutdown immediate;" >/dev/null
  [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -gt 0 ] && echo_success || quitOnError "Could not stop instance"
fi

#Tijdelijke PFile aanmaken met Bare minimum aan gegevens.:
echo_head "Creating temporary PFile"
PFILE=/tmp/init${DB}.ora
[ -f $PFILE ] && rm $PFILE
echo "*.db_name='${DB}'
*.remote_login_passwordfile='EXCLUSIVE'" >> $PFILE 2>/dev/null && echo_success || quitOnError "Could not create PFILE $PFILE"

echo_head "Setting up tnsnames.ora"

if [ "$hn" = "$PRIMARY" ]; then
 RMAN_TNS="
${DB}_RMAN =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${PRIMARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_P}.${DOMAIN})
    )
  )
"
elif [ "$hn" = "$SECONDARY" ]; then
 RMAN_TNS=" 
${DB}_RMAN =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${SECONDARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_S}.${DOMAIN})
    )
  )
"
fi


tnsfile=$TNS_ADMIN/tnsnames.ora

  echo "
${UNIQUE_P} =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${PRIMARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_P}.${DOMAIN})
    )
  )

${UNIQUE_S} =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = ${SECONDARY}.${DOMAIN})(PORT = 1521))
    )
    (CONNECT_DATA =
      (SERVICE_NAME = ${UNIQUE_S}.${DOMAIN})
    )
  )

${RMAN_TNS}

${DB} =
(DESCRIPTION =
      (ADDRESS_LIST =
          (LOAD_BALANCE = OFF)
          (FAILOVER = ON)
          (ADDRESS =
              (PROTOCOL = TCP)
              (HOST = ${PRIMARY}.${DOMAIN})
              (PORT = 1521))
          (ADDRESS =
              (PROTOCOL = TCP)
              (HOST = ${SECONDARY}.${DOMAIN})
              (PORT = 1521)))
      (CONNECT_DATA =
          (SERVICE_NAME = ${DB}.${DOMAIN})
          (FAILOVER_MODE =
              (FAILOVER = ON)
              (TYPE = SELECT)
              (METHOD = BASIC)
              (RETRIES = 10)
              (DELAY = 10))
          (SERVER = DEDICATED)))

"  | "$TNSEDIT" -o "$tnsfile" | oraLogger
[ $? -eq 0 ] && echo_success || echo_failure "Could not write to $tnsfile"

echo_head "Setting up listener.ora"
lsnrfile=$TNS_ADMIN/listener.ora
bakfile="$lsnrfile".$(date +%Y%m%d%H%M%S)
cp "$lsnrfile" "$bakfile"

LSNR_NAME=$(awk 'BEGIN{IGNORECASE=1}/^listener/{sub(/ .*/,"",$0);print $0}' $lsnrfile)
if [ $(grep -c "SID_LIST_${LSNR_NAME}" "$lsnrfile") -gt 0 ]; then
  if [ $(grep -c "SID_DESC=(GLOBAL_DBNAME=${UNIQUE_S}.${DOMAIN})" "$lsnrfile") -eq 0  ]; then
    #Voeg een regel toe bij SID_LIST_ hoofdstuk aan het SID_LIST deel
    #Dit verzorgt meteen een juiste spatie format aan het begin van de regel
    sed "/SID_LIST_${LSNR_NAME} *=/,$ {/SID_LIST *=/ a\
\ (SID_DESC=(GLOBAL_DBNAME=${UNIQUE_S}.${DOMAIN})(SID_NAME=${DB})(ORACLE_HOME = ${ORACLE_HOME}))
}" "$bakfile" > "$lsnrfile"
  fi
else
  echo "
SID_LIST_${LSNR_NAME}=
  (SID_LIST=
    (SID_DESC=(GLOBAL_DBNAME=${UNIQUE_S}.${DOMAIN})(SID_NAME=${DB})(ORACLE_HOME = ${ORACLE_HOME}))
  )
" >> $lsnrfile
fi
$ORACLE_HOME/bin/lsnrctl status $LSNR_NAME | oraLogger
[ "${PIPESTATUS[0]}" -eq 0 ] && { $ORACLE_HOME/bin/lsnrctl reload $LSNR_NAME | oraLogger; } || { $ORACLE_HOME/bin/lsnrctl start $LSNR_NAME | oraLogger; }
[ $? -eq 0 ] && echo_success || quitOnError "Could not reload listener $LSNR_NAME"

echo_head "Generating / replacing passwordfile"
pwfile="$ORACLE_HOME/dbs/orapw$inst"
[ -f $pwfile ] && rm $pwfile
$ORACLE_HOME/bin/orapwd file=$pwfile entries=10 force=y <<EOF | oraLogger
$PW
EOF
[ $? -eq 0 ] && echo_success || quitOnError "Could not create Password file $pwfile"

echo_head "Creating folders"
mkdir -p /{u02/oradata,u03/fra}/${DB}{,_1,_2,_P,_S}/{archivelog,controlfile,datafile,onlinelog} 2>&1 | oraLogger || quitOnError "Could not create folder's in /u02/oradata and /u03/fra"
AUDIT_DEST=$ORACLE_BASE/diag/rdbms/$(echo "${UNIQUE_S}" | tr '[:upper:]' '[:lower:]' )/$DB/adump
mkdir -p "$AUDIT_DEST" 2>&1 | oraLogger && echo_success || quitOnError "Could not create folder $AUDIT_DEST"

echo_head "Starting Instance in nomount"
run_sql $inst "STARTUP NOMOUNT PFILE='$PFILE';" >/dev/null && echo_success || quitOnError "Could not start instance with PFile $PFILE."

echo_head "Running RMAN DUPLICATE DATABASE"
#[ "$DBG" ] || DONTLOG=1
$ORACLE_HOME/bin/rman <<EOF | oraLogger
CONNECT TARGET sys/${PW}@${UNIQUE_P}
CONNECT AUXILIARY sys/${PW}@${UNIQUE_S}
DUPLICATE TARGET DATABASE
  FOR STANDBY
  FROM ACTIVE DATABASE
  DORECOVER
  SPFILE
    SET db_unique_name='${UNIQUE_S}' COMMENT 'Is standby'
    SET audit_file_dest='$AUDIT_DEST'
    SET LOG_ARCHIVE_DEST_1='LOCATION=USE_DB_RECOVERY_FILE_DEST VALID_FOR=(ALL_LOGFILES, ALL_ROLES) DB_UNIQUE_NAME=${UNIQUE_S}'
    SET FAL_SERVER='${UNIQUE_P}' COMMENT 'Is primary'
    SET FAL_CLIENT='${UNIQUE_S}' COMMENT 'Is secondary'
  NOFILENAMECHECK;
EOF
[ $? -eq 0 ] && echo_success || quitOnError "RMAN Finished with errors. Please check state of database and continue manually."
#unset DONTLOG

echo_head "Turning on broker"
run_sql $inst "ALTER SYSTEM SET DG_BROKER_START=TRUE;" >/dev/null && echo_success || echo_failure;

#LET OP:     SET CONTROL_FILES='/u02/oradata/${DB}_2/controlfile/control1.ctl,/u03/fra/${DB}_2/controlfile/control2.ctl' werkt niet.
#Reden: Aan de primaire zijde is deze aangemaakt middels OMF.
# Oplossingen: Geen OMF voor Primaire zijde (niet gewenst), of zonder dit statement, maar dan komen ze in de _1 directories terecht.
# later dan maar verplaatsen naar de _2 directory.

#Zie http://docs.oracle.com/cd/B19306_01/server.102/b14239/rcmbackp.htm#CHDDDICH
#Voor OMF dus geen log_file_name_convert en db_file_name_convert gebruiken...
#Daarmee zou onderstaande workaround weg kunnen vallen.

echo_head "Moving Control files to $UNIQUE_S folder"
unset par
run_sql $inst "STARTUP NOMOUNT FORCE;" >/dev/null || quitOnError "Could not restart instance NOMOUNT."
echo
for src in $(run_sql "$inst" "select VALUE from v\$parameter where NAME='control_files';" | awk '{gsub(","," ",$0);print $0}')
do
  dst=$(echo "$src" | sed 's|'$inst'[^/]*|'$UNIQUE_S'|')
  mkdir -p $(dirname ${dst})
  if [ "$dst" != "$src" ]; then
    echo_head "Moving $src"
    mv "$src" "$dst" && echo_success " to $dst" || quitOnError "Could not move $src to $dst."
  fi
  par="$par,'$dst'"
done
echo_head "Setting new locations to control files"
run_sql $inst "ALTER SYSTEM SET CONTROL_FILES=${par:1} scope=spfile;" >/dev/null && echo_success || echo_failure "Could not change CONTROL_FILES parameter."

echo_head "Reset services parameter (was copied from primary)."
run_sql $inst "alter system reset service_names scope=spfile;" >/dev/null && echo_success || echo_passed

echo_head "Restarting instance with new parameters."
run_sql $inst "STARTUP MOUNT FORCE;" >/dev/null && echo_success || quitOnError "Could not restart instance"

echo_head "Cleaning empty folders in /u02 and /u03"
while [ $(find /u02/oradata*/* /u03/fra -type d -empty 2>/dev/null | wc -l) -gt 0 ]
do
  find /u02/oradata*/* /u03/fra -type d -empty 2>/dev/null | while read d
  do
    echo "Cleaning $d" | oraLogger
    rmdir "$d"
  done
done
echo_success

echo_head "Turning on FLASHBACK DATABASE"
FBState=$(run_sql $inst 'select FLASHBACK_ON from v$database;')
if [ $FBState = 'YES' ]; then
   echo_passed 'Already on'
else
   run_sql $inst "alter database flashback on;" >/dev/null && echo_success || { echo_head "flashback on" ; echo_failure; }
fi

echo_head "Starting redo apply"
run_sql "$inst" "ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT FROM SESSION;" >/dev/null && echo_success || quitOnError

echo_head "Adding secondary database $UNIQUE_S to DG broker Configuration"
run_dgmgrl $DB "ADD DATABASE $UNIQUE_S AS CONNECT IDENTIFIER IS $UNIQUE_S;" > /dev/null
if [ $? -eq 0 ]; then
  echo_success
  echo_head "Enabling secondary database $UNIQUE_S in DG broker Configuration"
  run_dgmgrl $DB "ENABLE DATABASE $UNIQUE_S;" > /dev/null && echo_success || echo_failure "Could not enable secondary database $UNIQUE_S..."

else
  echo_failure "Could not add secondary database $UNIQUE_S..."
fi

#echo_head "Setting DELETION POLICY to 'APPLIED ON STANDBY'"
#run_rman $inst 'CONFIGURE ARCHIVELOG DELETION POLICY TO SHIPPED TO ALL STANDBY;' >/dev/null
#[ "${PIPESTATUS[0]}" -eq 0 ] && echo_success || echo_failure

echo_head "Setting up secondary Dataguard database result"
[ ! "$failures" ] && echo_success || quitOnError
}

function usage()
{
  cat << EOF
  usage: $0 options DB
:x

  Gebruik dit script om een Oracle database te configureren voor Dataguard.
  Draai het script eerst op de primary server, dan configureert hij een bestaande database als DG Primary.
  Draai het script daarna pas op de Secondary server, dan maakt hij daar een nieuwe DG Secondary database server aan.
  Op de Primary moet de database reeds correct zijn aangemaakt. op de secundaire mag hij niet bestaan.
  Gebruik eventueel de optie -recreate om alle oude database zooi op te ruimen voor hij opnieuw wordt aangemaakt.

  Het script kan ook worden gebruikt op een beheer server (uitgaande van ssh key uitwisseling). In dat geval:
  - Genereert hij een SYS wachtwoord (als deze niet meegegeven is)
  - Gaat daarna via SSH naar de primary node en start zichzelf voor primary gebruik.
  - Gaat daarna via SSH naar de secondary node en start zichzelf voor secondary gebruik.

  OPTIONS:
     -h         toont dit helpscherm
     -DB        De SID van de Database    (default standaard)
     -primary   De primary DB server      (Indien niet gespecificeert, dan haalt hij deze uit tnsnames, of rekent hem terug van -secondary).
                                          -primary of -secondary moet zijn gespecificeert.
     -secondary De secondary DB server    (Indien niet gespecificeert, dan haalt hij deze uit tnsnames, of rekent hem terug van -primary).
                                          -primary of -secondary moet zijn gespecificeert.
     -password  SYS password              (geen default)
     -reconfig  Hersteld de DG            (default uit)
                configuratie (uitgeklede versie van de Primary config).
     -recreate  Deze optie verwijdert een (default uit)
                bestaande database alvorens opnieuw dataguard op te zetten.
                Heeft de secondary database (\$DB_2) de Primare rol, dan kan hiermee de Primary database (\$DB_1)
                opnieuw worden aangemaakt op basis van de Secondary..

     -x         debug mode                (default uit)

     Overige opties worden gezien als database namen.

  Voorbeeld 1: Opzetten dataguard voor de D100T op de srv101 en srv102 (database met -DB optie meegegeven).
    - Maak op de srv101 de database aan met SBB_CreateDatabase.sh (indien nodig): $(dirname $0)/SBB_CreateDatabase.sh -dg D100T
    - Voer uit op de srv101: $0 -DB D100T -primary srv101 -secundary srv102 -password BLAAT
    - Voer uit op de srv102: $0 -DB D100T -primary srv101 -secundary srv102 -password BLAAT
  LET OP: de default waardes van -primary en -secondary parameters zouden automatisch goed ingesteld worden, maar meegeven is veiliger.

  Voorbeeld 2: Vanaf een beheerserver (database naam direct meegegeven).
  - log in op de stepstone en wordt oracle.
  - Voer uit: $0 -primary srv101 -secundary srv102 -password BLAAT D100T
  LET OP: Dit zet zowel de primary node als de secondary node correct op.
  LET OP2: Dit maakt (nog) geen primary database aan (optie voor toekomstige verbetering).

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
  -DB) export DBs="$DBs $2" ; shift 2 ;;
  -primary) PRIMARY=$2 ; shift 2 ;;
  -secondary) SECONDARY=$2 ; shift 2;;
  -password) SYS_PW=$2 ; shift 2;;
  -recreate) RECREATE=1; shift 1 ;;
  -reconfig) RECONFIG=1; shift 1 ;;
  -x) set -vx ; export DBG=1; shift 1 ;;
  *)  DBs="$DBs $1" ; shift 1 ;;
#  *) echo "error: no such option $1" ; exit 1 ;;
esac
done

if [ ! -f /etc/oratab ]; then
  echo "/etc/oratab does not exist. Probably not an Oracle server."
  exit 1
fi

logfile=/tmp/`basename $0 .sh`.log
. /stage/oracle/scripts/bash/oralib >> $logfile

TNSEDIT=$(dirname $(dirname $0))/python/tnsedit.py
[ -x "$TNSEDIT" ] || TNSEDIT=/stage/oracle/scripts/python/tnsedit.py

if [ ! "$DBs" ]; then
  usage
  exit 0
fi

DBs=$(echo "$DBs" | sed 's/[,;]/ /g')

for DB in $DBs
  do
  LOGCH="$(basename $0 .sh) $DB"
  
  export ORACLE_HOME=$(homeFromOratab $DB | sort -u | tail -n1)
  [ -x "$ORACLE_HOME/bin/tnsping" ] || export ORACLE_HOME=$(ls -d /u01/app/oracle/product/*/db* | tail -n1)
  [ -x "$ORACLE_HOME/bin/tnsping" ] || quitOnError "No valid Oracle home could be detected..."
  
  hn=$(hostname -s | tr '[:upper:]' '[:lower:]')
  
  [ "$PRIMARY" -o "$SECONDARY" ] || quitOnError "Will not continue without -primary or -secondary specified"
  
  if [ ! $PRIMARY ]; then
    # uit tnsnames lezen
    PRIMARY=$(tnsping ${DB}_1 | awk '/HOST *= */{sub(/.*HOST *= */,"");sub(/\).*/,"");sub(/\..*/,"");print $0}')
    [ ! $PRIMARY ] && PRIMARY=$(addToString $SECONDARY -1)
  fi
  
  if [ ! $SECONDARY ]; then
    # uit tnsnames lezen
    SECONDARY=$(tnsping ${DB}_2 | awk '/HOST *= */{sub(/.*HOST *= */,"");sub(/\).*/,"");sub(/\..*/,"");print $0}')
    [ ! $SECONDARY ] && SECONDARY=$(addToString $PRIMARY +1)
  fi
  
  if [ ! $SYS_PW ]; then
    if [ "$hn" != "$PRIMARY" -a "$hn" != "$SECONDARY" ]; then
      SYS_PW=$(randpass)
    else
      echo_head "Please specify sys password:"
      read -s SYS_PW
      [ $SYS_PW ] && echo_success || quitOnError "No password specified"
    fi
  fi
  
  if [ $RECREATE ]; then
  #  [ "$hn" = "$PRIMARY" ] && quitOnError "Dit mag niet op de primary database server worden uitgevoerd."
    [ "$RECONFIG" ] && quitOnError "Cannot Reconfigure AND Recreate. Please choose."
    
    echo_head "Checking for running database $DB"
  # Als de database draait, dan controleren dat hij niet Primary is.
  # Als hij niet draait, dan controleren of er een secondary is die goed functioneert.
  # Als de andere kant 
    [ "$hn" != "$PRIMARY" ] && OTHER_SID=${DB}_1 || OTHER_SID=${DB}_2
  
    tnsping ${OTHER_SID} 2>&1 >/dev/null || quitOnError "Cannot TNSPING secondary database ${OTHER_SID}."
  
    HIS_ROLE=$($ORACLE_HOME/bin/sqlplus -s sys/${SYS_PW}@${OTHER_SID} as sysdba <<EOF
  set pagesize 0
  set linesize 32767
  select database_role from v\$database;
EOF
  )
    [ "$HIS_ROLE" = "PRIMARY" ] && echo_success "Other database has Primary role" || quitOnError "Cannot recreate without properly functioning database with primary role."
  
    echo_head "Shutting down instance"
    run_sql ${DB} 'shutdown abort;' >/dev/null && echo_success || echo_failure
  
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
  
#    echo_head "Cleaning tnsnames for database $DB"
#    tnsfile=$TNS_ADMIN/tnsnames.ora

#    SIDS=$("$TNSEDIT" -l "$tnsfile" | grep D999P | xargs | sed 's/ /,/g')
#    [ "$SIDS" ] && "$TNSEDIT" -o "$tnsfile" -d "$SIDS" | oraLogger
#    [ $? -eq 0 ] && echo_success || echo_failure "Could not write to $tnsfile"

    echo_head "Cleaning listener for database $DB"
    lsnrfile=$TNS_ADMIN/listener.ora
    bakfile="$lsnrfile".$(date +%Y%m%d%H%M%S)
    cp "$lsnrfile" "$bakfile"
    [ $? -eq 0 ] && sed -i '/'${DB}'/d' $lsnrfile
    [ $? -eq 0 ] && echo_success || echo_failure
  fi
  
  if [ "$hn" = "$PRIMARY" ]; then
    if [ "$RECONFIG" ]; then
      reconfigureDG $DB $SYS_PW
    elif [ $RECREATE ]; then
      configSecondaryDG $DB $SECONDARY $SYS_PW _2 _1
    else
      configPrimaryDG $DB $SECONDARY $SYS_PW
    fi
  elif [ "$hn" = "$SECONDARY" ]; then
    if [ "$RECONFIG" ]; then
      reconfigureDG $DB $SYS_PW _2 _1
    else
      configSecondaryDG $DB $PRIMARY $SYS_PW
    fi
  else
    [ "$RECONFIG" ] && quitOnError "Reconfigure can only be applied on Primary or Secondary"
    ssh "$PRIMARY" "$0" -DB "$DB" -primary "$PRIMARY" -secondary "$SECONDARY" -password "$SYS_PW"
    ssh "$SECONDARY" "$0" -DB "$DB" -primary "$PRIMARY" -secondary "$SECONDARY" -password "$SYS_PW"
  fi
  done
