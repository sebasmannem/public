#!/bin/sh
for src in Media/Foto Media/Muziek Werkmap
do
  echo "Syncing $src"
  rsync -av /u02/nas/$src/ /u01/$src/
done
