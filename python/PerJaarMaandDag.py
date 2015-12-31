#!/bin/python

if __name__ == "__main__":
  import argparse
  import os
  import sys
  import re
  import datetime
  parser = argparse.ArgumentParser(description='Sorts files in folders by YEAR/MONTH/DAY and places in subfolders according')
#  parser.add_argument('--unit', metavar='U', type=str, default='G',help='SI Unit, [B]ytes, K, M, G, T, P',)
#  parser.add_argument('mount_point', metavar='PATH', type=str, default='/', help='BTRFS mount point', )
  parser.add_argument('args', nargs=argparse.REMAINDER)
  args = parser.parse_args()
  rootfolders = args.args
  if len(rootfolders) == 0:
    print("Please specify folder to proces")
    sys.exit(1)

  cleaned_dirs=[]
  YR_re=re.compile('[0-9]{4}')
  for r in rootfolders:
    if not r[-1] == '/': r+='/'
    for d,subs,files in os.walk(r):
      reldir=d[len(r):]
      if YR_re.match(reldir):
        if len(reldir) == 4:
          print('Folder: {0}: Looks like a year. Skipping.'.format(d))
        continue
      else:
        for f in files:
          src = "{0}/{1}".format(d,f)
          stat =os.stat(src)
          stat.st_ctime
          ctime=datetime.datetime.fromtimestamp(stat.st_ctime)
          year,month,day = str(ctime.year), "{0:02d}".format(ctime.month), "{0:02d}".format(ctime.day)
          dest = "{0}{1}/{2}/{3}/{4}".format(r,year,month,day,f)
          if os.path.exists(dest):
            print("Could not move '{0}'. Dest '{1}' already exists.".format(src,dest))
          else:
            print("mv '{0}' '{1}'".format(src, dest))
            os.renames(src, dest)
        cleaned_dirs.append(d)
'''
  for d in cleaned_dirs[::-1]:
    if os.path.is_dir(dest):
      try:
        os.rmdir(d)
      except:
        print("Could not clean up folder {0}. Please investigate".format(d))
'''


'''
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



'''
