#!/usr/bin/env python
import hashlib
def hash_for_file(fname, block_size=2**20):
  md5 = hashlib.md5()
  with open(fname, 'rb') as f:
    while True:
      data = f.read(block_size)
      if not data:
        break
      md5.update(data)
  return md5.digest()

if __name__ == "__main__":
  import argparse
  import os
  import sys
  import re
  import datetime
  parser = argparse.ArgumentParser(description='Sorts files in folders by YEAR/MONTH/DAY and places in subfolders according')
  parser.add_argument('-a', '--all', dest='all', action='store_true', help='Also process files that already seem to be in a Y/M/D location.')
  parser.add_argument('-c', '--clean', dest='clean', action='store_true', help='Clean duplicate files.')
  parser.add_argument('-q', '--quick', dest='quick', action='store_true', help='Dont compare file hashes. Rely on filesize solely.')
  parser.add_argument('args', nargs=argparse.REMAINDER)
  args = parser.parse_args()
  rootfolders = args.args
  if len(rootfolders) == 0:
    print("Please specify folder to proces")
    sys.exit(1)

  cleaned_dirs=[]
  YMD_sub_re=re.compile('\\b[0-9]{4}(/+[0-9]{2}){2}\\b')
  YMD_re=re.compile('^[0-9]{4}(/+[0-9]{2}){2}$')
  for r in rootfolders:
    r = os.path.abspath(r) + '/'
    for d,subs,files in os.walk(r):
      reldir=d[len(r):]
      if YMD_re.search(reldir):
        print('Folder {0} was already sorted. Skipping.'.format(d))
        continue
      elif YMD_sub_re.search(reldir) and not args.all:
        print('Folder {0} seems to be in an Y/M/D structure. Skipping. Please use -a to proces these too...'.format(d))
        continue
      else:
        empty=True
        for f in files:
          src = os.path.abspath(os.path.join(d,f))
          src_stat = os.stat(src)
          mtime=datetime.datetime.fromtimestamp(src_stat.st_mtime)
          year,month,day = str(mtime.year), "{0:02d}".format(mtime.month), "{0:02d}".format(mtime.day)
          dest = os.path.abspath("{0}{1}/{2}/{3}/{4}".format(r,year,month,day,f))
          if src == dest:
            pass
          elif os.path.exists(dest):
            dest_stat = os.stat(dest)
            if os.path.islink(src):
              if args.clean:
                print("Cleaning symlink '{0}' ".format(src))
                os.remove(src)
              else:
                print("Not moving '{0}' to '{1}' (src=symlink, dest=actual file)".format(src,dest))
                empty=False
            elif os.path.islink(dest):
              print("mv '{0}' '{1}' (replace symbolic link by actual file)".format(src, dest))
              os.renames(src, dest)
            elif src_stat == dest_stat:
              if args.clean:
                print("Cleaning '{0}' (same inode as dest '{1}') ".format(src, dest))
                os.remove(src)
              else:
                print("Not moving '{0}' to '{1}' (src and dest are same inode, use -c to clean)".format(src,dest))
            elif src_stat.st_size != dest_stat.st_size:
              print("Not moving '{0}' to '{1}' (both exist with different size)".format(src,dest))
              empty=False
            elif args.clean:
              if args.quick:
                print("Cleaning '{0}' (same size as dest '{1}') ".format(src, dest))
                os.remove(src)
              elif hash_for_file(src) != hash_for_file(dest):
                empty=False
                print("Not moving '{0}' to '{1}' (both exist with different hash digest)".format(src,dest))
                continue
              else:
                print("Cleaning '{0}' (same hash digest as dest '{1}') ".format(src, dest))
                os.remove(src)
            else:
              empty=False
              print("Could not move '{0}'. Dest '{1}' already exists.".format(src,dest))
          else:
            print("mv '{0}' '{1}'".format(src, dest))
            os.renames(src, dest)
        if empty:
          cleaned_dirs.append(d)
  for d in cleaned_dirs[::-1]:
    if os.path.isdir(d):
      try:
        os.rmdir(d)
        print("Cleaned folder '{0}' (all files where processed).".format(d))
      except:
        pass
