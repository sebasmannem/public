#!/bin/env python

'''
Aanpassingen die gedaan zijn voor RH5 complency:
.format is aangepast naar "" % () of naar ""+""
  print("Cleaned {0} files.".format(cleaned)) -> print("Cleaned %d files." % cleaned)
  outfile="{0}/{1}{2}.totals.log".format(fldr,options.prefix,mdate) -> outfile=fldr+'/'+options.prefix+mdate+'.totals.log'
onder RH5 wordt glob gebruikt ipv iglob
with open().. is aangepast naar try .. finally ...
'''
def CleanFolder(fldr):
  if fldr[-1]=='\n': fldr=fldr[0:-1]
  cleaned=0
  print("Cleaning folder %s" % fldr)
  files=[]
  for infile in iglob(fldr+'/'+options.filter):
    if infile[-11:] == '.totals.log' or infile[-14:] == '.totals.log.gz':
      if options.verbose: print("Skipping %s" % infile)
      continue
    mdate=path.getmtime(infile)
    files.append((infile,mdate))

  if options.datesort:
    files.sort(key=lambda x: x[1])
  else:
    files.sort()

  for file in files:
    infile,mtime=file
    mdate=datetime.fromtimestamp(mtime).strftime("%Y%m%d")
    outfile=fldr+'/'+options.prefix+mdate+'.totals.log'
    if options.compress>0: outfile+='.gz'
    try:
      fo=outfiles[outfile]
    except:
      if options.verbose: print(" > "+outfile)
      if options.compress>0:
        fo = gzip.open(outfile,'a',options.compress)
      else:
        fo = open(outfile,'a')
      outfiles[outfile]=fo

    try:
      fi=open(infile)
      for line in fi:
        fo.write(line)
    finally:
      fi.close()
    if options.verbose: print("File "+infile+" Done")
    remove(infile)
    cleaned+=1
  print("Cleaned %d files." % cleaned)
  for outfile, fo in outfiles.items():
    fo.close()

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from sys import stdin, hexversion
  import gzip
  from os import path

  #Onder RH5 werkt iglob niet. Grmbl...
  if hexversion < 33949424:
    from glob import glob as iglob
  else:
    from glob import iglob

  from os import path, remove
  from datetime import datetime

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-z", "--compress", "--zip", dest="compress", type="int", help="Set the compression level (gzip) for the output files. 0 (default) is no encryption.", default=0)
  parser.add_option("-d", "--date_sort", action="store_true", dest="datesort", help="Sort files by date. Also output daily to different file.", default=False)
  parser.add_option("-f", "--filter", dest="filter", default='*', help="Filter on filenames.")
  parser.add_option("-p", "--prefix", dest="prefix", default='', help="Prefix the destination files.")
  parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Show verbose output.")

  group = OptionGroup(parser, "All other options", "All other options are considered folders to be cleaned up.")
  parser.add_option_group(group)

  (options, args) = parser.parse_args()
  if options.prefix != '': options.prefix=options.prefix+'_'
  outfiles = {}
  if args:
    for d in args:
      CleanFolder(d)
  else:
    for d in stdin:
      CleanFolder(d)
