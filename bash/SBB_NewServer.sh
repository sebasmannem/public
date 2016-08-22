#!/bin/bash

  if [ $(whoami) != 'root' ]; then
    sudo -E "$0"
    exit
  fi

  SCRIPT_DIR=$(dirname "$0")
  cd $SCRIPT_DIR/..
  SCRIPT_DIR=$PWD
  [ "$logfile" ] || logfile=/tmp/$(basename $0 .sh).log
  tmpfile=$(mktemp)
  . "./bash/oralib" > "$tmpfile"
  cat "$tmpfile" | oraLogger
  rm "$tmpfile"

  echo_head "Add group oinstall"
  getent group oinstall 2>&1 | oraLogger
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo_passed
  else
    /usr/sbin/groupadd -g 500 oinstall 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError
  fi

  echo_head "Add group dba"
  getent group dba 2>&1 | oraLogger
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo_passed
  else
    /usr/sbin/groupadd -g 501 dba 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError
  fi

  echo_head "Add user oracle"
  getent passwd oracle 2>&1 | oraLogger
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo_passed
  else
    /usr/sbin/useradd -u 500 -g oinstall -G dba oracle 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError
  fi

  echo_head "generate .vimrc"
  if [ -f /home/oracle/.vimrc ]; then
    echo_passed
  else
    { echo "syntax off" > /home/oracle/.vimrc; chown oracle:oinstall /home/oracle/.vimrc; } 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError
  fi

  echo_head "Add user viv_rman"
  getent passwd viv_rman 2>&1 | oraLogger
  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo_passed
  else
    /usr/sbin/useradd -u 778 -g dba -G oinstall viv_rman 2>&1 | oraLogger
    [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError
  fi

  echo_head "Add /u01/app"
  mkdir -p /u01/app 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -ne 0 ] && quitOnError
  chown oracle:oinstall /u01/app 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -ne 0 ] && quitOnError
  chmod 755 /u01/app 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "Reconfiguring sysctl if needed"
  SCRIPT_DIR=$(dirname $(dirname "$0"))
  "./python/sysctl.py" -c "./conf/sysctl.oradb.conf" -r 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "SBB_SetupShm.sh"
  ./bash/SBB_SetupShm.sh | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "SBB_Update.sh"
  ./bash/SBB_Update.sh 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "Deploying RDBMS home (if needed)"
  ./bash/SBB_Deploy_RDBMS_Home.sh -unattended 2>&1 | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "ConfigTNS"
  ./bash/SBB_ConfigTNS.sh | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo_head "SBB_SetupNFS.sh"
  ./bash/SBB_SetupNFS.sh | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || quitOnError

  echo "Finished" | oraLoggerWithOutput
exit

  echo_head "Deploy agent"
  /stage/oracle/software/AGENT/AG11101/install_agent.sh | oraLogger
  sed -i 's/^EMD_URL=/#EMD_URL=/;s/^REPOSITORY_URL=/#REPOSITORY_URL=/' /u01/app/oracle/product/11.1.0/agent11g/sysman/config/emd.properties
  echo "EMD_URL=http://$(hostname -f):1831/emd/main/" >> /u01/app/oracle/product/11.1.0/agent11g/sysman/config/emd.properties
  echo "REPOSITORY_URL=http://gc11g:4889/em/upload" >> /u01/app/oracle/product/11.1.0/agent11g/sysman/config/emd.properties
  sudo su - oracle -c "/u01/app/oracle/product/11.1.0/agent11g/bin/emctl start agent" | oraLogger
  [ ${PIPESTATUS[0]} -eq 0 ] && echo_success || echo_failure
  echo "Finished" | oraLoggerWithOutput
