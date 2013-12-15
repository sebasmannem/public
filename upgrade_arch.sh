#!/bin/bash
SS_NAME=$(date +%Y-%m-%d_%H-%M-%S)
cd /var/lib/btrfs
umount __active
btrfs su sn __active __snapshots/$SS_NAME
mount __active
pacman -Syu
