#!/bin/sh

function IP2HN() {
  IP=$1
  HN=$(nslookup "$IP" | awk 'BEGIN{FS="="}/=/{sub(/\.$/,"",$2);print $2}' | sort | head -n 1)
  echo $HN
}

function HN2IP(){
  HN=$1
  nslookup "$HN" | sed -n '/Name:/,${/^Address: /{s/.*: //;p}}'
}

function collect_host()
{
  srv=$1
  if [ $(echo "$srv" | grep -Ec '([0-9]{1,3}.){3}[0-9]{1,3}') -gt 0 ]; then
    IP="$srv"
    srv=$(IP2HN "$srv")
    [ "$srv" ] || srv=$IP
  else
    IP=$(HN2IP "$srv")
  fi

  ping -c1 -t20 $IP >>$logfile 2>&1
  if [ $? -ne 0 ]; then
    ping -c1 -t20 ${srv}-prv >> $logfile 2>&1
    if [ $? -eq 0 ]; then
      srv=${srv}-prv
      IP=$(HN2IP "$srv")
    else
      echo "$IP ($srv) unpingable" >> $logfile
      return 1
    fi
  fi

  awk 'BEGIN{IRS=";"}{print $1}' $outputfile | grep -iq "$srv" && return
  if [ "$FORMAT" = 'txt' ]; then
    awk 'BEGIN{IRS=" "}{print $1}' $outputfile | grep -iq "$srv" && return
    AWK='{print "'$srv'",$0}'
  elif [ "$FORMAT" = 'csv' ]; then
    awk 'BEGIN{IRS=";"}{print $1}' $outputfile | grep -iq "$srv" && return
    AWK='{print "\"'$srv'\";"$0}'
  fi
  txtfile=$COLLECTDIR/$IP.txt
  [ -f "$txtfile" ] && return
  touch "$txtfile"

  echo $srv

  #Add to kown hosts if not allready done
  grep -qi "$IP" ~/.ssh/known_hosts || ssh-keyscan -t rsa $IP 2>/dev/null >> ~/.ssh/known_hosts
  grep -qi "$srv" ~/.ssh/known_hosts || ssh-keyscan -t rsa $srv 2>/dev/null >> ~/.ssh/known_hosts

  if [ \( "$scriptfile" != "$remote_scriptfile" -o "$srv" != "$hn" \) -a ${remote_scriptfile:0:7} != '/stage/' ]; then
    scp -Bq "$scriptfile" "$IP:$remote_scriptfile" >> $logfile 2>&1
  fi
  if [ $? -eq 0 ]; then
    if [ "$SCRIPTTYPE" = "asm" ]; then
      ssh -q $IP "/stage/oracle/scripts/bash/run_sql -DB +ASM \"@$remote_scriptfile\"" 2>&1 | awk "$AWK" > $txtfile
    elif [ "$SCRIPTTYPE" = "sql" ]; then
      ssh -q $IP "/stage/oracle/scripts/bash/run_sql \"@$remote_scriptfile\"" 2>&1 | awk "$AWK" > $txtfile
    elif [ "$SCRIPTTYPE" = "rman" ]; then
      ssh -q $IP "/stage/oracle/scripts/bash/run_rman \"@$remote_scriptfile\"" 2>&1 | awk "$AWK" > $txtfile
    else
      ssh -q $IP $remote_scriptfile 2>&1 | awk "$AWK" > $txtfile
    fi
    echo $srv | grep -iq "$hn" || ssh -q $IP rm $remote_scriptfile 2>&1 >> $logfile
  else
    echo "${IP} cannot_ssh" >> $logfile
    echo "${IP}" >> $failedfile
    [ $IP != $srv ] && echo "${srv}" >> $failedfile
    return 2
  fi
}

function timedout()
{
PIDs=$(jobs -p)
if [ "$PIDs" ]; then
  kill $PIDs
  sleep 5
  PIDs=$(ps -p $PIDs | awk '!/^ /{print $1}')
fi

if [ "$PIDs" ]; then
  kill -15 $($PIDs)
  sleep 5
  PIDs=$(ps -p $PIDs | awk '!/^ /{print $1}')
fi

if [ "$PIDs" ]; then
  kill -9 $($PIDs)
  sleep 5
fi
failures=$(($failures+1))
}

