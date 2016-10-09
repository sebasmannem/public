#!/usr/bin/python
if __name__ == "__main__":
  from NetworkInfo import NWConfig
  import re
  from sys import stdin
  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("--hostname", dest="hostname", help="Set the hostname.",default='new.mannem.nl')
  parser.add_option("--ip", dest="ip", help="Set the ip.",default='192.168.0.2')
  parser.add_option("--netmask", dest="netmask", help="Set the netmask.")
  parser.add_option("--base", dest="base", type="int", help="Set the base of the network.", default=24)

  (options, args) = parser.parse_args()
  re_IP=re.compile('([a-zA-Z]+)(:| +)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
  re_HN=re.compile('[a-zA-Z0-9.]+')
  networks={}
  for l in stdin:
    m=re_HN.match(l)
    if m:
      HN=m.group(0)
    info={}
    m=re_IP.findall(l)
    if len(m) > 0:
      for e in m:
        info[e[0]] = e[2]
      cnf=NWConfig(info['addr'],info['Mask'])
      try:
        networks[cnf.network()].append((cnf.ip(),cnf.netmask(),HN))
      except:
        networks[cnf.network()] = [(cnf.ip(),cnf.netmask(),HN)]

  for n in sorted(networks.keys()):
    print (n+":")
    for s in sorted(networks[n], key=lambda tup: tup[0]):
      print ("  {0:15} {1:15} {2}".format(*s)) 

