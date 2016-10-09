#!/bin/bash
#
# Script	:	srvmgmt.sh
# Purpose	:	Do all managament (start, stop, status, etc) for oracle servers (DB, DB-RAC, AS, OID, etc/)
# Author	:      	Sebastiaan Mannem (original version: Willem Vernes ism Henk Uiterwijk)
# Date		:	26/09/11

# tee >(proces1) >(proces2) | lastproces
# ls -A | tee >(grep ^[.] > hidden-files) >(grep -v ^[.] > normal-files) | less

function timeout()
{
#Voorbeeld aanroep: 
#timeout -t 5 sleep 10 2>/dev/null
# 2>/dev/null voorkomt een melding zoals:
#/home/oracle/bin/srvmgmt.sh: line 1104: 14604 Terminated              /home/oracle/bin/timeout.sh $@ 2>&1

  scriptpath=`dirname $0`
  echo $scriptpath/timeout.sh $@
  $scriptpath/timeout.sh $@ 2>&1
}

function stop_agent()
{
  AG_HOMES=$(awk 'BEGIN {FS=":";IGNORECASE="1"} /^ag/ {print $2}' < /etc/oratab | sort -u)
  if [ ! "$AG_HOMES" ]; then
    echo_head "no agent home could not be detected. Skipping..."
    echo_passed
  else
    echo "Stopping agents"
    for AG_HOME in $AG_HOMES
    do
      if [ ! -x $AG_HOME/bin/emctl ]; then
        echo_head "$AG_HOME" ; echo_failure "Can not execute $AG_HOME/bin/emctl"
      else
        start_autoblackout "$AG_HOME"
        echo_head "Stopping $AG_HOME"
        timeout -t 30 $AG_HOME/bin/emctl stop agent | oraLogger
        [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
      fi
    done
  fi
}

function start_agent()
{
  AG_HOMES=$(awk 'BEGIN {FS=":";IGNORECASE="1"} /^ag/ {print $2}' < /etc/oratab | sort -u)
  if [ ! "$AG_HOMES" ]; then
    echo_head "no agent home could not be detected. Skipping..."
    echo_passed
  else
    echo "Starting agent"
    for AG_HOME in $AG_HOMES
    do
      echo_head "$AG_HOME"
      if [ ! -x $AG_HOME/bin/emctl ]; then
        echo_failure "Can not execute $AG_HOME/bin/emctl"
      else
        timeout -t 30 $AG_HOME/bin/emctl start agent | oraLogger
        [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
      fi
    done
  fi
}

function show_blackout()
{
  AG_HOMES=$(awk 'BEGIN {FS=":";IGNORECASE="1"} /^ag/ {print $2}' < /etc/oratab | sort -u)
  if [ ! "$AG_HOMES" ]; then
    echo_head "no agent home could not be detected. Skipping..."
    echo_passed
  else
    echo "Showing blackouts"
    for AG_HOME in $AG_HOMES
    do
      echo_head "$AG_HOME"
      if [ ! -x $AG_HOME/bin/emctl ]; then
        echo_failure "Can not execute $AG_HOME/bin/emctl"
      else
        echo_success
        $AG_HOME/bin/emctl status blackout | sed -n '3,$ p'
      fi
    done
  fi
}

function start_autoblackout()
{
  [ "$1" ] && AG_HOMES="$1" || AG_HOMES=$(awk 'BEGIN {FS=":";IGNORECASE="1"} /^ag/ {print $2}' < /etc/oratab | sort -u)
  if [ ! "$AG_HOMES" ]; then
    echo_head "no agent home could not be detected. Skipping..."
    echo_passed
  else
    echo "Setting autoblackout"
    for AG_HOME in $AG_HOMES
    do
      echo_head "$AG_HOME"
      if [ ! -x $AG_HOME/bin/emctl ]; then
        echo_failure "Can not execute $AG_HOME/bin/emctl"
      elif [ `$AG_HOME/bin/emctl status blackout | grep autoblackout | wc -l` -ne 0 ]; then
        echo_passed "Autoblackout already exists"
      else
        timeout -t 30 $AG_HOME/bin/emctl start blackout autoblackout -nodeLevel 2>&1 | oraLogger
        [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
      fi
    done
  fi
}

function stop_autoblackout()
{
  AG_HOMES=$(awk 'BEGIN {FS=":";IGNORECASE="1"} /^ag/ {print $2}' < /etc/oratab | sort -u)
  if [ ! "$AG_HOMES" ]; then
    echo_head "no agent home could not be detected. Skipping..."
    echo_passed
  else
    echo "Stopping autoblackout"
    for AG_HOME in $AG_HOMES
    do
      echo_head "$AG_HOME"
      if [ ! -x $AG_HOME/bin/emctl ]; then
        echo_failure "Can not execute $AG_HOME/bin/emctl"
        continue
      elif [ `$AG_HOME/bin/emctl status blackout | grep autoblackout | wc -l` -eq 0 ]; then
        echo_warning "Autoblackout does not exist"
      else
        timeout -t 60 $AG_HOME/bin/emctl stop blackout autoblackout 2>&1 | oraLogger
        [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
        if ! $AG_HOME/bin/emctl status agent > /dev/null 2>&1
          then
          echo_head "Agent down. Blackout will disappear once agent is started."
          echo_warning
        fi
      fi
    done
  fi
}

function patchlist_app_up()
{
  echo_head "Updating patchlist" 
  echo | oraLogger
  /usr/bin/wget "http://patchlist.domain.org/auto_patch/autoup.php?hostname=`hostname`&section=app_up&username=(oracle)" -O - 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
}

function patchlist_app_down()
{
  echo_head "Updating patchlist"
  /usr/bin/wget "http://patchlist.domain.org/auto_patch/autoup.php?hostname=`hostname`&section=app_down&username=(oracle)" -O - 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
}

function show_clustername()
{
  [ $CRS_HOME ] && echo Cluster: `$CRS_HOME/bin/cemutlo -n`
  echo
}

function show_stats()
{
  if [ $CRS_HOME ] ; then
    echo "Oracle Resources:"
    echo "-----------------------------------------------------------------------------"
    echo
    show_crs
    echo
    echo
    echo "-----------------------------------------------------------------------------"
  else
    echo "show_stats skipped. No CRS installed..."
  fi
}

function show_nodes()
{
  if [ $CRS_HOME ]; then
    echo 
    echo The cluster consists of the following nodes:
    echo "-----------------------------------------------------------------------------"
    $CRS_HOME/bin/olsnodes
    echo "-----------------------------------------------------------------------------"
    echo
    echo
  else
    echo `hostname` is no clusternode
    echo ------------------------------------------------------------------------------
    echo
    echo
    return 1
  fi
}

function start_oms()
{
  if [ $OMS_HOME ]; then
    echo_head Trying to start OMS
    if [ `show_oms | grep -c 'Oracle Management Server is Up'` -eq 1 ]; then
      echo_passed
      echo OMS was already up
    else
      export ORACLE_INSTANCE=$OMS_HOME
      timeout -t 420 $OMS_HOME/bin/emctl start oms | oraLogger
      timeout -t 30 $OMS_HOME/opmn/bin/opmnctl startall | oraLogger
      [ `show_oms | grep -c 'Oracle Management Server is Up'` -eq 1 ] && echo_success || echo_failure
    fi
  fi
}

function stop_oms()
{
  if [ $OMS_HOME ]; then
    echo_head Trying to stop OMS
    if [ `show_oms | grep -c 'Oracle Management Server is Down'` -eq 1 ]; then
      echo_passed
      echo OMS was already down
      stop_oas oms
    else
      timeout -t 120 $OMS_HOME/bin/emctl stop oms -all | oraLogger
      if [ `show_oms | grep -c 'Oracle Management Server is Down'` -eq 1 ]; then
        echo_success
        stop_oas oms
      else
        echo_failure
      fi
    fi
  fi
}

function show_oms()
{
  [ $OMS_HOME ] && timeout -t 10 $OMS_HOME/bin/emctl status oms
}
 
function start_cman()
{
  [ ! $CMAN_TARGET ] && return 0
  [ ! $CMAN_HOME ] && return 0

  echo_head "Trying to start CMAN $CMAN_TARGET"
  if [ `show_cman | grep -c 'Start date'` -eq 0 ]; then
    run_cman startup 2>&1 | oraLogger
    for ((  i = 0 ;  i <= 20;  i++  ))
    do
      [ `show_cman | grep -c 'Start date'` -ne 0 ] && break
      sleep 1
    done

    if [ -f /tmp/cman_services_pre ]; then
      DONTLOG=1
      for ((  i = 60 ;  i >= 0;  i--  ))
      do
        run_cman "show services" | awk '$1~/Service/{gsub("\"","",$2);print $2}' | sort -u > /tmp/cman_services_post
        if [ `diff -i /tmp/cman_services_pre /tmp/cman_services_post | grep -Ec '^<'` -eq 0 ]; then
          echo_success
          break
        fi
        [ $i -eq 1 ] && echo_warning
        sleep 1
      done
      unset DONTLOG
      MIA=$(diff -i /tmp/cman_services_pre /tmp/cman_services_post | grep -Ec '^<')
      echo "Missing services: $MIA" | oraLogger
    else
      [ `show_cman | grep -c 'Start date'` -ne 0 ] && echo_success || echo_failure
    fi
  else
    echo_passed
    echo CMAN is allready running
  fi
}

function stop_cman()
{
  [ ! $CMAN_TARGET ] && return 0
  [ ! $CMAN_HOME ] && return 0

  echo_head Trying to stop CMAN $CMAN_TARGET
  IsRunning=`timeout -t 10 $0 show_cman | grep -c 'Start date'`
  if [ ! $IsRunning ]; then
    killByPath $CMAN_HOME
    echo_warning
    echo "CMAN was not responding. He is killed."
  elif [ $IsRunning -ne 0 ]; then
    DONTLOG=1
    run_cman "show services" | awk '$1~/Service/{gsub("\"","",$2);print $2}' | sort -u > /tmp/cman_services_pre
    unset DONTLOG
    run_cman "shutdown abort" 2>&1 | oraLogger
    for ((  i = 0 ;  i <= 30;  i++  ))
    do
      sleep 2
      [ `show_cman | grep -c 'Start date'` -eq 0 ] && break
    done

    killByPath $CMAN_HOME
    [ `show_cman | grep -c 'Start date'` -eq 0 ] && echo_success || echo_warning
  else
    killByPath $CMAN_HOME
    echo_passed
    echo CMAN is allready down
  fi
}

function show_cman()
{
  [ ! $CMAN_TARGET ] && return 0
  [ ! $CMAN_HOME ] && return 0

  DONTLOG=1
  run_cman 'show status
show services'
  echo
  unset DONTLOG
}

function show_asmlib()
{
  echo_head "Checking availability of ASMLib"
  if [ ! -f /etc/init.d/oracleasm ]; then
    echo_passed
    echo "/etc/init.d/oracleasm does not exist."
  elif [ `/etc/init.d/oracleasm status | awk 'BEGIN{FS=":"}$2~/^ no$/{print $0}' | wc -l` -ne 0 ]; then
    echo_failure "ASMLib is installed but not functioning correctly"
    return 1
  elif [ `/etc/init.d/oracleasm listdisks | wc -l` -eq 0 ]; then
    echo_warning
    echo "ASMLib is installed and functioning correctly, but no disks where found."
  else
    echo_success
     echo "ASMLib is functioning correctly."
  fi
}

function start_asm()
{
  if [ $(homeFromInventory asm | wc -l) -eq 0 ]; then
    echo_head "No asm installed..." && echo_passed
    return 0
  fi
  [ $1 ] && maxDur=$1 || maxDur=300
  #starttijd in seconden sinds 1-1-1970 (epoch)
  StartEpoch=`date +%s`

  if [ -f /etc/init.d/init.cssd -a ! -f /etc/init.d/init.crs ]; then
    echo_head "Stand alone server with 10g ASM. Checking for CSSD"
    CSSD_HOME=$(awk 'BEGIN{FS="="}$1~/^ORA_CRS_HOME$/{print $2}' /etc/init.d/init.cssd)
    [ `ps -ef | grep -c $CSSD_HOME/bin/[o]cssd.bin` -eq 0 ] && echo_failure CSSD not running
    [ ! -x "$CSSD_HOME/bin/crsctl" ] && echo_failure Cannot execute "'$CSSD_HOME/bin/crsctl'"
    while [ $((`date +%s` - $StartEpoch)) -lt $maxDur ]
    do
      $CSSD_HOME/bin/crsctl check cssd >> /dev/null && break
      sleep 1
    done
    $CSSD_HOME/bin/crsctl check cssd | oraLogger
    if [ $? -eq 0 ]; then
      echo_success
    else
      echo_failure CSSD dit not start in $maxDur seconds.
      return 1
    fi
  fi

  for inst in $(local_instances ASM)
  do
    [ $(ps -ef | grep -c [a]sm_pmon_${inst}) -gt 0 ] && continue
    echo_head "Starting $inst"
    run_sql $inst "startup;" && echo_success || echo_failure
  done
}

function stop_asm()
{
  if [ $(homeFromInventory asm | wc -l) -eq 0 ]; then
    echo_head "No asm installed..." && echo_passed
    return 0
  fi
  if [ $(ps -ef | grep -c [o]ra_pmon) -ne 0 ]; then
    echo_head "Stopping DB's before stopping ASM"
    stop_dbs
    if [ $(ps -ef | grep -c [o]ra_pmon) -ne 0 ]; then 
      echo_success
    else
      echo_failure
      return 1
    fi
  fi

  for inst in $(running_instances ASM)
  do
    echo_head "Stopping $inst"
    run_sql $inst "shutdown immediate;" && echo_success || echo_failure
  done
}

function start_dbs()
{
  insts=`local_instances DB`

  echo_head "Mounting databases"
  if [ $(homeFromInventory oradb | wc -l) -eq 0 ]; then
    echo_passed "No DB Home installed on this server"
  elif [ "$insts" = "" ]; then
    echo_passed "No DB's registered in oratab"
  else
    for inst in $insts
    do
      [ $(ps -ef | grep -i ${inst} | grep -ic [p]mon) -eq 0 ] && run_sql ${inst} 'startup mount;' 2>&1 | oraLogger &
    done
    wait
    echo_success

    echo_head "Opening databases"
    for inst in $insts
    do
      [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -eq 0 ] && continue
      STBY=$(run_sql ${inst} 'select database_role from v$database;' 2>/dev/null| grep -ic STANDBY)
      if [ $STBY -gt 0 ]; then
        run_sql $inst 'ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT;' 2>&1 | oraLogger &
      else
        run_sql $inst 'ALTER DATABASE OPEN;' 2>&1 | oraLogger &
      fi
    done
    wait
    echo_success

    echo_head "Checking databases"; echo
    for inst in $insts
    do
      echo_head "Checking database ${inst}"
      if [ $(ps -ef | grep -c [o]ra_pmon_${inst}) -eq 0 ]; then
        echo_failure "Not running"
      else
        CHECK=$(run_sql ${inst} "SELECT count(*) FROM V\$ARCHIVE_DEST_STATUS where status <> 'INACTIVE' and TYPE = 'LOCAL' AND DATABASE_MODE <> 'OPEN' AND RECOVERY_MODE <> 'MANAGED REAL TIME APPLY';" 2>/dev/null )
        [ "${CHECK}0" -gt 0 ] && echo_failure "Recover not enabled, or database not properly opened" || echo_success
      fi
    done
  fi
  start_listener
}

function stop_dbs()
{
  stop_listener
  insts=`local_instances DB`
  
  if [ `homeFromInventory oradb | wc -l` -eq 0 ]; then
    echo_passed "No DB Home installed on this server"
  elif [ "$insts" = "" ]; then
    echo_failure "No DB's registered in oratab"
  else
    echo_head "Stopping databases"; echo
    echo "Stopping recover for Standby databases;" | oraLogger
    for inst in $insts
    do
      if [ `ps -ef | grep -i $inst | grep -i pmon | wc -l` -ne 0 ]; then
        STBY=$(run_sql $inst 'select database_role from v$database;' | grep -ic STANDBY)
        [ $STBY -gt 0 ] && run_sql $inst 'ALTER DATABASE RECOVER MANAGED STANDBY DATABASE CANCEL;' >/dev/null 2>&1 &
      fi
    done
    wait

    for inst in $insts
    do
      [ `ps -ef | grep -i $inst | grep -i pmon | wc -l` -ne 0 ] && run_sql $inst 'shutdown immediate;' >/dev/null 2>&1 &
    done
    wait

    for inst in $insts
    do
      [ `ps -ef | grep -i $inst | grep -i pmon | wc -l` -ne 0 ] && run_sql $inst 'shutdown abort;' >/dev/null 2>&1 &
    done
    wait

    for inst in $insts
    do
      echo_head "Shutdown DB $inst"
      [ `ps -ef | grep -i $inst | grep -i pmon | wc -l` -eq 0 ] && echo_success || echo_failure
    done
  fi
}

function stop_listener()
{
  for lsnr in `ps -ef | awk '$8~/tnslsnr$/{print $8":"$9}'`
  do
    APPHOME=`echo $lsnr | cut -d: -f1`; APPHOME=`dirname $APPHOME`; export ORACLE_HOME=`dirname $APPHOME`
    lsnr=`echo $lsnr | cut -d: -f2`
    echo_head Stopping listener $lsnr
    timeout -t 10 $APPHOME/lsnrctl stop $lsnr 2>&1 | oraLogger
    if [ `ps -ef | grep "$APPHOME/tnslsnr" | grep -vc grep` -eq 0 ]; then
      echo_success
    else
      killByPath $APPHOME/tnslsnr
      sleep 1
      [ `ps -ef | grep "$APPHOME/tnslsnr" | grep -vc grep` -eq 0 ] && echo_warning || echo_failure
    fi
  done
}

function start_listener()
{
  [ `homeFromInventory oradb | wc -l` -eq 0 ] && return 0
  LSNR_HOMES="$ASM_HOME /u01/app/oracle/product/11.2.0/db_1 /u01/app/oracle/product/10.2.0/db_1 `homeFromInventory oradb | grep '/u01/app/oracle/product' | sort -r`"
  if [ -f $TNS_ADMIN/listener.ora ]; then
#    lsnr="LISTENER_`hostname | tr '[:lower:]' '[:upper:]'`"
    lsnr=`awk 'BEGIN{FS="="}$1~/^LISTENER_/{print $1}' $TNS_ADMIN/listener.ora | head -n 1`
  fi
  [ ! $lsnr ] && lsnr="LISTENER"

  #Om te voorkomen dat het subproces /stage bezet houdt.
  cd /
  for APPHOME in $LSNR_HOMES
  do
    if [ -f $APPHOME/bin/lsnrctl ]; then
      export ORACLE_HOME=$APPHOME
      echo_head "Starting listener"
      if [ `ps -ef | grep -v grep | grep -c "$APPHOME/bin/tnslsnr $lsnr"` -eq 0 ]; then
        stop_listener
        $ORACLE_HOME/bin/lsnrctl start $lsnr 2>&1 | oraLogger
        [ ${PIPESTATUS[0]} -eq 0 ] && echo_success "$lsnr from $APPHOME" || echo_failure "$lsnr from $APPHOME"
      else
        echo_passed "Listener $lsnr from $APPHOME was allready running."
      fi
      break
    fi
  done
}

function show_dbs()
{
  if [ ! "`homeFromInventory oradb`" ]; then
    echo_head "No databases installed on this server"
    echo_success
  elif [ ! "`local_instances DB`" ]; then
    echo_head "No $insttype registered in oratab"
    echo_passed
  else
    echo "Instance(s):" | oraLoggerWithOutput
    echo "-----------------------------------------------------------------------------" | oraLoggerWithOutput
    local_instances DB | while read inst
    do
      dbs=${inst:0:5}
      if [ `ps -ef | grep -i ${inst} | grep -i pmon | wc -l` -gt 0 ]; then
        echo "Database: $dbs" | oraLoggerWithOutput
        echo "-----------------------------------------------------------------------------" | oraLoggerWithOutput
        if [ $CRS_HOME ]; then
          $CRS_HOME/bin/srvctl status database -d $dbs | oraLoggerWithOutput
        else
          echo_head "Instance $inst is "
          [ `ps -ef | grep -c '[p]mon_'$inst` -eq 0 ] && echo_head "not running" || echo "running on node `hostname`"
        fi
      fi
    done
    echo "-----------------------------------------------------------------------------" | oraLoggerWithOutput
    echo | oraLoggerWithOutput
  fi
}

function show_services()
{
  if [ "$CRS_HOME" -a "`homeFromInventory oradb`" ]; then
    echo "Services per database:" | oraLoggerWithOutput
    echo "-----------------------------------------------------------------------------" | oraLoggerWithOutput
    local_instances DB | while read inst
    do
      dbs=${inst:0:5}
      if [ `ps -ef | grep -i ${inst} | grep -i pmon | wc -l` -gt 0 ]; then
        echo "Database: $dbs" | oraLoggerWithOutput
        echo | oraLoggerWithOutput
        $CRS_HOME/bin/srvctl status service -d $dbs | oraLoggerWithOutput
        echo
      fi
    done
    echo "-----------------------------------------------------------------------------" | oraLoggerWithOutput
  fi
}

function start_services()
{
  if [ "$CRS_HOME" ]; then
    if [ `homeFromInventory oradb | wc -l` -eq 0 ]; then
      echo_head No databases installed on this server
      echo_success
    else
      echo Repositioning local services
      for inst in `local_instances DB`
      do
        dbs=${inst:0:5}
        ShouldHave=`$CRS_HOME/bin/srvctl config service -d $dbs | awk 'BEGIN{FS=":"}{gsub("PREF:",":");gsub("AVAIL:",":");gsub(" ","",$1);split($2,a," ");for (x in a) print $1":"a[x]}' | sort`
        Having=`$CRS_HOME/bin/srvctl status service -d $dbs | awk '{i=split($0,a);while (i>=7) {gsub(",","",a[i]);print $2":"a[i];i=i-1}}' | sort`
        for Have in $Having
        do
          if [ `echo "$ShouldHave" | xargs -n 1 | grep -c "$Have"` -eq 0 ]; then
            NowHaving="$NowHaving $Have"
          else
            ShouldHave=`echo $ShouldHave | xargs -n1 | grep -v "$Have"`
          fi
        done
        ShouldHave=`echo $ShouldHave | xargs -n 1 | grep "$inst"`
        for Should in $ShouldHave
        do
          if [ `echo $NowHaving | xargs -n 1 | grep -c $Should` -eq 0 ]; then
            srvname=`echo $Should | cut -d":" -f1`
            old=`echo $NowHaving | xargs -n 1 | grep $srvname | head -n1 | cut -d":" -f2`
            echo "Service $srvname should be running on this server, but is not." | oraLogger
            echo_head "Relocating $srvname:$old to $srvname:$inst"
            $CRS_HOME/bin/srvctl relocate service -d $dbs -s $srvname -i $old -t $inst 2>&1 | oraLogger 
            [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_warning
          else
            echo "Service $Should is running on this server (`echo $Having | xargs -n 1 | grep $Should:$inst`)" | oraLogger
          fi
        done
      done
    fi
  fi
}

function stop_owbb()
{
  for APPHOME in `homeFromOratab wb`
  do
    if [ -x $APPHOME/owb/bin/unix/stopOWBBInst.sh ]; then
      echo_head Stopping OWB Browser ${APPHOME}
      cd $APPHOME/owb/bin/unix/
      ./stopOWBBInst.sh 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_warning
    else
      echo_head Could not stop OWB Browser ${APPHOME}
      echo_warning
      echo File $APPHOME/owb/bin/unix/stopOWBBInst.sh does not exist, or is not executable
    fi
  done
}

function start_owbb()
{
  for APPHOME in `homeFromOratab wb`
  do
    if [ -x $APPHOME/owb/bin/unix/startOwbbInst.sh ]; then
      echo_head Starting OWB Browser ${APPHOME}
      cd $APPHOME/owb/bin/unix/
      nohup ./startOwbbInst.sh 2>&1 | oraLogger &
      echo_success
    else
      echo_head Could not start OWB Browser ${APPHOME}
      echo_warning
      echo File $APPHOME/owb/bin/unix/startOwbbInst.sh does not exist, or is not executable
    fi
  done
}

function show_crs_enabled()
{
  if [ $CRS_HOME ]; then
    [ -f /etc/init.d/ohasd ] && return 0  #Niet van toepassing voor ohasd service
    crsstartfile=/etc/oracle/scls_scr/`hostname | tr '[:upper:]' '[:lower:]'`/root/crsstart
    [ -f $crsstartfile ] && echo `cat $crsstartfile`d || echo File not found: $crsstartfile
  fi
}

function enable_crs()
{
  if [ $CRS_HOME ]; then
    echo_head "Enabling CRS autostart after reboot."
    if [ -f /etc/init.d/ohasd ]; then
      echo_passed
      echo "Niet mogelijk voor /etc/init.d/ohasd"
      return 0
    elif [ -f /etc/init.d/init.crs ]; then
      sudo /etc/init.d/init.crs enable 2>&1 | oraLogger
    else
      echo_failure "init script was not found in /etc/init.d".
      return 1
    fi
    [ `show_crs_enabled` = "enabled" ] && echo_success || echo_failure
  fi
}

function disable_crs()
{
  if [ $CRS_HOME ]; then
    echo_head "Disabling CRS autostart after reboot."
    if [ -f /etc/init.d/ohasd ]; then
      echo_passed
      echo "Niet mogelijk voor /etc/init.d/ohasd"
      return 0
    elif [ -f /etc/init.d/init.crs ]; then
      sudo /etc/init.d/init.crs disable 2>&1 | oraLogger
    else
      echo_failure "init script was not found in /etc/init.d".
      return 1
    fi

    [ "`show_crs_enabled`" = "disabled" ] && echo_success || echo_failure
  fi
}

function stop_crs()
{
  echo_head Stopping CRS
  if [ $CRS_HOME ]; then
    if [ -f /etc/init.d/ohasd ]; then
      sudo /etc/init.d/ohasd stop 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
    elif [ -f /etc/init.d/init.crs ]; then
      sudo /etc/init.d/init.crs stop 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
    else
      echo_failure "init script was not found in /etc/init.d".
      return 1
    fi
    if [ -d $CRS_HOME ]
    then
      echo_head Waiting for CRS to stop
      for (( i = 1; i <=120 ; i++ ))
      do
        NumProcs=`ps -ef | grep -v grep | grep -c $CRS_HOME`
        [ $NumProcs -eq 0 ] && break
	sleep 1
      done
      [ $NumProcs -eq 0 ] && echo_success || echo_failure
    else
      echo_head "CRS missing in /etc/oratab. Waiting 120 seconden (default)."
      sleep 120
      echo_success
    fi
  else
    echo_passed "This is not a cluster node"
  fi
}

function start_crs()
{
  [ $1 ] && maxDur=$1 || maxDur=300
  #starttijd in seconden sinds 1-1-1970 (epoch) 
  StartEpoch=`date +%s`
  echo_head Starting CRS
  if [ ! $CRS_HOME ]; then
    echo_passed
    echo "This is not a cluster node"
    return 0
  fi

  #Checken of CRS al online is
  Offline=`show_crs 2>/dev/null | awk 'BEGIN{a=0}END{print a}$3~/OFFLINE/{a+=1}'`
  if [ `ps -ef | grep -v grep | grep -c $CRS_HOME/bin/crsd.bin` -eq 0 ]; then
    if [ -f /etc/init.d/ohasd ]; then
      sudo /etc/init.d/ohasd start 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
    elif [ -f /etc/init.d/init.crs ]; then
      sudo /etc/init.d/init.crs start 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
    else
      echo_failure "init script was not found in /etc/init.d".
      return 1
    fi

    #CRS is nog niet gestart. Met de hand starten...
    echo_head Waiting for crsd.bin to start
    #Max $maxDur sec. sinds begin start_crs
    while [ $((`date +%s` - $StartEpoch)) -lt $maxDur ]
    do
      [ `ps -ef | grep -v grep | grep -c $CRS_HOME/bin/crsd.bin` -gt 0 ] && break
      sleep 1
    done
    [ $((`date +%s` - $StartEpoch)) -lt $maxDur ] && echo_success || echo_failure

    echo_head Waiting for CRS to come online
    Started=1
    while [ $((`date +%s` - $StartEpoch)) -lt $maxDur ]
    do
      $CRS_HOME/bin/crsctl check crsd 2>&1 | oraLogger
      Started=${PIPESTATUS[0]}
      [ $Started -eq 0 ] && break
      sleep 1
    done
    [ "$Started" -eq 0 ] && echo_success || echo_failure
  else
    echo_passed
    echo CRS is already running
    #als CRS al gestart was, dan de services starten 
    echo_head Starting CRS services
    $CRS_HOME/bin/crs_start -all 2>&1 | oraLogger
    echo_success
  fi

  echo_head Waiting for local Resources to come online
  for inst in `local_instances DB`
  do
    dbs=${inst:0:5}
    ShouldHaves="$ShouldHaves `$CRS_HOME/bin/srvctl config service -d $dbs | awk 'BEGIN{FS=":";ORS=" "}$1~/PREF/&&$2$3~/'$inst'/{split($1,a," ");print "ora.'$dbs'."a[1]".cs"}/Service name: /{gsub(/ /,"",$2);s=$2}/Preferred instances: /&&$2~/'$inst'/{print "ora.'$dbs'."s".svc"}'`"
  done
  ShouldHaves="$ShouldHaves `$CRS_HOME/bin/crs_stat | awk 'BEGIN{IGNORECASE=1;FS="=";ORS=" "}$1~/NAME/&&$2~/ora.'$(hostname)'/{print $2}'`"
  while [ $((`date +%s` - $StartEpoch)) -lt $maxDur ]
  do
    unset MIA
    Online=`show_crs | awk 'BEGIN{ORS=" "}$3~/ONLINE/{print $1}'`
    for ShouldHave in $ShouldHaves
    do
      [ `echo $Online | grep -i -c -E "$ShouldHave"` -eq 0 ] && MIA="$MIA $ShouldHave"
    done
    [ ! "$MIA" ] && break
    sleep 1
  done
  if [ "$MIA" ]; then
    echo_failure
  elif [ `show_crs | awk 'BEGIN{a=0}END{print a}$3~/OFFLINE/{a+=1}'` -gt 0 ]; then
    echo_warning
    echo There are offline services
  else
    echo_success
  fi
}

function show_crs()
{
  [ ! $CRS_HOME ] && return 0

  awk 'BEGIN {printf "%-45s %-10s %-18s\n", "HA Resource", "Target", "State";
          printf "%-45s %-10s %-18s\n", "-----------", "------", "-----";}'

  $CRS_HOME/bin/crs_stat -u | awk \
 'BEGIN { FS="="; state = 0; }
  $1~/NAME/ {appname = $2; state=1};
  state == 0 {next;}
  $1~/TARGET/ && state == 1 {apptarget = $2; state=2;}
  $1~/STATE/ && state == 2 {appstate = $2; state=3;}
  state == 3 {printf "%-45s %-10s %-18s\n", appname, apptarget, appstate; state=0;}'
}

function show_final_checks()
{
  echo
  echo Final checks
  echo
  ps -ef | grep oracle | grep -v agent10g | grep -iv TZ | grep -v crs_mgt.sh
}

function show_pmon()
{
  [ `homeFromInventory oradb | wc -l` -eq 0 ] && return 0
  echo
  echo Show PMON info
  echo
  ps -ef | grep pmon | grep -v grep
}

function start_oas()
{
  [ $1 ] && type="$1"_ || type="mt"_
  for APPHOME in `homeFromInventory $type`
  do
    export ORACLE_INSTANCE=$APPHOME
    echo_head Starting AS ${APPHOME}
    if [ -x $APPHOME/opmn/bin/opmnctl ]; then
      timeout -t 60 $APPHOME/opmn/bin/opmnctl startall 2>&1 | oraLogger
      echo "$APPHOME/opmn/bin/opmnctl status -l" | oraLogger
      $APPHOME/opmn/bin/opmnctl status -l 2>&1 | oraLogger
      [ `$APPHOME/opmn/bin/opmnctl status | awk 'BEGIN{FS="|";a=0}END{print a}$4!~/Down/{$0=""}$2~/OC4J:/{a+=1}$1~/OID/{a+=1}'` -eq 0 ] && echo_success || echo_failure
    else
      echo_failure
      echo ${APPHOME}/opmn/bin/opmnctl does not exist
    fi

    echo_head Starting iasconsole ${APPHOME}
    if [ -x $APPHOME/bin/emctl ]; then
      unset CONSOLE_CFG
      unset EMSTATE
      timeout -t 60 $APPHOME/bin/emctl start iasconsole 2>&1 | oraLogger
      $APPHOME/bin/emctl status iasconsole | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_warning
    else
      echo_passed "${APPHOME}/bin/emctl does not exist"
    fi
  done
}

function show_oas()
{
  [ $1 ] && type="$1"_ || type="mt"_
  for APPHOME in `homeFromInventory $type`
  do
    export ORACLE_INSTANCE=$APPHOME
    if [ -x $APPHOME/opmn/bin/opmnctl ]; then
      echo "$APPHOME/opmn/bin/opmnctl status -l" | oraLogger
      $APPHOME/opmn/bin/opmnctl status -l 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] || "echo $APPHOME/opmn/bin/opmnctl is not up" | oraLogger
    else
      echo_head AS ${APPHOME} has no opmnctl 
      echo_failure
    fi

    if [ -x $APPHOME/bin/emctl ]; then
      echo "$APPHOME/bin/emctl status iasconsole" | oraLogger
      $APPHOME/bin/emctl status iasconsole 2>&1 | oraLogger
    else
      echo_head ${APPHOME}/bin/emctl does not exist
      echo_passed
    fi
  done
}

function stop_oas()
{
  case "$1" in
  "oms") type="oms";;
  "") type="mt_";;
  *) type="$1"_;;
  esac

  for APPHOME in `homeFromInventory $type`
  do
    [ `ps -ef | grep -v grep | grep -c $APPHOME` -eq 0 ] && continue
    echo "$APPHOME/opmn/bin/opmnctl status -l" | oraLogger
    timeout -t 30 $APPHOME/opmn/bin/opmnctl status -l 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] || echo "$APPHOME/opmn/bin/opmnctl is not up" | oraLogger

    echo_head "Stopping AS $APPHOME"
    timeout -t 30 $APPHOME/opmn/bin/opmnctl stopall 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_warning

    if [ -x $APPHOME/bin/emctl ]; then
      echo "${APPHOME}/bin/emctl status iasconsole" | oraLogger
      timeout -t 30 $APPHOME/bin/emctl status iasconsole 2>&1 | oraLogger

      unset CONSOLE_CFG
      unset EMSTATE
      echo_head Stopping iasconsole ${APPHOME}
      timeout -t 30 $APPHOME/bin/emctl stop iasconsole 2>&1 | oraLogger
      [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_warning
      killByPath $APPHOME
    else
      echo_head ${APPHOME}/bin/emctl does not exist
      echo_passed
    fi
    killByPath $APPHOME
  done
}

