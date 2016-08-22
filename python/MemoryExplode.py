#!/usr/bin/python

if __name__ == "__main__":
  import os
  import signal 
  import sys
  import time

  def signal_term_handler(signal, frame):
#    print 'got SIGTERM'
    sys.exit(0)

  signal.signal(signal.SIGTERM, signal_term_handler)

  from optparse import OptionParser, OptionGroup

  parser = OptionParser()
  parser.add_option("-p", "--parallel", dest="parallel", type="int", help="Set the number of parallel child processes to run.", default=1)
  parser.add_option("-b", "--bs", dest="blocksize", type="int", help="Size of random data block.", default=2**10)
  parser.add_option("-c", "--count", dest="count", type="int", help="number of random blocks to keep in memory.", default=2**10)
  parser.add_option("-n", "--nice", dest="nice", type="float", help="number of seconds it takes for one full round. 0 is as fast as possible.", default=0)

  (options, args) = parser.parse_args()
  if options.nice >0:
    timeout=options.nice/options.count
    print timeout
  else:
    timeout=0

  try:
    children=set()
    for i in range(options.parallel):
      child=os.fork()
      if child==0:
        children=set()
        s=[]
        now=time.time()
        while True:
          for i in range(1,options.count+1):
            #s.append(os.urandom(options.blocksize))
            s.append(range(i,i+13*options.blocksize,13))
            s=s[-options.count:]
            time.sleep(timeout)
#          sys.stdout.write('*')
#          sys.stdout.flush()
          prev, now = now, time.time()
          print int(now-prev)
      else:
        children.add(child)
    os.wait()

  except (SystemExit,KeyboardInterrupt):
    for c in children:
      os.kill(c, signal.SIGTERM)
  sys.exit(0)
