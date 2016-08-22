#!/bin/sh
/stage/linuxbeheer/netapp/santools/sanlun lun show | awk 'BEGIN{IGNORECASE=1}/pfas/{printf("%10s:%-60s %4s\n",$1,$2,$6)}' | sort -u
