#!/bin/bash
. /stage/oracle/scripts/bash/oralib > /dev/null
host=$(hostname -s)
cluster=$([ -x $CRS_HOME/bin/cemutlo ] && $CRS_HOME/bin/cemutlo -n || echo Single)
running_instances | awk 'BEGIN{IGNORE_CASE=1}$0!~/ASM/{print "'$host'","'$cluster'",$0}'
