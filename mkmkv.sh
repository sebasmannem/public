#!/bin/bash
src=$1
if [ ! -e "$src" ]; then
  echo "Source '$src' does not exist"
  exit 1
fi
srcdir=`dirname "$src"`
dst=`basename "$src"`
[ -f "$src" ] && dst=$(echo "$dst" | sed 's/\.[^.]+$//') #${dst:0:$((${#dst}-4))}
dst=$srcdir/mkv/$dst.mkv
if [ -f "$dst" ]; then
  echo "Destination file '$dst' allready exists"
  exit 1
fi
echo Creating "$srcdir/iso"
mkdir -p "$srcdir/iso"
echo Creating "$srcdir/mkv"
mkdir -p "$srcdir/mkv"
echo "Collecting source info from '$src'"
title=$(HandBrakeCLI --main-feature --scan -i "$src" 2>&1 | awk 'BEGIN{RS="\+ title";FS="\n"}/Main Feature/{sub(":","",$1);print $1}')
info=$(HandBrakeCLI -t $title --scan -i "$src" 2>&1 | awk 'BEGIN{FS=","}END{print a,b}/\+ audio tracks:/{t="a"}/\+ subtitle tracks:/{t="s"}{sub(/[+, ]+/,"",$1)} $1~/^[0-9]*$/&&t~/a/{a=a","$1} $1~/^[0-9]*$/&&t~/s/{b=b","$1}')
audioTracks=`echo $info | awk '{print $1}'`
subTracks=`echo $info | awk '{print $2}'`
echo Sub: $subTracks
echo Audio: $audioTracks

audioTracks=${audioTracks:1}
subTracks=${subTracks:1}
[ "$audioTracks" ] && audioTracks='-a'${audioTracks} || audioTracks=''
[ "$subTracks" ] && subTracks="-s"${subTracks} || subTracks=''
echo Sub: $subTracks
echo Audio: $audioTracks
echo "Making '$dst' from '$src'"
echo HandBrakeCLI -i "$src" -t $title -o "$dst" -e x264 -b 2000 -2 -T $audioTracks $subTracks -Ndut --native-dub
HandBrakeCLI -i "$src" -t $title -o "$dst" -e x264 -b 2000 -2 -T $audioTracks $subTracks -Ndut --native-dub
[ $? -eq 0 -a -d "$src" ] && mv "$src" "$srcdir/iso"
#mkisofs -o "$dst" "$src"
#mencoder dvd://1 -dvd-device zwelgje/Als\ je\ begrijpt\ wat\ ik\ bedoel/ -ovc lavc -lavcopts vcodec=mpeg4:vhq:vbitrate="2000" -oac mp3lame -lameopts br=192 -o zwelgje.avi
#mkvmerge -o zwelgje.mkv zwelgje.avi

