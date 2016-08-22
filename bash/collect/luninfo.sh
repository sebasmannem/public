#!/bin/sh
Host=${dq}`hostname`${dq}
  dest=/var/tmp/LunPaths_pre.log
if [ ! -f "$dest" ]; then
  dest=/var/tmp/LunPaths_pre.log
else
  file_age=$(date -r "$dest" +%s)
  [ $file_age ] || file_age=0
  file_age=$(($(date +%s)-$file_age))
  #Ouder dan een week?
  [ $file_age -gt 604800 ] && dest=/var/tmp/LunPaths_pre.log || dest=/var/tmp/LunPaths_post.log
fi
/stage/linuxbeheer/netapp/santools/sanlun lun show | awk 'BEGIN{IGNORECASE=1}$1~/SRV/{print $1":"$2}' | sort | awk 'END{print a,b}{if (a==$1) {b+=1} else {if (b>0) print a,b;b=1;a=$1}}' > $dest
if [ -x /usr/bin/lssg ]; then
  echo -n "ULTRIUM-TD1 " >> $dest
  /usr/bin/lssg | grep -c 'ULTRIUM-TD1' >> $dest
fi
#awk '{print "'$Host'",$0}' $dest
cat $dest
