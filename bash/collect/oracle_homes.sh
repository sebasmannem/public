#!/bin/sh
[ -f /etc/oratab ] && sed -r -n 's/#.*//;s/:/ /g;/D[0-9]{3}[OTAP]/p' /etc/oratab
