#!/bin/sh
DIR=/u02/backup

if [ $(date +%d) -eq 1 ] 
then
  if [ $(date +%m) -eq 1 ] 
  then
    echo 1 januari
    rm -rf $DIR/y-2/
    mv -f $DIR/y-1 $DIR/y-2
    mv -f $DIR/y-0 $DIR/y-1
    mv -f $DIR/current $DIR/y-0
    mkdir $DIR/current
  else
    echo 1e van de maand
    rm -rf $DIR/m-1/
    mv -f $DIR/m-0 $DIR/m-1
    mv -f $DIR/current $DIR/m-0
    mkdir $DIR/current
  fi
else
  if [ $(date +%u) -eq 1 ]
  then
    echo Maandag
    rm -rf $DIR/w-1/
    mv -f $DIR/w-0 $DIR/w-1
    mv -f $DIR/current $DIR/w-0
    mkdir $DIR/current
  else
    echo Vandaag naar gisteren verplaatsen
    rm -rf $DIR/d-1/
    mv -f $DIR/current $DIR/d-1
    mkdir $DIR/current
  fi
fi

if [ -f /var/log/backup.log ]
then
	rm /var/log/backup.log
fi
