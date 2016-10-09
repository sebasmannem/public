#!/usr/bin/python
function cleanpath()
{
PTH="$1"
[ ${PTH:0:1} = "~" ] && PTH="$HOME/$PTH"
[ ${PTH:0:1} != "/" ] && PTH="$PWD/$PTH"

#Remove /./
while [ $(echo "$PTH" | sed -n '/\/\.\//p') ]
do
  PTH=$(echo "$PTH" | sed 's|/\./|/|')
done

#Remove /blaat/../
while [ $(echo "$PTH" | sed -n '/\/[^/]*\/\.\.\//p') ]
do
  PTH=$(echo "$PTH" | sed 's/\/[^/]*\/\.\.\//\//g')
done
echo $PTH
}

function part2asminfo()
{
disk=$1
hdr=$(dd if="$disk" bs=1 count=8 skip=32 2>/dev/null)
[ "$hdr" = "ORCLDISK" ] || return 1
ASMLIB=$(dd if="$disk" bs=1 count=32 skip=40 2>/dev/null | strings)
ASMNAME=$(dd if="$disk" bs=1 count=32 skip=72 2>/dev/null | strings)
DG=$(dd if="$disk" bs=1 count=32 skip=104 2>/dev/null | strings)
ASMNAME2=$(dd if="$disk" bs=1 count=32 skip=136 2>/dev/null | strings)

echo $ASMLIB:$ASMNAME:$ASMNAME2:$DG
echo "<ASMDISK ASMLIB='$ASMLIB' DISKNAME='$ASMNAME' DISKGROUP='$DG' ASMNAME2='$ASMNAME'>" >&2
}

function asmdisks()
{
ls /dev/mapper/*p* | while read part
do
  echo -n "$part:"
  part2asminfo $part 2>/dev/null || echo ":::"
done
}

function dev2size()
{
  /sbin/fdisk -l "$@" 2>/dev/null | awk '$1~/^Disk$/&&$6~/bytes/{print $5}'
}

function dev2mapper()
{
DEV=$@
MAJ=$(ls -l "$DEV" | awk '{print $5}')
MIN=$(ls -l "$DEV" | awk '{print $6}')
ls -l /dev/mapper/* | awk '$5~/^'$MAJ'$/&&$6~/^'$MIN'$/{print $10}'
}

function dev2part()
{
MAPPER=$(dev2mapper $1)
if [ $(echo "$MAPPER" | sed -n '/p[0-9]*/p') ]; then
  echo $MAPPER
  SIZE=$(dev2size $MAPPER)
  echo "<PART PATH='$MAPPER' SIZE='$SIZE'>" >&2
fi
}

function part2disk()
{
PART=$(dev2mapper $@)
DISK=$(echo "$PART" | sed 's/p[0-9]*$//')
echo "$DISK"
SIZE=$(dev2size $DISK)
echo "<DISK PATH='$DISK' SIZE='$SIZE'>" >&2
}

function disk2lun()
{
DISK=$(dev2mapper $1)
ID=$(basename "$DISK")
DISKNAME=$(ls -l /dev/disk/by-id/ | awk '$9~/^scsi-'$ID'$/{split($11,a,"/");print a[3]}')
LUN=$(/stage/linuxbeheer/netapp/santools/sanlun lun show all | awk '$3~/^\/dev\/'$DISKNAME'$/{print $1,$2,$6}')
FAS=$(echo $LUN | awk '{print $1}')
LUNPATH=$(echo $LUN | awk '{print $2}')
SIZE=$(echo $LUN | awk '{print $3}')
echo "$LUN"
echo "<LUN FAS='$FAS' PATH='$LUNPATH' SIZE='$SIZE'>" >&2
}

if [ $(whoami) != 'root' ]; then
  sudo "$0" $@
  exit
fi

until [ -z "$1" ]  # Until all parameters used up . . .
do
  OBJ=$1
  if [ -x "$OBJ" ]; then
    if [ -f "$OBJ" -o -d "$OBJ" ]; then
      #File or directory
      OBJ=$(cleanpath $OBJ)
    elif [ $(/usr/sbin/lvdisplay | grep -c "$OBJ") -gt 0 ]; then
      #LVM logical volume
      /usr/sbin/lvdisplay -m "$OBJ" | awk '/Physical volume/{print $3}'

    elif [ $(/usr/sbin/vgdisplay | grep -c "$OBJ") -gt 0 ]; then
      #LVM Volume group
      VG=$(basename "$OBJ")
      pvdisplay | awk '/PV Name/{a=$3}/VG Name.*'$VG'/{print a":"$3}'

    else
      OBJ=$(cleanpath $OBJ)
      [ ${OBJ:0:5} = '/dev/' ] || continue
      PART=$(dev2part $1)
      [ $PART ] && part2asminfo $PART
      [ $PART ] && DISK=$(part2disk $1)
      [ $DISK ] && LUN=$(disk2lun $DISK)
      
    fi
  else
    if [ ${OBJ:0:5} = "ORCL:" ]; then
      #ASMLib
      asmdisks | awk 'BEGIN{FS=":"}$2~/^'${OBJ:5}'$/{print $1}'
    elif [ ${OBJ:0:1} = "+" ]; then
      #Oracle diskgroup
      asmdisks | awk 'BEGIN{FS=":"}$5~/^'${OBJ:1}'$/{print $1}'
    elif [ $(echo "$OBJ" | grep -c ":" ) -gt 0 ]; then
      #FAS of NFS of CIFS
      SRVR=$(echo "$OBJ" | awk 'BEGIN{FS=":"}{print $1}')
      PTH=$(echo "$OBJ" | awk 'BEGIN{FS=":"}{print $2}')
#      /stage/linuxbeheer/netapp/santools/sanlun lun show all | awk '$3~/^\/dev\/'$DISKNAME'$/{print $1,$2,$6}')
    fi
  fi
  shift
done
