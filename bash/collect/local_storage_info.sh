#!/bin/sh
for MP in $(ls / | grep u0)
do
  echo $(hostname) ${TYPE} $(mount | awk '$3~/'${MP}'/{print $3,$5}') $(df /${MP} | tail -n1)
done
