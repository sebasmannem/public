#!/bin/env python
def CleanFolder(fldr):
  if fldr[-1]=='\n': fldr=fldr[0:-1]
  cleaned=0
  print("Cleaning folder {0}".format(fldr))
  files=[]
  for infile in iglob(fldr+'/'+options.filter):
    if infile[-11:] == '.totals.log' or infile[-14:] == '.totals.log.gz':
      if options.verbose:
        print("Skipping {0}".format(infile))
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
    outfile='{0}/{1}{2}.totals.log'.format(fldr,options.prefix,mdate)
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

    with open(infile) as fi:
      for line in fi:
        fo.write(line)
    if options.verbose: print("File {0} Done".format(infile))
    remove(infile)
    cleaned+=1
  print("Cleaned {0} files.".format(cleaned))
  for outfile, of in outfiles.items():
    of.close()

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from glob import iglob
  from os import path, remove
  from datetime import datetime
  import gzip
  from sys import stdin

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
