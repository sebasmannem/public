#!/bin/sh
[ "$?" -lt 1 ] || exit 1

for i
do
  if [ -f "$i" ]; then
    f=$(basename "$i")
    d=$(dirname "$i")
    ext=$(echo $f | sed 's/^.*\.//')
    new=$d/$(echo "$f" | sed 's/\.[^.]*$//' | rev).$ext
    echo "Moving '$d/$f' to '$new'"
    mv "$d/$f" "$new"
  else
    echo "File '$i' does not exist."
  fi
done
