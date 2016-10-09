#!/bin/bash
set -e
VMNAME=${1:-vm_centos_cloud_1}
VMIMAGE=${2:-CentOS-7-x86_64-GenericCloud-1606}
LVMVOLUME=${3:-Volume00}

TMPDIR=$(mktemp -d)


ID=$(uuidgen)

echo -n "instance-id: $ID
local-hostname: $VMNAME
public-keys:
  - " > "$TMPDIR/meta-data"

cat ~/.ssh/id_rsa.pub >> "$TMPDIR/meta-data"

mkisofs -o "$TMPDIR/config.iso" -V cidata -r -J "$TMPDIR/meta-data"

sudo lvcreate -kn -ay -n "$VMNAME" -s "$LVMVOLUME/$VMIMAGE"

sudo chmod 777 -R "$TMPDIR"

sudo virt-install --name="$VMNAME" \
   --disk=/dev/Volume00/"$VMNAME" \
   --disk "path=$TMPDIR/config.iso,device=cdrom" \
   --graphics spice \
   --vcpus=2 --ram=2048 \
   --network default \
   --os-type=linux \
   --os-variant=centos7.0 \
   --import
