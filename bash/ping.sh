#!/bin/sh
pingTest()
{
  address=$1
  count=5
  res=`ping -c $count $address 2>&1 | awk '/packets transmitted, .* received, /{print $4}'`
  test "$res" -eq "$res" 2>/dev/null
  if [ $? -eq 0 ]; then
    if [ $res -eq $count ]; then
      echo Successful ping to $address
    else
      logger -s -t pingTest -- "Error occured during ping of '$address'. $res of $count where received."
    fi
  else
    logger -s -t pingTest -- "Error occured during ping of '$address'"
  fi
}

pingTest 192.168.254.1
pingTest 192.168.1.1
pingTest www.google.nl
pingTest 192.168.254.200
logger -t pingTest -- "pingTest finished..."
