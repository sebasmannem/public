#!/bin/bash
if [ $(whoami) != 'oracle' ]; then
  sudo -u oracle "$0" $@
  exit
fi

. /stage/oracle/scripts/bash/oralib > /dev/null
NEEDED=$(for i in $(running_instances); do run_sql $i "select value+314572800 from v\$parameter where name = 'memory_target';"; done | awk 'BEGIN{a=2**31}END{print a}{a+=$1+300*2*20}')
HAVING=$(awk '/MemTotal/{print $2*2**10}' /proc/meminfo)
u02_free=$(df -k /u02 | tail -n1 | sed -r 's/^([^ ]* +)([0-9]+ +[0-9]+ +[0-9]+)( .*)/\2/' | awk '{print $3-$1*.2}')
u03_free=$(df -k /u03 | tail -n1 | sed -r 's/^([^ ]* +)([0-9]+ +[0-9]+ +[0-9]+)( .*)/\2/' | awk '{print $3-$1*.2}')

echo $NEEDED $HAVING $u02_free $u03_free
