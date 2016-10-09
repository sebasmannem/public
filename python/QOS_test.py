#!/usr/bin/python

suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
def humansize(nbytes):
  if nbytes == 0: return '0 B'
  i = 0
  while nbytes >= 1024 and i < len(suffixes)-1:
    nbytes /= 1024.
    i += 1
  f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
  return '%s %s' % (f, suffixes[i])

def log(msg):
  for o in log_streams:
    o.write('{0}: {1}\n'.format(time.time(), msg))
    o.flush()

if __name__ == "__main__":
  import os
  import signal 
  import sys
  import time
  import socket

  def signal_term_handler(signal, frame):
    sys.exit(0)

  signal.signal(signal.SIGTERM, signal_term_handler)

  from optparse import OptionParser, OptionGroup

  parser = OptionParser()
  parser.add_option("-p", "--parallel", dest="parallel", type="int", help="Set the number of parallel child processes to run.", default=1)
  parser.add_option("-b", "--bs", dest="blocksize", type="int", help="Size of random data block.", default=2**10)
  parser.add_option("-t", "--target", dest="target", help="For a Sender, please specify a hostname or IP. Without target a receiver is started.", default='')
  parser.add_option("-d", "--display_seconds", dest="display_seconds", help="Number of seconds between printing status rows. <1 disables output.", default=10)
  parser.add_option("-l", "--logfile", dest="logfile", help="logfile to write log to.", default='')
  parser.add_option("--start_port", dest="start_port", type="int", default=2024, help="Port to use for first subproces.")

  (options, args) = parser.parse_args()
  port=options.start_port
  if options.target == '':
    tp='receivers'
  else:
    tp='senders to '+options.target
  hbs=humansize(options.blocksize)

  log_streams = [sys.stdout]
  if options.logfile != '':
    log_streams.append(open(options.logfile, 'a'))

  log("Starting {0} {1}.".format(options.parallel, tp))
  try:
    children=set()
    for i in range(options.parallel):
      child=os.fork()
      if child==0:
        children=set()
        i=0.0
        if options.target == '':
          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.bind(('', port))
          while True:
            s.listen(1)
            prev = now = time.time()
            conn, addr = s.accept()
            cli_addr, cli_port = addr
            log('Connected on port {0} by {1}:{2}.'.format(port, cli_addr, cli_port))
            while True:
              data = conn.recv(options.blocksize)
              i+=len(data)
              now = time.time()
              if now - prev > options.display_seconds and options.display_seconds > 0:
                log("Received {0} in {1} msec from port {2} ({3}/sec.).".format(humansize(i), int((now-prev)*10**3), port, humansize(i/(now-prev))))
                i=0.0
                prev = now
              if not data: break
        else:
          data='\0'*options.blocksize
          while True:
            try:
              s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
              s.connect((options.target, port))
              prev = time.time()
              while True:
                i+=s.send(data)
                now = time.time()
                if now - prev > options.display_seconds and options.display_seconds > 0:
                  log("Sent {0} in {1} msec to port {2} ({3}/sec.).".format(humansize(i), int((now-prev)*10**3), port, humansize(i/(now-prev))))
                  i=0.0
                  prev = now

            except socket.error:
              if i>0:
                log("Sent {0} in {1} msec to port {2} ({3}/sec.).".format(humansize(i), int((now-prev)*10**6), port, humansize(i/(now-prev))))
                i=0.0
                log('socket error on port {0}. retrying every 1 seconds'.format(port))
              s.close()
              time.sleep(1)

      else:
        children.add(child)
        port+=1
    os.wait()

  except (SystemExit,KeyboardInterrupt):
    for c in children:
      os.kill(c, signal.SIGTERM)
  sys.exit(0)
