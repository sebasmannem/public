#!/bin/sh
dq='"'
Host=${dq}`hostname`${dq}
IP=${dq}$(/usr/bin/nslookup `hostname` | tail -n2 | awk '$1~/Address:/{print $2}')${dq}
CPUModel=${dq}$(awk 'BEGIN{FS=":"}$1~/model name/{sub(/^ +/,"",$2);gsub(/ +/,"_",$2);print $2}' /proc/cpuinfo | sort -u | xargs)${dq}
CPUCount=$(awk 'BEGIN{FS=":";b=c=d=1}$1~/^$/{print b;c;d}$1~/processor/{b=$2}$1~/physical id/{b=$2}$1~/cpu cores/{c=$2}$1~/siblings/{d=$2}' /proc/cpuinfo | sort -u | awk 'END{print "\""a"\";\""b"\";\""c"\""}{a+=1;b+=$2;c+=$3}')
Procs=$(awk 'BEGIN{FS=":"}$1~/physical id/{print $2}' /proc/cpuinfo | sort -u | wc -l)
PMons=$(ps -ef | grep -c [p]mon)
Mem=$((1024*$(awk '$1~/MemTotal/{print $2}' /proc/meminfo)))
OS=${dq}$(awk '{print "RHEL",$7,$8}' /etc/redhat-release)${dq}
if [ -r /etc/oratab ]; then
  CRSHOME=$(grep "^crs" /etc/oratab|cut -d: -f2)
  [ $CRSHOME ] || CRSHOME=$(grep "^grid" /etc/oratab|cut -d: -f2)
fi
[ -x $CRSHOME/bin/olsnodes ] && Nodes=$($CRSHOME/bin/olsnodes | xargs) || Nodes=$(hostname)
[ -x $CRSHOME/bin/cemutlo ] && Nodes="$($CRSHOME/bin/cemutlo -n) ($Nodes)"
Nodes=${dq}$Nodes${dq}

# fysiek of virtueel?
CCISS=$(/sbin/lsmod |grep -i cciss|wc|awk '{ print $1 }')
QLA=$(/sbin/lsmod |grep -i qla|wc|awk '{ print $1 }')
PCNET=$(/sbin/lsmod |grep -i pcnet32 |wc|awk '{ print $1 }')
VMX=$(/sbin/lsmod |grep -i vmxnet |wc|awk '{ print $1 }')
VGA=$(/sbin/lspci |grep -i vmware |wc|awk '{ print $1 }')
MB=$(/sbin/lspci |grep -i 440bx |wc|awk '{ print $1 }')
PN=$(dmidecode -s system-product-name | sed 's/ \+$//')
SN=$(dmidecode -s system-serial-number | sed 's/ \+$//')

pgrep vmware    > /dev/null 2>&1 && VMWARE="1" || VMWARE="0"
[ -d /usr/lib/vmware-tools ] && TOOLS="1" || TOOLS="0"

# punten optellen
FYSIEK=$(($CCISS+$QLA))
VIRTUEEL=$(($PCNET+$VMX+$VMWARE+$TOOLS+$VGA+$MB))

#testen op het aantal punten wat de server is
[ "$FYSIEK" -gt "$VIRTUEEL" ] && TYPE='"P"'
[ "$FYSIEK" -eq "$VIRTUEEL" ] && TYPE='"?"'
[ "$FYSIEK" -lt "$VIRTUEEL" ] && TYPE='"V"'

echo "$Host;$IP;${dq}$DATACENTER${dq};\"$PN\";\"$SN\";$OS;$TYPE;$CPUModel;$CPUCount;$Mem;$PMons;$Nodes"