function start_im()
{
  start_oas im
}

function show_im()
{
  show_oas im
}

function stop_im()
{
  stop_oas im
}

function status()
{
  echo "Status overview `uname -n`"
  echo "----------------------------"
  echo "`/stage/oracle/scripts/bash/serverinfo.sh`"
  [ -f $CRS_HOME/bin/cemutlo ] && echo "Cluster (`$CRS_HOME/bin/cemutlo -n`) consisting of nodes: `$CRS_HOME/bin/olsnodes | sort | xargs`"
  [ -f $CRS_HOME/bin/srvctl ] && echo "Databases: `$CRS_HOME/bin/srvctl config | sort | xargs`"
  [ -x $CRS_HOME/bin/ocrcheck ] && echo "OCR: `$CRS_HOME/bin/ocrcheck | grep /dev | cut -d: -f2 | xargs`"
  [ -x $CRS_HOME/bin/crsctl ] &&  echo "Votedisks: `$CRS_HOME/bin/crsctl query css votedisk | awk '/raw/{print $3}' | xargs`"

  PMON=`ps -ef | grep pmon | grep -v grep | cut -d_ -f3 | sort | xargs`
  [ "$PMON" ] && echo "Running Instances (PMON): $PMON"

  for tab in `grep -v '^#' /etc/oratab | awk 'BEGIN{FS=":"}$1~/D[0-9][0-9][0-9]/{$0=""}/:/ {split($0,a,"#") ; print a[1]}' | sort`
  do
    ID="`echo $tab | cut -d: -f1`"
    ORAPATH=`echo $tab | cut -d: -f2`
    AUTOSTART=`echo $tab | cut -d: -f3`
    if [ "$ID" = "ag11g" ]; then
      if [ -x $ORAPATH/bin/emctl ]; then
        AGPID=`ps -ef | grep $ORAPATH/bin/emagent | grep -v grep | awk '{print $2}'`
        [ "$AGPID" ] && echo "Agent is running (PID:$AGPID)" || echo "Agent is not running"
      fi
    else
      Count=`ps -ef | grep "$ORAPATH" | grep -c -v grep`
      if [ $Count -eq 0 ]; then
        echo_head "$ID has no processes running."
        echo_warning
      elif [ -x $ORAPATH/opmn/bin/opmnctl ]; then
        alive=""
        down=""
        for line in `$ORAPATH/opmn/bin/opmnctl status | awk 'BEGIN {FS="|";OFS=",";x=1};{gsub(/^[ \t]+|[ \t]+$/,"",$1);gsub(/^[ \t]+|[ \t]+$/,"",$2);gsub(/^[ \t]+|[ \t]+$/,"",$4)};{if(x>5) print $1,$2,$4}; {x++}'`
        do
          iasComp=`echo "$line" | cut -d, -f1`
          processType=`echo "$line" | cut -d, -f2`
          status=`echo "$line" | cut -d, -f3`
          [ "$iasComp" = "$processType" ] && unset iasComp || iasComp="("$iasComp")"
          [ "$status"="Alive" ] && alive="$alive $processType$iasComp" || down="$down $processType$iasComp"
        done
        if [ "$alive" ]; then
          echo_head "$ID has the following running processes:"
          echo_success
          echo $alive
        fi
        if [ "$down" ]; then
          echo_head "$ID has the following NOT running processes:$down"
          echo_warning
          echo $down
        fi
      else
        echo "$ID has $Count processes runnning."
      fi
    fi
  done

  echoed=0
  for dir in `find /u01/app/oracle/product -maxdepth 2 -mindepth 2`
  do
    if [ `grep -v '^#' /etc/oratab | grep -c "$dir"` -eq 0 ]; then
      if [ $echoed -eq 0 ]; then
        echo_head Folders not in oratab
        echo_warning
        echoed=1
      fi
      echo $dir 
    fi
  done

  echo
  echoed=0

  for dir in `grep -v '^#' /etc/oratab | awk '/:/ {split($0,a,"#") ; split(a[1],p,":") ; print p[2]}' | sort -u`
  do
    if [ ! -d $dir ]; then
      if [ $echoed -eq 0 ]; then
        echo_head "Entry in oratab does't exist"
        echo_warning
        echoed=1
      fi
      echo $dir
    fi
  done
}

