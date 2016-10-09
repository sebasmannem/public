#!/bin/bash
primary=$1
password=$2
set -e
[ $(id -un) == 'postgres' ] || { echo 'Please run as user postgres (like sudo -u postgres, or something).'; exit 1; }
/usr/pgsql-9.4/bin/pg_ctl -D /var/lib/pgsql/9.4/data -l logfile stop
cd /var/lib/pgsql/9.4
if [ -x ~/.pgpass ]
    echo "$primary:5432:replication:replicant:$password" > ~/.pgpass
    chmod 600 ~/.pgpass
fi
pg_basebackup -h "$primary" -U replicant -D data -RPX stream
echo "primary_slot_name = 'slot1'" >> /var/lib/pgsql/9.4/data/recovery.conf
/usr/pgsql-9.4/bin/pg_ctl -D /var/lib/pgsql/9.4/data -l logfile start

#promote:
#stop master
#pg_ctl promote -D $PG_DATA
#pg_ctl -D $PG_DATA -l logfile start

