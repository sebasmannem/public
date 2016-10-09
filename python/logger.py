#!/bin/env python

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from sys import stdin,stdout,stderr

  from datetime import datetime

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-f", "--file", dest="logfile", help="The file where the entries should be written to.", default='/dev/null')
  parser.add_option("-t", "--tag", dest="tag", default='', help="Add one or more tags to the lines.")
  parser.add_option("-o", "--output", action="store_true", dest="output", default=False, help="Also print to stdout.")
  parser.add_option("-e", "--error", action="store_true", dest="error", default=False, help="Also print to stderr.")

  (options, args) = parser.parse_args()
  if options.tag:
    output="{0} {1} {2}"
  else:
    output="{0} {2}"
  while True:
    line = stdin.readline()
    if not line:
      break
    dest=open(options.logfile,'a+')
    try:
      dest.write(output.format(datetime.today().strftime('%Y-%m-%d %H:%M:%S'),options.tag,line))
      if options.output: stdout.write(line)
      if options.error: stderr.write(line)
    finally:
      dest.close()
