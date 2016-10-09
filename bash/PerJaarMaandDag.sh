#!/bin/sh

processFolder()
{
  root="$1"
  path="$2"
  ls -a "$path"/ 2>/dev/null | while read file
  do
    [ "$file" = "." -o "$file" = ".." ] && continue
    echo -n "$path/$file"
    if [ -d "$path/$file" ]
    then
      base=$(basename "$file")
      echo "$file" | grep -qE '^[0-9]{4}$' && { echo " (folder - Looks like a year. Skipping.)" ; continue ; }

      echo " (folder)"
      path="$file"
      processFolder "$root" "$path/$file"
      rmdir "$path"
      path=$(dirname "$path")
    elif [ -f "$path/$file" ]
    then
      echo " (file)"
      Created=$(exif -t 0x9003 "$file" 2>/dev/null | grep Value | cut -c10-100)
      [ "$Created" = "" ] && Created=$(stat -c %y "$file")
      Year=`echo "$Created" | cut -c1-4`
      Month=`echo "$Created" | cut -c6-7`
      Day=`echo "$Created" | cut -c09-10`

      mkdir -p "$root/$Year/$Month/$Day"
      mv "$file" "$root/$Year/$Month/$Day/"
    else
      echo " (unknown)"
    fi
  done
}

if [ $# -lt 1 ]; then
  echo "Please specify folder to process"
  exit 1
elif [ -d "$1" ]; then
  processFolder "$1" "$1"
else
  echo "unknown folder '$1'"
fi
