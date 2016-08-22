#!/bin/sh

function genAutofsFile() {
  NFSFile="$1"
  MOUNTPOINT="$2"
  MOUNTOPTS="$3"

  echo "Creating backups of auto.master and $NFSFile in /tmp"
  [ -f "$NFSFile" ] && cp "$NFSFile" /tmp/$(basename "$NFSFile").$(date +%Y%m%d%H%M%S)
  cp /etc/auto.master /tmp/auto.master.$(date +%Y%m%d%H%M%S)

  echo "Adding $NFSFile to auto.master"
  sed -i "/^\/${MOUNTPOINT}/d" /etc/auto.master
  echo "/${MOUNTPOINT} "$NFSFile" --ghost --timeout=1800" >> /etc/auto.master

  echo "Generating / replacing $NFSFile file"
  echo "$MOUNTOPTS" > "$NFSFile"
  chmod 644 "$NFSFile"
  chown root:root "$NFSFile"

  echo "Creating subfolders if needed"
  awk '{print $3}' $NFSFile | while read SHARE; do
    echo "Creating $SHARE"
    MNT=$(dirname "$SHARE")
    mount "$MNT" "$TMPDIR"
    mkdir -p "$TMPDIR/"$(basename "$SHARE")
    chown oracle:oinstall "$TMPDIR/"$(basename "$SHARE")
    umount "$TMPDIR"
  done

  echo "Removing symbolic link /${MOUNTPOINT} (if any)"
  [ -L "/${MOUNTPOINT}" ] && rm "/${MOUNTPOINT}"
  return 0
}

function cleanAutofsFile() {
  NFSFile=$1
  MOUNTPOINT="$2"
  SUBDIRS="$3"

  [ -f "$NFSFile" ] || return 0

  echo "Creating backups of auto.master and $NFSFile in /tmp"
  [ -f "$NFSFile" ] && cp "$NFSFile" /tmp/$(basename "$NFSFile").$(date +%Y%m%d%H%M%S)
  cp /etc/auto.master /tmp/auto.master.$(date +%Y%m%d%H%M%S)

  echo "Removing $NFSFile from auto.master"
  sed -i "/^\/${MOUNTPOINT}/d" /etc/auto.master

  echo "Cleaning subfolders if needed"
  awk "/$SUBDIRS/{print \$3}" $NFSFile | while read SHARE; do
    echo Cleaning $SHARE
    MNT=$(dirname "$SHARE")
    mount "$MNT" "$TMPDIR"
    rm -r "$TMPDIR/"$(basename "$SHARE")
    umount "$TMPDIR"
  done

  echo "Removing $NFSFile"
  rm "$NFSFile"
  return 0
}

function usage() {
  cat << EOF
  usage: $0 options

  This script is used toconfigure NFS Shares for dumps, datafiles and FRA.

  OPTIONS:
     -h                Show this help screen
     --oradump_share   Share that should hold dump files (/u04).
                       Default: Depends on Domain and \$DATACENTER.
     --oradata_share   optional: Share that should hold oracle datafiles.
     --orafra_share    optional: Share that should hold oracle Flash Recovery Area.
     --clean           optional: Clean the locations for oracle datafiles, oracle fra and dump location

     -x                debug mode                      (default off)

     all other options are invalid.

EOF
  exit 0

}

if [ $(whoami) != 'root' ]; then
  sudo -E "$0" $@
  exit
fi

unset CLEAN

while [ -n "$1" ]; do
  case $1 in
    -h) usage; exit 0 ;;
    --oradump_share) ORADUMP=$2 ; shift 2 ;;
    --oradata_share) ORADATA=$2 ; shift 2 ;;
    --orafra_share)  ORAFRA=$2  ; shift 2 ;;
    --clean) CLEAN=CLEAN ; shift 1 ;;
    *) echo "cannot specify $1" ; exit 1 ;;
#    *)  DBs=$@ ; break ;;
  esac
done

set -e

TMPDIR=$(mktemp -d)

DOMAIN=$(hostname -d)
if [ "$DOMAIN" = 'domain.org' ]; then
  if [ ! "$ORADUMP" ]; then

    . /etc/profile.d/datacenter.sh
    case "$DATACENTER" in
    "DC01")
      ORADUMP=SRVNFS01:/export/p_common_nfs
      ;;
    "DC02")
      ORADUMP=SRVNFS02:/export/a_common_nfs
      ;;
    "DC03")
      ORADUMP=SRVNFS03:/export/ot_common_nfs
      ;;
    # Voor DC04 is een aparte situatie van toepassing aangezien hier geen NFS Share is.
    "DC04")
      unset ORADUMP
      ;;
    *)
      unset ORADUMP
      ;;
    esac
  fi
fi

if [ "$ORADATA" -o "$CLEAN" ]; then
  if [ $CLEAN ]; then
    cleanAutofsFile /etc/auto.oradata u02 oradata
  else
    genAutofsFile /etc/auto.oradata u02 "oradata -fstype=nfs,rw,hard,intr,nodev,nfsvers=3,rsize=32768,wsize=32768 $ORADATA/$HOSTNAME/"
  fi
fi

if [ "$ORAFRA" -o "$CLEAN" ]; then
  if [ $CLEAN ]; then
    cleanAutofsFile /etc/auto.orafra u03 orafra
  else
    genAutofsFile /etc/auto.orafra u03 "fra -fstype=nfs,rw,hard,intr,nodev,nfsvers=3,rsize=32768,wsize=32768 $ORAFRA/$HOSTNAME/"
  fi
fi

if [ "$ORADUMP" -o "$CLEAN" ]; then
  if [ $CLEAN ]; then
    cleanAutofsFile /etc/auto.oradump u04 oracle
  else
    genAutofsFile /etc/auto.oradump u04 "oracle -fstype=nfs,rw,hard,intr,nodev,nfsvers=3,rsize=32768,wsize=32768 $ORADUMP/all/$HOSTNAME/
all    -fstype=nfs,ro,hard,intr,nodev,nfsvers=3,rsize=32768,wsize=32768 $ORADUMP/all
git    -fstype=nfs,rw,hard,intr,nodev,nfsvers=3,rsize=32768,wsize=32768 $ORADUMP/git"
  fi
fi

if [ "$ORADUMP$ORADATA$ORAFRA" ]; then
  echo "Reloading autofs config:"
  service autofs reload
fi

#Workaround voor /etc/auto.master files die niet eindigen ,et een \n
echo "" >> /etc/auto.master

#But clean out any double enters in the file
# 1h;           Copy line 1 to hold buffer
# 1!H;          Copy rest to hold buffer
# ${;           In the end
# g;            Copy from hold buffer back to pattern buffer
# s|\n\+|\n|g ; replace multipole enters by one
# p;}           Print out pattern buffer
sed -i -n '1h;1!H;${;g;s|\n\+|\n|g ;p;}' /etc/auto.master
