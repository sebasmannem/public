#!/bin/bash
SS_NAME=$(date +%Y-%m-%d_%H-%M-%S)
BTRFS_LIB=/var/lib/btrfs
cd $BTRFS_LIB
umount __active
btrfs su sn __active __snapshots/$SS_NAME
mount __active
pacman -Syu --noconfirm
ls -tr ./__snapshots/ | sed -n '5,$p' | while read s; do btrfs su de ./__snapshots/$s; done
