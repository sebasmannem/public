#!/bin/sh
for conf in `ls /etc/drbd.d/*.res`
do
  res=`awk '/^resource .* {/{print $2}' $conf`
  for dns in `awk '/ *on .* {/{print $2}' $conf`
  do
    IP=`nslookup $dns | awk 'BEGIN{RS="\n\n";FS="\n"}/'$dns'/{split($2,a,":");print a[2]}'`
    IP=`echo $IP` #spaties eruit
    if [ `ifconfig | grep "inet addr:$IP  "` -gt 0  ]; then
      sudo drbdadm secondary $res
      sudo drbdadm -- --discard-my-data connect $res
    else
      ssh $srv "sudo drbadm connect $res"
    fi
  done
done
