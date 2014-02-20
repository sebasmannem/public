#!/bin/python2
import re
lvm_name_re = re.compile('\s*(\S*)\s*{')
lvm_pvs_re  = re.compile('physical_volumes\s*{[^{]*({[^{]*?}.*?)*}',re.S)
lvm_pv_re   = re.compile('\S+?\s*{[^{]*?}',re.S)
lvm_lvs_re  = re.compile('logical_volumes\s*{\s*(\S*\s*{.*?(segment[0-9]+\s*{.*?}.*?)+}.*?)*}',re.S)
lvm_lv_re   = re.compile('\S+?\s*{[^{]*?segment.*?{.*?}.*?}',re.S)


class blockdevice():
  name=''
  children={}
  parents={}
  aliases=set()

class lvmvg(blockdevice):
  '''Deze class representeerd een Volume group.'''
  def __init__(self,hdr):
    '''
    Deze functie initieerd een Volume Group.
    Hij wordt aangeroepen met een header (die uit een block device wordt gelezen).
    Op basis van de header bepaalt hij de naam van de VG en maakt de PV's en LV's aan.
    name wordt ingesteld op de naam van de VG.
    parents bevat alle Physical Volumes.
    children bevat alle Logical Volumes.
    Aliases bevat alle device names die leiden tot deze VG.
    Verder registreert hij zich bij de children van het object blockdevice en van het object lvmvg.
    '''

    '''reset de waarden, anders krijg je de children van het object type...'''
    children={}

    '''Bepaal de naam'''
    match = lvm_name_re.search(hdr)
    if match:
      self.name = match.group(1)
    if lvmvg.children.has_key(self.name):
      return lvmvg.children[self.name]
    else:
      lvmvg.children[self.name] = self
      bdname = "/dev/{0}".format(self.name)
      blockdevice.children[bdname] = self
      self.aliases.add(bdname)
      self.aliases.add(self.name)

    '''Bepaal de PV's'''
    match=lvm_pvs_re.search(hdr)
    if match:
      hdr=lvm_pvs_re.sub('',hdr)
      pvs=match.group(0)
      matches=lvm_pv_re.findall(pvs)
      for match in matches:
        pv=lvmpv(match)
        pv.children[self.name] = self
        self.parents[pv.name] = pv

    '''Bepaal de LV's'''
    match=lvm_lvs_re.search(hdr)
    if match:
      hdr=lvm_lvs_re.sub('',hdr)
      lvs=match.group(0)
      matches=lvm_lv_re.findall(lvs)
      for match in matches:
        lv=lvmlv(match)
        self.children[lv.name] = lv
    print "Resulting header:"
    print "-----------------"
    print hdr

class lvmpv(blockdevice):
  def __init__(self,hdr):
    print "Physical Volume:"
    for line in hdr.split('\n'):
      print line

class lvmlv(blockdevice):
  def __init__(self,hdr):
    print "Locical Volume:"
    for line in hdr.split('\n'):
      print line


def readdev(dev):
  blkid=Popen(args=['blkid',dev], bufsize=1, stdout=PIPE)


  if devtype=='LVM2_member':
    start=0x218
    lines=[]
    buffer=""
    f=open(dev,'r')
    f.seek(start,0)
    devtype=f.read(4)

    start=0x1200
    BS=0x200
    history=[]
    buffer=""
    f.seek(start,0)
    while 1:
      buffer+=f.read(BS)
      if buffer[-1] == "\0":
        history.append(buffer.replace("\0",""))
        buffer=f.read(BS)
        if buffer[0] == "\0":
          break
    device = lvmvg(history[-1])

if __name__ == "__main__":
  def read_args():
    try:
      if len(argv) < 2:
        usage()
        exit(0)
      opts, args = getopt(argv[1:], "hd:", ["help", "device="])
      for opt, arg in opts:
        if opt in ("-h", "--help"):
          usage()
          exit(0)
        elif opt in ('-d', '--device'):
          global devices
          devices+=arg.split(',')
    except IOError:
      print "Could not open "+arg
      exit(2)
    except SystemExit:
      raise
    except:
      usage()
      raise

  def usage():
    print """'{0}' can be used to show information about from block device to filesystem and vice versa:
'{0}' can be used with the following options:
-h, --help, no parameters                  : Show this usage info.
-d [blockdevices], --device=[blockdevices] : The device(s) to print. Multiple devices should be comma separated...

Without a source, input will be read from stdin.
Without a destination, output will be written to stdout.""".format(argv[0])

  from sys import argv, exit, stdin, stdout, stderr
  from subprocess import Popen
  from getopt import getopt
  from os import _exit

  devices=[]

  read_args()
  for d in devices:
    readdev(d)

  print "Einde."
