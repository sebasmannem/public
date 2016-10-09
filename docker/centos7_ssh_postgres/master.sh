#!/bin/bash
set -e
[ $(id -un) == 'postgres' ] || { echo 'Please run as user postgres (like sudo -u postgres, or something).'; exit 1; }
echo "create user replicant with replication, password 'replication';
SELECT * FROM pg_create_physical_replication_slot('slot1');" | psql
cat 'wal_level = hot_standby
max_wal_senders = 5
hot_standby = on
hot_standby_feedback = on
max_replication_slots = 1' > /var/lib/pgsql/9.4/data/conf.d/replication.conf
echo 'host    replication     replicant       172.17.0.0/24           md5' >> /var/lib/pgsql/9.4/data/pg_hba.conf
/usr/pgsql-9.4/bin/pg_ctl -D /var/lib/pgsql/9.4/data -l logfile restart
