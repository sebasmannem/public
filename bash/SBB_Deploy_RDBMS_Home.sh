#!/bin/bash

function usage()
{
  cat << EOF
  usage: $0 options

  Dit script wordt gebruikt om een Oracle RDBMS Home te installeren.
  Standaard zoekt het script zelf de meest recente versies van PSU en patchsets.
  Het is mogelijk om in plaats daarvan een specifieke versie en/of psu te kiezen.
  Het is niet mogelijk om 'geen' psu te kiezen, maar wel om de installatie af te breken voor installatie van psu (maar niet unattended).
  Het script gaat uit van de 11.2 methode (Direct PSU installatie en niet eerst base).

  OPTIONS:
     -h          toont dit helpscherm
     -stage      Stage locatie                   (default /stage/oracle/software/RDBMS/{x86|x86_64}
     -base       Base version                    (default laatste in Stage, e.a. 11.2)
     -ps         Patch set                       (default laatste in Base loc, e.a. 11.2.0.4)
     -psu        PSU nummer                      (default standaard: laatste in [ps_loc]/psu, e.a. 19769489 ; zonder psu is geen optie)
     -ojvm_psu   OJVM_PSU nummer                 (default standaard: laatste in [ps_loc]/ojvm_psu, e.a. 21068539 ; zonder ojvm_psu is geen optie)
     -opatch     Opatch locatie                  (default /stage/oracle/software/OPATCH/{x86|x86_64}/[base]/OPatch/opatch
     -unattended voor script-integratie          (default uit ; base/ps/psu wordt dan fixed naar 11.2.0.3.10 = 19769489)
     -companion  Installeerd de CompanionCD mee  (default uit ; alleen bedoeld voor RDBMS 10g installaties voor OID's)
        
     -x          debug mode                      (default uit)

     overige opties zijn niet toegestaan.

  Voorbeelden:
  - 11g standaard home:
    $0 -unattended
  - 10gOID
    $0 -base 10.2 -ps 10.2.0.5 -psu 16056270 -companion

EOF
  exit 0
}

  while [ -n "$1" ]; do
  case $1 in
    -h) usage; exit 0 ;;
    -stage) STAGE=$2 ; shift 2 ;;
    -base) BASE=$2 ; shift 2 ;;
    -ps) PS=$2 ; shift 2 ;;
    -psu) PSU=$2 ; shift 2;;
    -ojvm_psu) OJVM_PSU=$2 ; shift 2;;
    -opatch) OPATCH=$2 ; shift 2 ;;
    -unattended) UNATTENDED=$1 ; shift 1 ;;
    -companion) COMPANIONCD=$1 ; shift 1 ;;
    -x) set -vx ; shift 1 ;;
    -*) echo "error: no such option $1" ; exit 1 ;;
    *) echo "cannot specify $1" ; exit 1 ;;
