#!/bin/bash

function QuitOnError() {
  [ "$1" ] && echo "$1"
  exit 1
}

SS_NAME=$(date +%Y-%m-%d_%H-%M-%S)
BTRFS_LIB=/var/lib/btrfs
cd $BTRFS_LIB
umount __active || QuitOnError "Could not umount __active"
btrfs su sn __active __snapshots/$SS_NAME || QuitOnError "Could not create snapshot"
mount __active || QuitOnError "Could not mount __active"
pacman -Syu --noconfirm || QuitOnError "Could not upgrade"
ls -tr ./__snapshots/ | sed -n '5,$p' | while read s; do btrfs su de ./__snapshots/$s || QuitOnError "Could not remove snapshot $s"; done
