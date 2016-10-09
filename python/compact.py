#!/usr/bin/python
def main(argv):
 global interval
 interval = 3600
 try:
  opts, args = getopt.getopt(argv[1:], "hs:d:i:", ["help", "source=", "dest=", "interval="])
  for opt, arg in opts:
   if opt in ("-h", "--help"):
    usage(argv[0])
    sys.exit()
   elif opt in ('-s', '--source'):
    global source
    source = arg
   elif opt in ("-d", "--dest"):
    global dest
    dest = arg
   elif opt in ("-i", "--interval"):
    interval = float(arg)
  if 'source' not in globals():
   usage(sys.argv[0])
   sys.exit(2)
 except:
  usage(sys.argv[0])
  sys.exit(2)

def usage(scriptname):
 print """'{0}' can be used with the following options:
-h, --help                     : Show this usage info.
-s [source], --source=[source] : The source file that will be read.
-d [dest], --dest=[dest]       : The destination file to wich will be written.
Source is mandatory.\nWithout a destination, output will be written to stdout.""".format(scriptname)

import sys, getopt, string
from datetime import datetime, date, time

if __name__ == "__main__":
 main(sys.argv)

try:
 fhSource = open(source,'r')
except IOError:
 print "Could not open "+source

for line in fhSource:
 try:
  cols = string.split(line, ' ')
  server = cols[1]
  linedate = datetime.strptime(cols[1]+' '+cols[2], '%Y-%m-%d %H:%M:%S')
  groupby = int(float(linedate.strftime("%s")) / interval)
  if server != pserver:
   
  elif groupby == pgroupby:
   
  else
   

 except:
  continue
 print groupby
