#!/bin/python2
if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from glob import iglob
  from os import path, remove
  from datetime import datetime
  import gzip

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-c", "--compress", dest="compress", type="int", help="Compress the output files.", default=0)
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
      if infile[-11:] in ('.totals.log','.totals.log.gz'):
        print("Skipping {0}".format(infile))
        continue
      mdate=datetime.fromtimestamp(path.getmtime(infile)).strftime("%Y%m%d")
      outfile='{0}/{1}{2}.totals.log'.format(d,options.prefix,mdate)
      if options.compress: outfile+='.gz'
      try:
        fo=outfiles[outfile]
      except:
        print(" > "+outfile)
        if options.compress>0:
          fo = gzip.open(outfile,'a',options.compress)
        else:
          fo = open(outfile,'a')
        outfiles[outfile]=fo
      
      with open(infile) as fi:
        for line in fi:
          fo.write(line)
      print("File {0} Done".format(infile))
      remove(infile)

    for outfile, fo in outfiles.items():
      fo.close()
