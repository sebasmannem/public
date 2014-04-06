#!/bin/python3
if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from glob import iglob
  from os import path, remove
  from datetime import datetime

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-c", "--compress", dest="compress", help="Compress the output files (default).", default=False)
  parser.add_option("-d", "--date_sort", dest="datesort", help="Sort files by date. Also output daily to different file.", default=True)
  parser.add_option("-f", "--filter", dest="filter", default='*', help="Filter on filenames.")
  parser.add_option("-p", "--prefix", dest="prefix", default='', help="Prefix the destination files.")

  group = OptionGroup(parser, "All other options", "All other options are considered folders to be cleaned up.")
  parser.add_option_group(group)

  (options, args) = parser.parse_args()
  if options.prefix != '': options.prefix=options.prefix+'_'
  i=0
  outfiles = {}
  for d in args:
    for infile in iglob(d+'/'+options.filter):
      if infile[-11:] == '.totals.log':
        print("Skipping {0}".format(infile))
        continue
      mdate=datetime.fromtimestamp(path.getmtime(infile)).strftime("%Y%m%d")
      outfile='{0}/{1}{2}.totals.log'.format(d,options.prefix,mdate)
      try:
        fo=outfiles[outfile]
      except:
        print(" > "+outfile)
        fo = open(outfile,'a')
        outfiles[outfile]=fo
      
      with open(infile) as fi:
        for line in fi:
          fo.write(line)
      print("File {0} Done".format(infile))
      remove(infile)

    for outfile, hnd in outfiles.items():
      hnd.close()
