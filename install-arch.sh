#!/bin/sh

#Refresh list with:
#{ pacman -Qqet | awk '{print $1}' ; cat /u02/nas/scripts/conf/package_list.txt ; } | sort -u > package_list.txt

PCKs=$(cat /u02/nas/scripts/conf/package_list.txt)
echo Trying to install
echo $PCKs
echo
pacman -S --noconfirm ${PCKs} 2>&1 | awk 'BEGIN{FS=":"}$1~/error/{print $3}' > /tmp/pacman_failed_packages.txt
PCKs_FAILED=$(cat /tmp/pacman_failed_packages.txt | xargs | sed 's/ /|/g')
if [ "$PCKs_FAILED" ]; then
  echo Failed on
  echo $PCKs_FAILED
  echo
  PCKs=$(grep -vE "($PCKs_FAILED)" /u02/nas/scripts/conf/package_list.txt)
  echo Trying to install
  echo $PCKs
  echo
  pacman -S --noconfirm ${PCKs} 
fi

exit
cat /u02/nas/scripts/conf/package_list.txt | while read pck
do
  pacman -S --noconfirm "$pck" || echo "$pck" >> /tmp/pacman_failed_packages.txt
done
