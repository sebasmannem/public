#!/bin/bash
cp /config/main.cf /etc/postfix/main.cf

cp /config/dovecot.conf /etc/dovecot/dovecot.conf
cp /config/10-ssl.conf /etc/dovecot/conf.d/10-ssl.conf

cp /config/aliases /etc/aliases
/usr/bin/newaliases

sed 's/#.*//;s/.*://;s/,//g' /etc/aliases | xargs -n1 | sort -u | while read USR
do 
  useradd -m $USR > /run_all.log 2>&1
  chown ${USR}:${USR} /home/${USR}
  [ "${PASSWORD}" ] && echo "$PASSWORD" | passwd --stdin "${USR}"
done

/sbin/postfix -c /etc/postfix -D  start > /run_all.log 2>&1
nohup /usr/sbin/dovecot -F -c /etc/dovecot/dovecot.conf > /run_all.log 2>&1 &
cat
