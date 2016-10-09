#!/bin/sh
HN=$(hostname)
DOMAIN=$(hostname -d)
if [ $1 ]; then
  TYPE=_$1
elif [ "$DOMAIN" = "domain.org" ]; then
  case "$(echo $HN  | cut -c8)" in
    1) 
      TYPE=_db
      ;;
    2)
      TYPE=_app
      ;;
    3)
      TYPE=_oid
      ;;
    4)
      TYPE=_cman
      ;;
    9)
      TYPE=_oms
      ;;
  esac
elif [ "${DOMAIN:${#DOMAIN}-12:1000}" = ".localdns.nl" ]; then
  case "$(echo $HN | cut -b 9-11)" in
    "a35")
      TYPE=_db
      ;;
  esac
else
  echo "Invalid DOMAIN: $DOMAIN. Should be domain.org or *.localdns.nl."
fi

mkdir -p /usr/local/bin/ini
chown oracle:oinstall /usr/local/bin
chown oracle:dba /usr/local/bin/ini

mkdir -p /u01/app/oracle/logs
chown oracle:oinstall /u01/app/oracle/logs
chmod 755 /u01/app/oracle/logs
#lk 20140430: check ownership /u01/app/oracle, aanpassen naar oracle als dat niet het geval is
[[ `stat -c %U /u01/app/oracle` !=  'oracle' ]] && chown oracle:oinstall /u01/app/oracle

sed -n 's/#.*//
/^ *$/!p' /stage/oracle/scripts/conf/update${TYPE}.conf | while read line
do
  rsync -av $line
done
/sbin/chkconfig oracle --list >/dev/null 2>&1 || { /sbin/chkconfig --add oracle; /sbin/chkconfig oracle on;  }

[ -L /etc/init.d/oracle${TYPE} ] || ln -sf /etc/init.d/oracle /etc/init.d/oracle${TYPE}
[ -e /home/oracle/bin ] || ln -s /stage/oracle/scripts/bash /home/oracle/bin
[ -e /home/oracle/sql ] || ln -s /stage/oracle/scripts/sql /home/oracle/sql

if [ ${TYPE:0:3} = _db ]; then
  su - oracle /stage/oracle/scripts/bash/SBB_Update_DB.sh
fi