#    *)  DBs=$@ ; break ;;
  esac
  done

  if [ $UNATTENDED ]; then
    BASE=11.2
    PS=11.2.0.4
    PSU=23054359
    OJVM_PSU=23177551
  fi

  [ $STAGE ] || STAGE="/stage/oracle/software/RDBMS/"$(uname -m)
  [ $BASE ] || BASE=$(ls -d -p "$STAGE/"* | awk '/\/$/{split($0,a,"/");print a[length(a)-1]}' | tail -n1)
  [ $PS ] || PS=$(ls -d -p "$STAGE/$BASE/$BASE"* | awk '/\/$/{split($0,a,"/");print a[length(a)-1]}' | tail -n1)
  [ $PSU ] || PSU=$(ls -d -p "$STAGE/$BASE/$PS/psu/"* | awk '/\/[0-9]+\/$/{split($0,a,"/");print a[length(a)-1]}' | tail -n1)
  [ $OJVM_PSU ] || OJVM_PSU=$(ls -d -p "$STAGE/$BASE/$PS/ojvm_psu/"* | awk '/\/[0-9]+\/$/{split($0,a,"/");print a[length(a)-1]}' | tail -n1)
  [ $OPATCH ] || OPATCH=/stage/oracle/software/OPATCH/$(uname -m)/$BASE/OPatch/opatch

  if [ $(whoami) != 'root' ]; then
    sudo -E "$0" -stage "$STAGE" -base "$BASE" -ps "$PS" -psu "$PSU" -opatch "$OPATCH" $UNATTENDED $COMPANIONCD
    exit
  fi

  tmpfile=$(mktemp)
  logfile=$tmpfile
  echo "$0" >> $logfile
  . /stage/oracle/scripts/bash/oralib >> /dev/null
  export TNS_ADMIN=/u01/app/oracle/admin/network

  echo_head "Checking for paths:"
  BASE_LOC="$STAGE/$BASE/"$(echo $PS|sed 's/[0-9]$/1/')
  PS_LOC="$STAGE/$BASE/$PS"
  PSU_LOC="$PS_LOC/psu/$PSU"
  ONEOFF_LOC="$PS_LOC/oneoff"
  OJVM_PSU_LOC="$PS_LOC/ojvm_psu/$OJVM_PSU"
  PSU_VERSION=$(awk 'BEGIN{FS="content=\""}END{print NUM,LEVEL,"("DATE")"}/<meta name="date"/{sub(/".*/,"",$2);DATE=$2}/<meta name="doctitle"/{sub(/".*/,"",$2);split($2,a," ");NUM=a[4];LEVEL=a[10]}' $PSU_LOC/README.html)
  VERSION=$(echo $PSU_VERSION | awk '$2~/\.[0-9]$/{sub(/[0-9]$/,"0&",$2)}{print $2}')
  ORACLE_HOME="/u01/app/oracle/product/$VERSION/db"
  ORACLE_HOME_NAME='OraDb_home'$(echo "$VERSION" | sed 's/\.//g')
  logfile=/tmp/$(echo "$VERSION" | sed 's/\.//g').log
  cat $tmpfile | oraLogger
  rm $tmpfile
  tnsfile="$TNS_ADMIN/tnsnames.ora"
  lsnfile="$TNS_ADMIN/listener.ora"
  sqlnetfile="$TNS_ADMIN/sqlnet.ora"
  dbsdir="/u01/app/oracle/admin/dbs"

  [ -f "$PS_LOC/base/Disk1/runInstaller" ] || quitOnError "Cannot find PatchSet installer '$PS_LOC/base/Disk1/runInstaller'."
  [ -d "$PSU_LOC" ] || quitOnError "Cannot find PSU '$PSU_LOC'."
  [ -d "$OJVM_PSU_LOC" ] || quitOnError "Cannot find OJVM_PSU '$OJVM_PSU_LOC'."
  [ -d "$ONEOFF_LOC" ] || quitOnError "Cannot find ONEOFF_PATCH '$ONEOFF_LOC'."

  echo_success
  if [ -d "$ORACLE_HOME" ]; then
    echo "Home '$ORACLE_HOME' allready exists..."
    exit 0
  fi

  [ $BASE = "10.2" ] && echo "Base: $BASE ($BASE_LOC)"
  [ $COMPANIONCD ] && echo "Companion components will be deployed too"
  echo "PatchSet: $PS ($PS_LOC)" | oraLogger
  echo "PSU: $PSU ($PSU_LOC)"    | oraLogger
  echo "Version: $VERSION"       | oraLogger
  echo "Home: $ORACLE_HOME"      | oraLogger
  echo "Opatch: $OPATCH"         | oraLogger
  echo "Logfile: $logfile"       | oraLogger
#    echo "Home_name: $ORACLE_HOME_NAME"
#    ORACLE_HOME_NAME kan niet in responsefile


## De 3 onderstaande regels uitgehekt vanwege libgcc rpm update issues
## De rpm's die in packages_db.list staan, staan ook in de satelite oracle deploymen.
#  echo_head "Workaround: Installing forgotten dependencies"
#  cat /stage/oracle/scripts/conf/packages_db.list | xargs yum install -y 2>&1 | oraLogger
#  [ ${PIPESTATUS[1]} -eq 0 ] && echo_success || quitOnError "Could not install dependencies..."

  echo
  CMD_FILE=$(mktemp)
  echo "#!/bin/sh" > "$CMD_FILE"
  if [ $BASE = "10.2" ]; then
    RSP=/tmp/Deploy$(echo "$BASE" | sed 's/\.//g')01.rsp
    RSP_TEMPLATE=/stage/oracle/scripts/rsp/$(basename "$RSP")
    echo_head "Creating responsefile $RSP"
    sed 's/ORACLE_HOSTNAME=.*/ORACLE_HOSTNAME='$(hostname -f)'/
s|ORACLE_HOME=.*|ORACLE_HOME="'$ORACLE_HOME'"|
s|HOME_PATH|'$ORACLE_HOME'|
s|CLUSTER_NODES=.*|CLUSTER_NODES={"'$(hostname -f)'"}|
s|ORACLE_HOME_NAME=.*|ORACLE_HOME_NAME="'$ORACLE_HOME_NAME'"|' $RSP_TEMPLATE > "$RSP" 2>/dev/null && echo_success "Succesfully created '$RSP' from '$RSP_TEMPLATE'" || echo_failure "Could not create '$RSP' from '$RSP_TEMPLATE'"
    chmod 666 "$RSP"
    echo "$BASE_LOC/base/Disk1/runInstaller -silent -responseFile \"$RSP\" -waitforcompletion ORACLE_HOME_NAME=\"$ORACLE_HOME_NAME\"" >> "$CMD_FILE"
  fi
  [ $COMPANIONCD ] && echo "$BASE_LOC/companion/runInstaller -silent -responsefile $BASE_LOC/companion/response/companionCD.db.rsp -waitforcompletion ORACLE_HOME_NAME=\"$ORACLE_HOME_NAME\"" >> "$CMD_FILE"

  RSP=/tmp/Deploy$(echo "$PS" | sed 's/\.//g').rsp
  RSP_TEMPLATE=/stage/oracle/scripts/rsp/$(basename $RSP)
  echo_head "Creating responsefile $RSP"
  sed 's/ORACLE_HOSTNAME=.*/ORACLE_HOSTNAME='$(hostname -f)'/