function usage()
{
  cat << EOF
  usage: $0 options DB

  Dit script wordt gebruikt om informatie te verzamelen van veel andere servers.
  Basis is dat voor een selectie aan servers (zie onderstaande parameters) wordt per server het volgende gedaan:
  - Een script wordt (indien nodig) gekopieerd naar de server
  - middels ssh wordt het script lokaal op de server uitgevoerd en de output wordt centraal opgevangen.

  Indien oracle, of root de owner van het beatand is, dan wordt alles uitgevoerd als die gebruiker (het script $0 roept zichzelf aan middels sudo).

  OPTIONS:
     -h           toont dit helpscherm
     -script      het lokaal te draaien script. Geen standaard. Zonder pad wordt het juiste bestand erbij gezocht op de onderstaande volgorde:
                  - /stage/oracle/scripts/bash/collect/
                  - /stage/oracle/scripts/bash/
                  - /stage/oracle/scripts/sql
                  - /stage/oracle/scripts/rman
                  - ~/
                  - /tmp
                  .sql scripts worden middels ssh / run_sql uitgevoerd.
                  .rman scripts worden middels ssh / run_rman uitgevoerd.
                  overige scripts worden middels ssh direct uitgevoerd.
     -scripttype  type script (asm, sql, rman of bash, default op basis van locatie / extensie)
     -servers     een komma gescheiden opsomming van de servers welke moet worden geprocessed.
                  zonder -servers parameter wordt de HOSTS parameter als basis gebruikt. Vul deze met 'export HOSTS='
                  Eventueel kan middels het Magic Word 'known_hosts' alle servers in ~/.ssh/known_hosts wordt gebruikt.
                  Eventueel kan middels het Magic Word 'sysdoc' alle servers in /stage/oracle/scripts/conf/sysdoc_* wordt gebruikt.

                  Let hierbij op dat afhankelijk van de owner van het uit te voeren script door een sudo ~ kan verwijzen naar /root of /home/oracle.
     -srvfile     Middels deze otpie kan een lijst met servers worden gelezen uit een file.
                  Deze lijst wordt toegevoegd aan de lijst van servers opgegeven met -servers (ze staan er uniek in).
     -parallel    Deze parameter geeft aan hoeveel er parallel gedraaid moeten worden. (default 20)
     -logfile     De locatie waar de log van de sessie opgevangen moet worden (default /tmp/{scriptnaam}.log).
     -output      De locatie waar de output van de scripts verzameld moet worden (default /tmp/{scriptnaam}.txt).
     -format      Het format van de output.
                  csv : Het script levert een csv (Comma Seperated File) op. Text staat tussen '"' en kolommen zijn gescheiden middels ';'.
                  txt (standaard): Het script levert een text file. Geen separator en kolommen gescheiden door ' '.
     -timeout     Timeout waarna het script wordt gestopt met een foutmelding (standaard 1 uur).
     -x           debug level (default 0)

     Overige opties zijn niet toegestaan

EOF
  exit 0
}

while [ -n "$1" ]; do
case $1 in
  -h) usage; exit 0 ;;
  -script) export scriptfile="$2" ; shift 2 ;;
  -servers) export SERVERS=$(echo "$2"|sed 's/,/ /g') ; shift 2 ;;
  -srvfile) export SRVFILE="$2" ; shift 2 ;;
  -parallel) export max_parallel="$2" ; shift 2;;
  -logfile) logfile="$2" ; shift 2;;
  -failedfile) failedfile="$2" ; shift 2;;
  -output) outputfile="$2"; shift 2 ;;
  -format) export FORMAT="$2"; shift 2 ;;
  -timeout) export TIMEOUT="$2"; shift 2;;
  -scripttype) export SCRIPTTYPE="$2"; shift 2;;
  -x) export DBG="$2"; shift 2 ;;
  *) echo "error: no such option $1" ; exit 1 ;;
esac
done

[ "$DBG" ] || DBG=0
[ "$DBG" -gt 1 ] && set -vx

if [ ! "$scriptfile" ]; then
  echo "Geen scriptfile ingesteld."
  exit 1
elif [ ${scriptfile:0:1} != "~" -a ${scriptfile:0:1} != "/" ]; then
  if [ -f /stage/oracle/scripts/bash/collect/$scriptfile ]; then
    export scriptfile="/stage/oracle/scripts/bash/collect/$scriptfile"
    [ "$SCRIPTTYPE" ] || export SCRIPTTYPE=bash
  elif [ -f /stage/oracle/scripts/bash/$scriptfile ]; then
    export scriptfile=/stage/oracle/scripts/bash/$scriptfile
    [ "$SCRIPTTYPE" ] || export SCRIPTTYPE=bash
  elif [ -f /stage/oracle/scripts/sql/$scriptfile ]; then
    export scriptfile=/stage/oracle/scripts/sql/$scriptfile
    [ "$SCRIPTTYPE" ] || export SCRIPTTYPE=sql
  elif [ -f /stage/oracle/scripts/rman/$scriptfile ]; then
    export scriptfile=/stage/oracle/scripts/rman/$scriptfile
    [ "$SCRIPTTYPE" ] || export SCRIPTTYPE=rman
  elif [ -f ~/$scriptfile ]; then
    export scriptfile=~/$scriptfile
  elif [ -f /tmp/$scriptfile ]; then
    export scriptfile=/tmp/$scriptfile
  else
    unset scriptfile
  fi
fi

if [ ! -f "$scriptfile" ]; then
  echo "Scriptfile niet gevonden."
  exit 1
fi

if [ ! "$SCRIPTTYPE" ]; then
  [ $(echo "$scriptfile" | sed 's/^.*\.//' ) = "sql" ] && export SCRIPTTYPE=sql
  [ $(echo "$scriptfile" | sed 's/^.*\.//' ) = "rman" ] && export SCRIPTTYPE=rman
  [ $(echo "$scriptfile" | sed 's/^.*\.//' ) = "asm" ] && export SCRIPTTYPE=asm
  [ "$SCRIPTTYPE" ] || export SCRIPTTYPE=bash
