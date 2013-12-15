#!/bin/sh
#Eerst alle niet mp3 files weg gooien
find . -type f | grep -viE '.(mp3|wma|wav)$' | while read fl
do
  rm "$fl"
done

#Dan de nummers aan het begin minimaal 2 cijfers maken...
find . -regex '.*/[0-9][^0-9 /][^/]*\.mp3' | while read fl
do 
  echo -n "$fl -> "
  newfl=$(echo "$fl" | sed 's/\(\/\)\([0-9]\)\([^0-9 /][^/]*\.mp3\)/\/0\2 - \3/')
  echo "$newfl"
  mv "$fl" "$newfl"
done

##Dan de nummers met direct text erachter aanpassen naar '## - '...
find . -regex '.*/[0-9][0-9][^0-9 /][^/]*\.mp3'| while read fl
do
  echo -n "$fl -> "
  newfl=$(echo "$fl" | sed 's/\(\/\)\([0-9][0-9]\)\([^0-9 /][^/]*\.mp3\)/\/\2 - \3/')
  echo "$newfl"
  mv "$fl" "$newfl"
done

#Dan alle files op volgerde doorlopen en middels touch de filedattime naar nu zetten...
find . | sort | while read fl
do
  echo "$fl"
  touch "$fl"
  sleep 0.1
done
