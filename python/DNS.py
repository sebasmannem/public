#!/usr/bin/python
import socket
import re

re_ip = re.compile('^([0-9]{1,3})(?:\.[0-9]{1,3}){3}$')

def DNSInfo(qry):
  #Nope. DNS en reverse DNS terug zoeken.
  try:
    hostinfo = socket.gethostbyaddr(qry)
    return hostinfo
  except Exception as e:
    pass

  #Nope. DNS zodner reverse DNS?
  try:
    #Als reverse DNS niet goed is ingesteld, geeft gethostbyaddr een fout, maar kan wellicht nog wel een IP opgezocht worden.
    hostinfo = socket.gethostbyname_ex(qry)
    return hostinfo
  except:
    pass

  #Nope. IP adres zonder reverse DNS?
  if re_ip.match(qry):
    return qry, (qry,), (qry,)

  #Nou ik weet het echt niet meer. Unresolvable...
  raise socket.error()

if __name__ == "__main__":
  import socket
  import sys
  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-b", "--bare", action='store_true', dest="bare", default=False, help="Use bare output instead of table format.")

  (options, args) = parser.parse_args()

  if options.bare:
    out="{0} {1}\n"
  else:
    out="| {0:43} | {1:35} | {2:43} | {3:15} |"
    length=len(out.format(1,2,3,4))
    out+="\n"
    sys.stdout.write("-"*length+'\n')
    sys.stdout.write(out.format('query','hostname','alias','ipaddr'))
    sys.stdout.write("-"*length+'\n')

  for qry in sys.stdin:
    qry=qry[:-1]
    try:
      hostname, aliaslist, ipaddrlist=DNSInfo(qry)
    except socket.error as e:
      sys.stderr.write(out.format(qry,'error occurred.',e.strerror,str(e.errno)))
      continue
    if len(aliaslist) == 0:
      aliaslist.append('')
    if len(ipaddrlist) == 0:
      ipaddrlist.append('')
    for ipaddr in ipaddrlist:
      if options.bare:
        sys.stdout.write(out.format(ipaddr,hostname))
      else:
        for alias in aliaslist:
          sys.stdout.write(out.format(qry,hostname,alias,ipaddr))

  if not options.bare:
    sys.stdout.write("-"*length+'\n')

