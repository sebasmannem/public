#!/bin/sh
logfile=/var/tmp/$(basename ${0}).log
mkdir -p "$(dirname $logfile)"
[ -f "$logfile" -a $(date +%u) -eq 7 ] && rm "$logfile"
find /u01/Media/Videos/Series -regextype posix-extended -iregex '.*\.(mkv|avi)' | while read f
do 
  s=$(echo "$f" | sed 's/\.[a-zA-Z]*$//')
  [ -f "$s.srt" ] && continue
  [ -f "$s.sub" ] && continue
  grep -q "$s.srt" "$logfile" && continue
  echo -n "Looking for '$s.srt'" | tee -a "$logfile"
  echo >> "$logfile"
  { time submarine -l dut -l eng -q "$f"; } >> "$logfile" 2>&1
  { [ -f "$s.srt" ] && echo " OK" || echo " Not found"; } | tee -a "$logfile"
done
