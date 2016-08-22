#!/bin/sh
/sbin/fdisk -lu 2>&1 | awk '/^\/dev/{sub(/\*/," ");if ($2%8 != 0) print $0}'
