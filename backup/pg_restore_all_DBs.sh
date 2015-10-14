#!/bin/bash

# Hier moet nog veel omheen gebeuren...

[ "$1" ] && Path=$1 || Path=/u02/nas/backup/current/psql

if [ -f $Path/globals.out.gz ]; then
  echo "Processing global settings"
  gunzip -c $Path/globals.out.gz | psql postgres
fi

for file in `ls -1 $Path/*.out.gz`
do
  if [ $file != 'globals.out.gz' ]; then
    DBName=`basename $file .out.gz`
    echo "Processing $DBName"
    createdb $DBName
    gunzip -c $file | psql $DBName
  fi
done
