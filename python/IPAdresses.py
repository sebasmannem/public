#!/usr/bin/python

# Use those functions to enumerate all interfaces available on the system using Python.
# found on <http://code.activestate.com/recipes/439093/#c1>

import socket
import fcntl
import struct
import array

def all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    lst = []
    for i in range(0, outbytes, 40):
        name = namestr[i:i+16].split('\0', 1)[0]
        ip   = namestr[i+20:i+24]
        lst.append((name, format_ip(ip)))
    return lst

def format_ip(addr):
    return str(ord(addr[0])) + '.' + \
           str(ord(addr[1])) + '.' + \
           str(ord(addr[2])) + '.' + \
           str(ord(addr[3]))

if __name__ == "__main__":
  from optparse import OptionParser
  import re
  import subprocess
  import sys

  parser = OptionParser(usage='''Run this script on a forwarding server  to configure IP forwarding.
All packets from Source that reach the bridge server, will be rerouted to destination.
Usage: %prog [options] [folders]''')
  '''
  parser.add_option("-s", "--source", dest="source", help="")
  parser.add_option("-d", "--dest", "--destination", dest="destination", help="Destination DNS or IP to wich packets should be rerouted. DNS would be resolved to IP.")
  parser.add_option("-b", "--bridge", dest="bridge", default='', help="Bridge device. Mostly is eth0. If not provided, hostname is resolved to IP and device with this IP attached is used.")
  parser.add_option("--duplex", dest="duplex", action="store_true", default=False, help="Also forward from dest to source.")
  parser.add_option("-c", "--clean", dest="clean", action="store_true", default=False, help="Only clean out existing rules if they may exist.")
  (options, args) = parser.parse_args()
  '''
  IP_re=re.compile('^([0-9]{1,3}.){3}[0-9]{1,3}$')
  ifcs =  all_interfaces()
  l=["%s=%s" % (iface[0], iface[1]) for iface in all_interfaces()]
  
  print (",".join(l))
    
