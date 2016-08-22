#!/bin/sh
[ $# -eq 0 ] && SIDs=`awk 'BEGIN {IGNORECASE=1;FS=":"} {sub("#.*","",$0)}$1~/^ag/{print $1}' /etc/oratab | sort -u` || SIDs="$@"

if [ ! -f /etc/oratab ]; then
  echo "Couldn't detect agent home."
  echo "/etc/oratab does not exist. Please fix and run again."
  exit 1
fi

for SID in $SIDs
do
  echo Reconfiguring $SID:
  export ORACLE_SID=$SID
  export ORACLE_HOME=`awk 'BEGIN{FS=":"}/^#/{$0=""}$1~/^'$ORACLE_SID'$/{print $2}' /etc/oratab | head -n1`
  if [ ! $ORACLE_HOME ]; then
    echo "Couldn't detect agent home."
    echo "/etc/oratab does not contain ag entry. Please fix and run again."
    exit 1
  fi
  echo $ORACLE_HOME | grep -q 'product/10' && Version=10g
  echo $ORACLE_HOME | grep -q 'product/11' && Version=11g
  [ "$Version" ] || continue

  case $Version in
  "10g") URL="http://`hostname -f`:3872/emd/main/";;
  "11g") URL="http://`hostname -f`:1831/emd/main/";;
  *) continue;;
  esac

  if [ `awk 'BEGIN{FS="=";a=0}END{print a}$1~/^EMD_URL$/&&$2~/'$(hostname)'/{a+=1}' $ORACLE_HOME/sysman/config/emd.properties` -eq 0 ]; then
    new_file=$ORACLE_HOME/sysman/config/emd.properties_`date +%Y%m%d`
    mv $ORACLE_HOME/sysman/config/emd.properties $new_file
    sed '/^EMD_URL=/ s|=.*|='$URL'|' < $new_file > $ORACLE_HOME/sysman/config/emd.properties
  fi

  if [ `ps -ef | grep -v grep | grep -c "$ORACLE_HOME/perl/bin/perl"` -gt 0 ]; then
    #Agent still runnning. Shutting down agent"
    $ORACLE_HOME/bin/emctl stop agent
  fi

  echo '<Targets>
   <Target TYPE="host" NAME="'`hostname -f`'"/>
</Targets>' > $ORACLE_HOME/sysman/emd/targets.xml

  rm -rf $ORACLE_HOME/sysman/emd/upload/* $ORACLE_HOME/sysman/emd/state/* $ORACLE_HOME/sysman/emd/lastupld.xml 2>/dev/null
  case $Version in
  "10g") $ORACLE_HOME/bin/emctl secure agent "hillstr33tblues";;
  "11g") $ORACLE_HOME/bin/emctl secure agent "P0l1tiepet" -emdWalletSrcUrl https://gc.domain.org:4900/em;;
  *) continue;;
  esac
  $ORACLE_HOME/bin/emctl start agent
  $ORACLE_HOME/bin/emctl upload agent
  $ORACLE_HOME/bin/emctl status agent
done
