#!/usr/bin/python

'''
IPTABLES="/sbin/iptables"
INT="eth0"

# source1 (srv1)
SOURCE1="192.168.2.100"
# source2 (srv2)
SOURCE2="192.168.2.101"
# bridge1 (srv3)
BRIDGE1="192.168.3.103"
# target1 (srv4)
TARGET1="192.168.4.104"
# target1 (srv5)
TARGET2="192.168.4.105"

# enable ip routing
sysctl -w net.ipv4.ip_forward=1

# define nat rules
${IPTABLES} -t nat -A PREROUTING -i $INT -s ${SOURCE1} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${TARGET1}
${IPTABLES} -t nat -A POSTROUTING -s ${SOURCE1} -d ${TARGET1} -j SNAT -p tcp --to-source=${BRIDGE1}
${IPTABLES} -t nat -A OUTPUT -s ${SOURCE1} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${TARGET1}

${IPTABLES} -t nat -A PREROUTING -i $INT -s ${SOURCE2} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${TARGET2}
${IPTABLES} -t nat -A POSTROUTING -s ${SOURCE2} -d ${TARGET2} -j SNAT -p tcp --to-source=${BRIDGE1}
${IPTABLES} -t nat -A OUTPUT -s ${SOURCE2} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${TARGET2}

${IPTABLES} -t nat -A PREROUTING -i $INT -s ${TARGET1} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${SOURCE1}
${IPTABLES} -t nat -A POSTROUTING -s ${TARGET1} -d ${SOURCE1} -j SNAT -p tcp --to-source=${BRIDGE1}
${IPTABLES} -t nat -A OUTPUT -s ${TARGET1} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${SOURCE1}

${IPTABLES} -t nat -A PREROUTING -i $INT -s ${TARGET2} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${SOURCE2}
${IPTABLES} -t nat -A POSTROUTING -s ${TARGET2} -d ${SOURCE2} -j SNAT -p tcp --to-source=${BRIDGE1}
${IPTABLES} -t nat -A OUTPUT -s ${TARGET2} -d ${BRIDGE1} -j DNAT -p tcp --to-destination ${SOURCE2}

'''


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
  parser.add_option("-s", "--source", dest="source", help="Source DNS or IP from wich packets should be rerouted. DNS would be resolved to IP.")
  parser.add_option("-d", "--dest", "--destination", dest="destination", help="Destination DNS or IP to wich packets should be rerouted. DNS would be resolved to IP.")
  parser.add_option("-b", "--bridge", dest="bridge", default='', help="Bridge device. Mostly is eth0. If not provided, hostname is resolved to IP and device with this IP attached is used.")
  parser.add_option("--duplex", dest="duplex", action="store_true", default=False, help="Also forward from dest to source.")
  parser.add_option("-c", "--clean", dest="clean", action="store_true", default=False, help="Only clean out existing rules if they may exist.")

  (options, args) = parser.parse_args()

  IP_re=re.compile('^([0-9]{1,3}.){3}[0-9]{1,3}$')
  if not options.source:
    print 'Please specify a source and destination (at minium)'
    sys.exit(1)
  elif IP_re.search(options.source):
    src = options.source
  else:
    src = socket.gethostbyname(options.source)

  if not options.destination:
    print 'Please specify a source and destination (at minium)'
    sys.exit(1)
  elif IP_re.search(options.destination):
    dst = options.destination
  else:
    dst = socket.gethostbyname(options.destination)

  if options.bridge == '':
    bridgeip = socket.gethostbyname(socket.gethostname())
  elif IP_re.search(options.destination):
    bridgeip = options.bridge
  else:
    bridgeip = socket.gethostbyname(options.bridge)

  for i in all_interfaces():
    if i[1] == bridgeip:
      bridgedev = i[0]
      break

  for action in ('-D', '-A'):
    if action == '-D':
      action_desc = 'Removing'
    else:
      action_desc = 'Creating'

    for i in range(2):
      print "{0} forwarding rule for {1} to {2} on device {3} (IP {4})".format(action_desc, src, dst, bridgedev, bridgeip)
      subprocess.call(['/sbin/iptables', '-t', 'nat', action, 'PREROUTING', '-i', bridgedev, '-s', src, '-d', bridgeip, '-j', 'DNAT', '-p', 'tcp', '--to-destination', dst])
      subprocess.call(['/sbin/iptables', '-t', 'nat', action, 'POSTROUTING', '-s', src, '-d', dst, '-j', 'SNAT', '-p', 'tcp', '--to-source', bridgeip])
      subprocess.call(['/sbin/iptables', '-t', 'nat', action, 'OUTPUT', '-s', src, '-d', bridgeip, '-j', 'DNAT', '-p', 'tcp', '--to-destination', dst])
      if not options.duplex:
        break
      src, dst= dst, src
    if options.clean:
      break
