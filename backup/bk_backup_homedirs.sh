#!/bin/bash
DIR=/u02/backup/current/homedirs
if [ ! -d $DIR ]
then 
  mkdir -p $DIR
fi

LIST=$(ls -1 /home)
for d in $LIST
do
  echo "Backup of homedir /home/$d to $DIR/$d.gz"
  tar -acf $DIR/$d.tar.gz /home/$d
done
