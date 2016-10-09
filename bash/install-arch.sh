#!/bin/bash

function quitOnError() {
  [ $# -gt 0 ] && echo "$@"
  exit 1
}

[ $HN ] || HN=new.mannem.nl
[ $IP ] || IP=192.168.122.200
[ $BASE ] || BASE=24

[ "$1" ] && DRIVE="$1" || quitOnError "Please specify an empty disk device from /dev/."
[[ "$DRIVE" =~ / ]] || DRIVE="/dev/$DRIVE"
[[ "$DRIVE" =~ ^/dev/[svh] ]] || quitOnError "$DRIVE is not an disk device (/dev/[svh]*). Please specify an empty disk device from /dev/."
[[ "$DRIVE" =~ [0-9]$ ]] && quitOnError "$DRIVE is not an disk device but a partition. Please specify an empty disk device from /dev/."
[ -b "$DRIVE" ] || quitOnError "$DRIVE does not exist."
ls "$DRIVE"[0-9] >/dev/null 2>&1 && quitOnError "$DRIVE has a partition. Please specify an empty disk device from /dev/."

echo "installing to $DRIVE"
parted -s "$DRIVE" mklabel msdos || quitOnError "Could not create partition table"
parted -s -- "$DRIVE" mkpart primary ext2 1 -0 || quitOnError "Could not create partition"
parted -s "$DRIVE" set 1 LVM on || quitOnError "Could set LVM on for partition"

pvcreate "${DRIVE}1" || quitOnError "Could not create Physical Disk"
vgcreate Volume00 "${DRIVE}1" || quitOnError "Could not create LVM Volume Group"

MEM=$(free -b | awk '/Mem:/{print $2}')
lvcreate -n lv_swap -L $(($MEM*2))b Volume00 || quitOnError "Could not create SWAP logical Volume"
mkswap /dev/Volume00/lv_swap || quitOnError "Could not initialize swap disk"
swapon /dev/Volume00/lv_swap || quitOnError "Could not set swap on"

lvcreate -n lv_root -l 100%FREE Volume00 || quitOnError "Could not create ROOT Logical Volume"
mkfs.btrfs /dev/Volume00/lv_root || quitOnError "Could nog make btrfs filesystem"
mount /dev/Volume00/lv_root /mnt || quitOnError "COuld not mount btrfs fs"
mkdir /mnt/__snapshots || quitOnError "Could not make subdir for snapshots"
btrfs su cr /mnt/__active || quitOnError "Could not create __active subvolume"
BTRFS_ID=$(btrfs su li /mnt | awk '/__active/{print $2}')
btrfs su se ${BTRFS_ID} /mnt || quitOnError "Could not set $BTRFS_ID as default subvol"
umount /mnt || quitOnError "Could not unmount /mnt"
mount /dev/Volume00/lv_root /mnt || quitOnError "Could not remount btrfs fs"
mkdir -p /mnt/var/lib/btrfs/empty || quitOnError "Could not create folder /mnt/var/lib/btrfs/empty/"
pacstrap /mnt base || quitOnError "Could not pacstrap"

genfstab -p /mnt > /mnt/etc/fstab
echo '/var/lib/btrfs/empty                            /var/lib/btrfs/__active none    bind' >> /mnt/etc/fstab

mkdir -p /mnt/u02/nas
mount -o bind /u02/nas /mnt/u02/nas

ln -sf /usr/share/zoneinfo/Europe/Amsterdam /mnt/etc/localtime

if [ "$HN" -a "$IP" ]; then
  arch-chroot /u02/nas/git/scripts/python/ConfigNetwork.py --hostname $HN --ip $IP --base $BASE | tee -a /mnt/tmp/install-arch-chroot.log
  cp "/u01/git/scripts/systemd/network@.service" "/mnt/etc/systemd/system/network@.service"
fi

arch-chroot /mnt /u02/nas/git/scripts/bash/install-arch-chroot.sh | tee -a /mnt/tmp/install-arch-chroot.log
