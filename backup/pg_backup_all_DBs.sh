#!/bin/bash
DIR=/u02/nas/backup/current/psql
if [ ! -d $DIR ] 
then
  mkdir -p $DIR
  chown :postgres $DIR
  chmod g+w $DIR
fi

LIST=$(su - postgres -c 'psql -l' | grep '|' | awk '{ print $1}' | grep -vE '^-|^List|^Name|template[0|1]')
for d in $LIST
do
  echo "Dumping $d to $DIR/$d.out.gz"
  su - postgres -c "pg_dump $d | gzip -c >  $DIR/$d.out.gz"
done

echo "Dumping global settings to $DIR/globals.out.gz"
su - postgres -c "pg_dumpall --globals | gzip > $DIR/globals.sql.gz"