s|ORACLE_HOME=.*|ORACLE_HOME="'$ORACLE_HOME'"|
s|HOME_PATH|'$ORACLE_HOME'|
s|ORACLE_HOME_NAME=.*|ORACLE_HOME_NAME="'$ORACLE_HOME_NAME'"|' $RSP_TEMPLATE > "$RSP" 2>/dev/null && echo_success "Succesfully created '$RSP' from '$RSP_TEMPLATE'" || echo_failure "Could not create '$RSP' from '$RSP_TEMPLATE'";
  chmod 666 "$RSP"

  echo "$PS_LOC/base/Disk1/runInstaller -silent -responseFile \"$RSP\" -waitforcompletion ORACLE_HOME_NAME=\"$ORACLE_HOME_NAME\" ORACLE_HOME=\"$ORACLE_HOME\"" >> "$CMD_FILE"
  awk '{print "  "$0}' "$CMD_FILE" | oraLogger
  chmod a+x,a+r "$CMD_FILE"

  if [ ! $UNATTENDED ]; then
    echo
    echo_head "Do you want to continue (y/n)?"
    read ret
    echo "User replied $ret" | oraLogger
    [ `echo $ret | tr '[:upper:]' '[:lower:]'` = "y" ] && echo_success || exit 0
  else
    echo_head "Unattended installation" && echo_success
  fi

  echo_head "Running installers"
  sudo -u oracle "$CMD_FILE" | tee "$tmpfile" | oraLogger

#  [ $(tail -n4 $tmpfile | grep -cE '(Successfully Setup Software|The installation of Oracle Database 11g was successful.)') -gt 0 ] && echo_success || echo_failure
  [ $(grep -cE '(Successfully Setup Software|The installation of Oracle Database 11g was successful.)' "$tmpfile") -gt 0 ] && echo_success || quitOnError "Please check \"$logfile\""

  awk '/ *[0-9]\. \/u01\/app\/ora.*\.sh/{print $2}' "$tmpfile" | sort -u | while read file
  do
    echo_head "Running root script"
    "$file" -silent | oraLogger && echo_success "$file" || echo_failure "$file"
  done

  #Enable NFS if needed
#  if [ $(df /u02/oradata 2>&1 | grep -c ':/') -gt 0 ]; then
    echo_head "Enabling dNFS"
    ln -sf "$ORACLE_HOME/lib/libnfsodm11.so" "$ORACLE_HOME/lib/libodm11.so" && echo_success || echo_failure
#  fi

  #Zet alle config files en dirs goed (waaronder tnsnames.ora, listener.ora, sqlnet.ora, dbs/)
  /stage/oracle/scripts/bash/SBB_ConfigTNS.sh -home $ORACLE_HOME


  for LOC in $PSU_LOC $OJVM_PSU_LOC $(find $ONEOFF_LOC -maxdepth 1 -mindepth 1 -type d)
  do
    echo_head "OPATCH: Applying patches in dir: $LOC"
    echo "#!/bin/sh" > "$CMD_FILE"
    echo "cd \"$LOC\"" >> "$CMD_FILE"
    echo "\"$OPATCH\" apply -all_nodes -silent -oh \"$ORACLE_HOME\" -ocmrf /stage/oracle/scripts/rsp/OCM.rsp" >> "$CMD_FILE"
    awk '{print "  "$0}' "$CMD_FILE" | oraLogger
    chmod a+x,a+r "$CMD_FILE"

    sudo -u oracle "$CMD_FILE" 2>&1 | tee "$tmpfile" | oraLogger

    if [ $(grep -c 'OPatch succeeded' "$tmpfile") -gt 0 ]; then
      echo_success
    elif [ $(grep -c 'OPatch completed with warnings.' "$tmpfile") -gt 0 ]; then
      echo_warning "opatch reported warnings. Patch_dir: $LOC - Please check \"$logfile\" for more info."
      grep 'warning' "$tmpfile" | awk '{print "  "$0}'
    else
      quitOnError "opatch not succeeded and not completed with warnings. Patch_dir: $LOC - Please check \"$logfile\""
    fi

    echo_head "Cleaning tempfiles"
    rm "$tmpfile"
    rm "$CMD_FILE"
    echo_success

    echo
    echo "Deploying home finished succesfully"
  done
