#!/bin/bash
function usage()
{
  cat << EOF

  Dit script wordt gebruikt om een Oracle RDBMS Home te verwijderen.
  De orainventory wordt aangepast en de opgegeven home wordt verwijderd.
  Voordat dit gebeurt:
  - wordt er gecheckt of er nog processen uit de opgeven RDBMS home draaien.
  - wordt gecheckt of de opgeven RDBMS home in /etc/oratab aanwezig is.

  usage: $0 <Full path to OracleHome>

  Voorbeeld: $0 /u01/app/oracle/product/11.2.0.4.03/db

EOF
  exit 0
}


### MAIN ###

if [ -z "$1" ]
then
  usage
fi

ORAHOME=$1
if [ ! "${ORAHOME}" ]; then
  echo "Please specify the home..."
  exit 1
fi

if [ $(whoami) != 'root' ]; then
  sudo -E "$0" "${ORAHOME}"
  exit
fi

[ -x "${ORAHOME}/oui/bin/detachHome.sh" ] || { echo "Could not execute ${ORAHOME}/oui/bin/detachHome.sh"; exit 1; }

if grep -q "${ORAHOME}" /etc/oratab; then
  echo "Home is still in oratab"
  exit 1
elif [ $(ps -ef | grep -v grep | grep -v "$0" | grep -c "${ORAHOME}") -gt 0 ]; then
  echo "There are processes running from this home:"
  ps -ef | grep -v grep | grep -v "$0" | grep "${ORAHOME}"
  exit 1
fi
CUR_DIR=$(pwd)
cd /u01/app/oracle/
sudo -u oracle "${ORAHOME}/oui/bin/detachHome.sh"
cd ${CUR_DIR}
rm -rf "${ORAHOME}"
PARENT=$(dirname "${ORAHOME}")
if [ $(ls $PARENT | wc -l) -eq 0 ] ;then
  rmdir $PARENT
fi