fi

[ "$FORMAT" ] || FORMAT=txt
export FORMAT=$(echo "$FORMAT" | tr '[:upper:]' '[:lower:]')
if [ "$FORMAT" != "csv" -a "$FORMAT" != "txt" ]; then
  echo "Onbekend format."
  exit 1
fi

[ "$max_parallel" ] || max_parallel=20
script_base=$(echo $scriptfile | sed 's|^.*/||;s|\.[^.]*$||')
[ "$logfile" ] || export logfile=/tmp/collect_${script_base}.log
[ "$outputfile" ] || export outputfile=/tmp/collect_${script_base}.${FORMAT}
[ "$failedfile" ] || export failedfile=/tmp/collect_${script_base}.failed

if [ ${scriptfile:1:7} = '/stage/' -a $(date -r "$scriptfile" +%Y%m%d) != $(date +%Y%m%d) ]; then
  remote_scriptfile="$scriptfile"
else
  remote_scriptfile=/tmp/$(basename "$scriptfile")
fi

[ "$TIMEOUT"  ] || TIMEOUT=3600
export TIMEOUT_EPOCH=$(($(date +%s)+$TIMEOUT))

user=$(ls -l $scriptfile | awk '{print $3}')
if [ $user = 'root' -o $user = 'oracle' ]; then
  if [ $(whoami) != $user ]; then
    sudo su - $user -c "$0 -script '$scriptfile' -servers '$SERVERS' -parallel '$max_parallel' -logfile '$logfile' -output '$outputfile' -failedfile '$failedfile' -format '$FORMAT' -timeout '$TIMEOUT' -srvfile '$SRVFILE'"
    exit
  fi
fi

if [ "$SERVERS" = 'known_hosts' ]; then
  HOSTS=$HOSTS\ $(awk '{split($1,a,",");print a[1]}' ~/.ssh/known_hosts)
elif [ "$SERVERS" = 'sysdoc' ]; then
  HOSTS=$HOSTS\ $(cat /stage/oracle/scripts/conf/sysdoc_* | awk '{print $1}'|sort -u)
else
  HOSTS=$HOSTS\ $SERVERS
fi

if [ "$SRVFILE" ]; then
  HOSTS=$HOSTS\ $(cat "$SRVFILE")
fi
HOSTS=$(echo $HOSTS | xargs -l1 | sort -u)

if [ ! "$HOSTS" ]; then
  echo "Geen HOSTS ingesteld."
  exit 1
fi

if [ ! -x "$scriptfile" -a $SCRIPTTYPE = 'bash' ]; then
  echo "$scriptfile is not executable..."
  exit 1
fi

hn=$(hostname)
for f in $logfile $outputfile; do
  touch $f
  chmod 666 $f
done
rm -f $failedfile

COLLECTDIR=$(mktemp)
rm "$COLLECTDIR"
mkdir "$COLLECTDIR"

echo "Scriptfile: $scriptfile"
echo "Hosts:$HOSTS"
[ "$DBG" -gt 0 ] && echo "Collectdir: $COLLECTDIR"
echo "Parallel: $max_parallel"
echo "Logfile: $logfile"
echo "Output: $outputfile"
echo "Format: $FORMAT"
echo "Timeout: $TIMEOUT seconden."

failures=0

for srv in $HOSTS
do
  while [ ! $(jobs | wc -l) -lt $max_parallel ]
  do
    echo -n "."
    sleep 1
    [ $(date +%s) -gt $TIMEOUT_EPOCH ] && timedout
  done
  [ "$failures" -eq 0 ] && collect_host $srv &
done 

while [ $(jobs | wc -l) -gt 0 ]
do
  #Om een of andere reden triggerd dit dat de jobs die er waren uit het lijstje verdwijnen.
  #Kortom, zonder deze regel blijft $(jobs | wc -l) meer dan 0 terug geven en door deze regel wordt het uiteindelijk wel een 0...
  jobs > /dev/null
  [ "$failures" -eq 0 ] || break
  echo -n ":"
  sleep 1
  [ $(date +%s) -gt $TIMEOUT_EPOCH ] && timedout
done

ls -l "$COLLECTDIR"/*.txt >/dev/null 2>&1 && cat "$COLLECTDIR"/*.txt >> $outputfile
[ "$DBG" -eq 0 ] && rm -r "$COLLECTDIR"

if [ -f "$failedfile" ]; then
  echo -n "There where failed ssh connections: "
  cat "$failedfile" | xargs | sed 's/ /, /g'
  echo
  echo "You should run the following commands and then rerun this command to collect them too."
  known_hosts=$HOME/.ssh/known_hosts
  cat "$failedfile" | while read srv; do
    num=$(grep -c "$srv" "$known_hosts")
    [ $num -gt 0 -a $num -lt 5 ] && echo "sudo -u $USER sed -i '/$srv/d' '$known_hosts'"
  done
fi

echo -n "Done"
[ "$failures" -eq 0 ] || echo -n " with errors"
echo

exit $failures