function stop()
{
  show_clustername | oraLogger
  show_nodes | oraLogger
  show_dbs 3>/dev/null
  show_services | oraLogger
  start_autoblackout
  stop_oms
  stop_owbb
  stop_oas
  stop_im
  stop_cman
  stop_crs
  stop_dbs
  stop_asm
  disable_crs
  show_final_checks | oraLoggerWithOutput
  if [ ! "$failures" ]; then
    sudo /sbin/chkconfig oracle off
    patchlist_app_down
  fi
}

function stop_service()
{
  start_autoblackout
  stop_oms
  stop_owbb
  stop_oas
  stop_im
  stop_cman
  if [ $CRS_HOME ]; then
    stop_crs
  else
    stop_dbs
    stop_asm
  fi
#  [ ! "$failures" ] && patchlist_app_down
}

function start()
{
  show_asmlib
  if [ $? -eq 0 ]; then
    start_crs
    start_asm
    start_dbs
    show_clustername | oraLogger
    show_stats | oraLoggerWithOutput
    show_nodes | oraLogger
    show_dbs
    show_services | oraLogger
  fi
  start_cman
  start_im
  start_oas
  start_owbb
  start_oms
  show_oas | oraLogger
  start_services 
  show_pmon | oraLoggerWithOutput
  if [ ! "$failures" ]; then
    sudo /sbin/chkconfig oracle on
    stop_autoblackout
    patchlist_app_up
  else
    echo "Failures:$failures" | oraLogger
  fi
  
}

