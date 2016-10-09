#!/bin/bash
if [ $(whoami) != 'root' ]; then
  sudo -E "$0"
  exit
fi

shmgb=$(awk '/MemTotal/{printf("%.0f",$2/1024/1024-2,0)}' /proc/meminfo)
sed -i '/\/dev\/shm/d' /etc/fstab
echo "tmpfs                   /dev/shm                tmpfs   defaults,size=${shmgb}g        0 0" >> /etc/fstab
mount | grep -q '/dev/shm' && mount /dev/shm -o remount || mount /dev/shm

shm=$(($shmgb * 1024*1024*1024))
sed -i -r '/kernel.shm(max|all)/d' /etc/sysctl.conf
echo "kernel.shmmax = "$shm >> /etc/sysctl.conf
echo "kernel.shmall = "$(($shm / 4096)) >> /etc/sysctl.conf

sysctl -p > /dev/null
