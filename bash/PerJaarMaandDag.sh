#!/bin/sh

processFolder()
{
  root=$1
  path=$2
  FILES=$path/*
  for file in $FILES #`ls -Q -d $path/*`
  do
    echo "$file"
    base=`basename $file`
    if [ -d $file ]
    then
      if [ ${#base} -ne 4 -o `expr substr $base 1 2` != "20" ]
      then
        path=$file
        processFolder "$root" "$file"
        rmdir $path
        path=`dirname $path`
      fi
    elif [ -f $file ]
    then
      Created=`exif -t 0x9003 $file 2>/dev/null | grep Value | cut -c10-100`
      [ "$Created" = "" ] && Created=`stat -c %y $file`
      Year=`echo "$Created" | cut -c1-4`
      Month=`echo "$Created" | cut -c6-7`
      Day=`echo "$Created" | cut -c09-10`

      mkdir -p $root/$Year/$Month/$Day
      mv "$file" "$root/$Year/$Month/$Day/"
    fi
  done
}

if [ $# -lt 1 ]; then
  echo "Please specify folder to process"
  exit 1
elif [ -d $1 ]; then
  processFolder "$1" "$1"
else
  echo "unknown folder $1"
fi