function start_service()
{
  show_asmlib
  if [ $? -eq 0 ]; then
    if [ $CRS_HOME ]; then
      start_crs 480
    else
      start_asm
      start_dbs
    fi
  fi
  start_cman
  start_im
  start_oas
  start_owbb
  start_oms
  start_services 
  if [ ! "$failures" ]; then
    stop_autoblackout
#    patchlist_app_up
  fi

}

function restart()
{
  stop
  start
}

function help()
{
  echo "Server Management script Release 1.2.1.0"
  echo
  echo "Copyright (c) 2011. No Rights Reserved."
  echo
  echo "Usage 1: $0 help"
  echo " will display this information"
  echo "Usage 2: crs_mgt.sh option_1 option_2 ... option_n"
  echo " will process the options one by one in the order in which they are specified."
  echo " Multiple options can be specified in which crs_mgt.sh will process them in the order in which they are specified."
  echo " The given options can be one of the following:"
  echo " - start: Will start all there is to start (CRS, ASM, DB's, oas, owbb, etc), but not the agent (use start_agent start if needed)."
  echo "   '$0 start' is equivalent to 'crs_mgt.sh start_crs show_stats start_oas start_im start_owbb start_services show_pmon stop_autoblackout',"
  echo "   except that 'start' will provide extra logging in '/tmp/`basename $0 .sh`_start.log'."
  echo " - stop: Will stop anything there is to stop (CRS, ASM, DB's, oas, owbb, etc), but not the agent (use stop stop_agent if needed)."
  echo "   '$0 stop' is equivalent to 'start_autoblackout stop_owbb stop_oas stop_im stop_crs disable_crs show_final_checks',"
  echo "   except that 'stop' will provide extra logging in '/tmp/`basename $0 .sh`_stop.log'."
  echo " - status: Will show some general status info on the cluster, machine, processes, oratab, etc."
  echo " - restart: Will restart the stack. It is equivalent to 'crs_mgt.sh stop start'."
  echo " - show_pmon, show_final_checks, show_clustername, show_dbs, show_instances, show_nodes, show_services, show_stats, show_crs_enabled"
  echo "   Will show information on the given subject."
  echo " - start_autoblackout, stop_autoblackout, show_blackout: Will set or unset a autoblackout, or give blackout info."
  echo " - patchlist_app_up, patchlist_app_down: Will set app_up or app_down on the patchlist."
  echo " - start_dbs, stop_dbs, show_dbs: Will start, stop or give info on local running databases."
  echo " - start_asm, stop_asm: Wil start or stop ASM."
  echo " - show_asmlib: Will check if ASMLib is installed and succesfully loaded."
  echo " - start_listener, stop_listener: Will start or stop the listener."
  echo " - start_crs, stop_crs, show_crs: Will start or stop the CRS stack, or show info (crsstat)."
  echo " - start_im, stop_im, show_im: Will start or stop the OID, or give info on OID.."
  echo " - start_cman, stop_cman, show_cman: Will start, stop or  give info on CMAN."
  echo " - start_oas, stop_oas, show_oas: Will start, stop or give info on all the Application Servers."
  echo " - start_owbb, stop_owbb: Will start or stop OWB (untested)."
  echo " - start_oms, stop_oms, show_oms: Will start or stop OMS (Grid Control)."
  echo " - start_agent, stop_agent: Will start or stop oracle agent (Grid Control)."

  echo " - enable_crs, disable_crs, show_crs_enabled: Will enable, disable or show status of autostart of the CRS stack on change of init level (like boot, reboot, etc.)."
  echo " - start_services: Will restart all services that should run locally but are not."
  echo
}

