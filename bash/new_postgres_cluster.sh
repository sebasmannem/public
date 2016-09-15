#!/bin/bash

set -e

if [ $(id -u) -ne 0 ]; then
    echo "Please run as root (e.a. sudo $0 $@)"
    exit 1
fi

RET=0
cluster=$1
port=${2:-5432}
PGDATA=/etc/postgresql/${cluster}
DATA_DIR=/var/lib/postgresql/${cluster}/data

for d in "$PGDATA" "$DATA_DIR"; do
    if [ -x "$d" ]; then
        echo "Seems that $d already exists. Please clean and run again..."
        RET=1
    fi
done

[ $RET -ne 0 ] && exit $RET

for d in "$PGDATA" "$DATA_DIR"; do
    mkdir -p "$d"
    chown postgres:postgres "$d"
done
sudo -u postgres /usr/bin/pg_ctl init -D "$DATA_DIR"

for f in postgresql.conf pg_hba.conf pg_ident.conf; do
    mv "$DATA_DIR/$f" "$PGDATA"
done

sudo -u postgres mkdir "$PGDATA/conf.d"
echo "include_dir = 'conf.d'" >> "$PGDATA/postgresql.conf"

echo "port = $port" > "$PGDATA/conf.d/port.conf"

systemctl enable postgresql@${cluster}
