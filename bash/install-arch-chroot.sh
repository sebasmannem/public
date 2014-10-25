#!/bin/bash

function quitOnError() {
  [ $# -gt 0 ] && echo "$@"
  exit 1
}

sed -i '/nl_NL.UTF-8 UTF-8/s/#//g' /tmp/locale.gen
/usr/bin/locale-gen
echo 'LANG="nl_NL.UTF-8"' > /etc/locale.conf

sed -i 's/HOOKS=.*/HOOKS="base udev autodetect modconf block filesystems btrfs keyboard lvm2"/' /etc/mkinitcpio.conf
/usr/bin/mkinitcpio -p linux

#Refresh list with:
#{ pacman -Qqet | awk '{print $1}' ; cat /u02/nas/git/scripts/conf/package_list.txt ; } | sort -u > package_list.txt

PCKs=$(cat /u02/nas/git/scripts/conf/package_list.txt)
echo Trying to install
echo $PCKs
echo
/usr/bin/pacman -S --noconfirm ${PCKs} 2>&1 | awk 'BEGIN{FS=":"}$1~/error/{print $3}' > /tmp/pacman_failed_packages.txt
PCKs_FAILED=$(cat /tmp/pacman_failed_packages.txt | xargs | sed 's/ /|/g')
if [ "$PCKs_FAILED" ]; then
  echo Failed on
  echo $PCKs_FAILED
  echo
  PCKs=$(grep -vE "($PCKs_FAILED)" /u02/nas/git/scripts/conf/package_list.txt)
  echo Trying to install
  echo $PCKs
  echo
  /usr/bin/pacman -S --noconfirm ${PCKs} 
fi

/usr/bin/lvdisplay -m /dev/Volume00/lv_root* | awk '/Physical volume/{print $3}' | sort -u | while read d
do 
  echo >> /tmp/grub-install.log
  echo "$d:" >> /tmp/grub-install.log
  /usr/bin/grub-install --target=i386-pc --recheck --debug "$d" >> /tmp/grub-install.log
done
grub-mkconfig -o /boot/grub/grub.cfg

/usr/bin/groupadd sudo
echo '%sudo   ALL=(ALL) ALL' >> /etc/sudoers.d/sudo_group
/usr/bin/useradd -m sabes -G sudo

/usr/bin/pacman -R --noconfirm vi
ln -s /bin/vim /bin/vi

[ $PW ] || PW=blaat
passwd <<EOF
$PW
$PW
EOF

passwd sabes<<EOF
$PW
$PW
EOF

systemctl start sshd.service && systemctl enable sshd.service