if [ $(whoami) != 'oracle' ]; then
  sudo -u oracle "$0" $@
  exit
fi

# Start of the main part
[ -f "/home/oracle/bin/crs_mgt_new.sh" ] && rm -f /home/oracle/bin/crs_mgt_new.sh
if [ $# -eq 0 -o `echo $* | grep -c "help"` -gt 0 ]; then
  help
  exit 0
fi

tmpfile=$(mktemp)
logfile=/tmp/`basename $0 .sh`.log
LIB=$(dirname $0)/oralib
[ -f "$LIB" ] || LIB=/usr/local/bin/oralib
[ -f "$LIB" ] || LIB=/stage/oracle/scripts/bash/oralib
echo "oralib: $LIB" > "$tmpfile"
. "$LIB" >> "$tmpfile"
cat "$tmpfile" | oraLogger
rm $tmpfile

for parm in $*
do
  unset isdone
  for cmd in `help | awk 'BEGIN {FS=":"} /^ - / {split(substr($1,4),a,",");for (e in a) {sub(/^[ \t]*/, "",a[e]) ; print a[e]}}' | sort -u ; echo "start_service stop_service"`
  do
    if [ "$parm" = "$cmd" ]; then
      logfile=/tmp/`basename $0 .sh`_$cmd.log
      $cmd 3>&2
      isdone=1
    fi
  done
  if [ ! $isdone ]; then
    echo_head "Illegal command $parm."
    echo_failure
    help
    exit 1
  fi
done

[ ! $failures ] || exit 1
