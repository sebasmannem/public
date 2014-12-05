#!/usr/bin/python3

class NWConfig():
  def ip_to_int(self, ip):
    if type(ip) is int:
      return ip
    if type(ip) is str:
      ip_ar = ip.split(".")
      if len(ip_ar) != 4:
        raise Exception("Invalid IP: {0}. We need 4 numbers in an IP".format(ip))
      ip=0
      for i in ip_ar:
        try:
          i=int(i)
        except:
          raise Exception("IP part {0} must be numeric".format(i))
        if i<0 or i>255:
          raise Exception("IP part {0} must be from 0-255".format(i))
        ip=ip*256+i
      return ip
    raise Exception("{0} has an invalid type for an IP.".format(ip.__repr__()))

  def int_to_ip(self,i):
    try:
      i = int(i)
    except:
      raise Exception("{0} is not an integer.".format(i.__repr__()))
    ip = ""
    for x in range(4):
      ip += "." + str(int(i/2**(8*(3-x)) % 256))
    return ip[1:]

  def base_to_netmask(self, base):
    if type(base) is str:
      base=base.replace('/','')
    try:
      base=int(base)
    except:
      raise Exception("invalid numeric expression for network base {}".format(base))
    return (2**base-1) * 2** (32-base)

  def network(self):
    return self.int_to_ip(self.__ip & self.__netmask)

  def gateway(self):
    return self.int_to_ip((self.__ip & self.__netmask)+1)

  def broadcast(self):
    #eerst network adress
    t = self.__ip & self.__netmask
    #daarna inverse van netmask erbij optellen
    t += self.__netmask ^ (2 ** 32 - 1)
    return self.int_to_ip(t)

  def netmask(self):
    return self.int_to_ip(self.__netmask)

  def ip(self):
    return self.int_to_ip(self.__ip)

  def __init__(self,ip,netmask,base=None):
    if "/" in ip:
      ip, base = ip.split("/")
    if netmask:
      self.__netmask=self.ip_to_int(netmask)
    else:
      self.__netmask = self.base_to_netmask(base)
    self.__ip = self.ip_to_int(ip)

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("--hostname", dest="hostname", help="Set the hostname.", default='new.mannem.nl')
  parser.add_option("--ip", dest="ip", help="Set the ip.", default='192.168.0.2')
  parser.add_option("--netmask", dest="netmask", help="Set the netmask.")
  parser.add_option("--base", dest="base", type="int", help="Set the base of the network.", default=24)


  (options, args) = parser.parse_args()
  NW = NWConfig(options.ip, options.netmask, options.base)
  print("IP:{0}".format(NW.ip()))
  print("network:{0}".format(NW.network()))
  print("netmask:{0}".format(NW.netmask()))
  print("gateway:{0}".format(NW.gateway()))
  print("broadcast:{0}".format(NW.broadcast()))
  print("hostname:{0}".format(options.hostname))

  hn=open('/tmp/etc/hostname','w')
  hn.write(options.hostname)
  hn.close()

#  nwconf = open('/mnt/etc/conf.d/network\@eth0')
  nwconf = open('/tmp/network\@eth0')
  nwconf.write('''address={0}
netmask={1}
broadcast={2}
gateway={3}'''.format(NW.ip(),NW.netmask(),NW.broadcast(),NW.gateway()))
  nwconf.close()
