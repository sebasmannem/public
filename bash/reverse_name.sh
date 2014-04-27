#!/bin/sh
[ "$?" -lt 1 ] || exit 1

for i
do
  if [ -f "$i" ]; then
    f=$(basename "$i")
    d=$(dirname "$i")
    ext=.$(echo $f | sed 's/^.*\.//')
    [ ${#f} -eq ${#ext} ] && ext=""
    f=$(basename "$f" "$ext")
  elif [ -d "$i" ]; then
    f=$(basename "$i")
    d=$(dirname "$i")
    ext=""
  else
    echo "File '$i' does not exist."
    continue
  fi

  new=$d/$(echo "$f" | rev)
  echo "Moving '$d/$f$ext' to '$new$ext'"
  mv "$d/$f$ext" "$new$ext"
done
