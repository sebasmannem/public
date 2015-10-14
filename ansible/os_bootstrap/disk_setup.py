#!/usr/bin/env python
import re

def blkid2dict(blkid):
  ret={}
  splitter_re=re.compile('[ \t]+')
  for pair in splitter_re.split(blkid.decode('utf-8')):
    try:
      if pair[-1] == '\n':
        pair=pair[:-1]
    except:
      pass
    try:
      key, val = pair.split('=', 1)
      if val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
      ret[key] = val
    except:
      pass
  return ret

if __name__ == "__main__":
  from glob import glob
  import subprocess
  import json
  import sys
  import os
  import time

  import argparse
  parser = argparse.ArgumentParser(description='Create PVs from empty disks and add to (new or existing) VG.')
  parser.add_argument('--vg', dest='vg', default='Volume00', help='VG to create or extend')
  parser.add_argument('-p', '--partition_table_type', dest='pttype', default='gpt', help='partitiontable type')
  parser.add_argument('-i', '--info', dest='info', action='store_true', help='Only show info and dont actually modify')
  parser.add_argument('-m', '--mountpoint', dest='mountpoint', default='/mnt', help='Specify mountpoint to mount root to')
  parser.add_argument('--noswap', dest='swap', action='store_false', help='Dont create a swap lv.')
  parser.add_argument('--noroot', dest='root', action='store_false', help='Dont create a rot lv')

  parser.add_argument('-x', '--debug', dest='debug', action='store_true', help='Debug option')

  args = parser.parse_args()

  devnull=open('/dev/null')
  dp_re=re.compile('^/dev/([sv]d[a-z]+)([0-9]*)$')
  parted_re=re.compile('^([0-9]+):([0-9]+)B:([0-9]+)B:([0-9]+)B:([a-zA-Z0-9]*):([^:]*):([^:]*);$')
  disks={}
  invalid_disks=set()
  for blk in glob('/dev/[sv]d*'):
    d, p = dp_re.search(blk).groups()[:2]
    if p == '':
      try:
        dsk=disks[d]
      except:
        dsk={}
        disks[d] = dsk
      try:
        f=open(blk, 'w+b')
        s=f.read(1)
        f.close()
      except IOError:
        #read only, no permissions, no media, or whatever
        invalid_disks.add(d)
        continue
      blkid=subprocess.Popen(['blkid', blk], stdin=None, stdout=subprocess.PIPE, stderr=devnull, shell=False)
      blkid_info = blkid2dict(blkid.stdout.read())
      blkid.wait()
      if blkid.returncode != 0:
        #Seems there is no blkid info (so no partition table either).
        continue
      try:
        if blkid_info['PTTYPE'] not in ['dos','gpt']:
          #unknown partittion table format. Save to proceed? Probably not...
          print('I dont understand the output of blkid {0}.\nSaver if a admin checks it out.'.format(blk))
          if not args.info:
            sys.exit(1)
      except:
        #There is blkid info, but no partitiontable type. Maybe fs/lvmpv directly on disk?
        print('blkid {0} shows no info on PTTYPE.\nSaver if a admin checks it out.'.format(blk))
        if not args.info:
          sys.exit(1)
      parted=subprocess.Popen(['parted', '-s', '-m', '/dev/{0}'.format(d), 'unit','b','print'], stdout=subprocess.PIPE, stdin=None, stderr=devnull)
      for line in parted.stdout:
        if line[-1] == '\n':
          line=line[:-1]
        try:
          m=parted_re.search(line)
          if m:
            print(m.groups())
            p, start, stop, size, fs, name, flags = m.groups()
            dsk[p] = m.groups()
        except:
          pass
      parted.wait()
      if parted.returncode != 0:
        invalid_disks.add(d)
    else:
      try:
        dsk=disks[d]
      except:
        dsk={}
        disks[d]=dsk
      if p not in dsk.keys():
        dsk[p]=(p,-1)
  valid_disks=set([d for d in disks.keys() if len(disks[d]) == 0]) - invalid_disks

  #invalid_disks bevat alle disks die niet geopend konden worden.
  #valid_disks bevat alle disks zonder partities (zowel in udev als in partitietabel) en die wel geopend konden worden.
  #disks bevat een dictionary van disks welek weer dictionarys zijn van prtities welke tuples zijn.

  if len(valid_disks) == 0:
    print('No suitable disk found. Please cleanup partitions before you proceed.'.format(d))

  if args.debug:
    print(json.dumps({'valid_disks':list(valid_disks), 'invalid_disks':list(invalid_disks), 'disks':disks}))
  if not args.info:
    parts=[]
    for d in valid_disks:
      try:
        subprocess.check_call(['parted', '-s', '-m', '/dev/{0}'.format(d), '--','mklabel',args.pttype,'mkpart','lvm','1','-1', 'set', '1', 'lvm', 'on'], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Failed to create new partition on {0}.'.format(d))
        sys.exit(1)
      try:
        part='/dev/{0}1'.format(d)
        parts.append(part)
        subprocess.check_call(['pvcreate', '-y', '-ff', part], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Failed to create pv on new partition.'.format(d))
        sys.exit(1)
    
    if os.path.exists('/dev/{0}'.format(args.vg)):
      #device exists. Hope it's a vg and try to extend
      try:
        subprocess.check_call(['vgextend', '-y', args.vg]+parts, stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('device /dev/{0} exists. Tried to extend, but couldnt. Maybe the vg name is invalid?'.format(args.vg))
        sys.exit(1)

      #rediscover what PV's de VG is made of.
      parts=[]
      pvs=subprocess.Popen(['pvs', '-o', 'VG_Name,PV_Name', '--noheadings'], stdout=subprocess.PIPE, stdin=devnull, stderr=devnull)
      pvs_re=re.compile('{0} +([a-zA-Z0-9]+)'.format(args.vg))
      for line in pvs:
        if line[-1] == '\n':
          line=line[:-1]
        m=pvs_re.search(line)
        if m:
          parts.append(m.group(1))
    else:
      try:
        subprocess.check_call(['vgcreate', '-y', args.vg]+parts, stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to create new vg {0}, but failed. Invalid VG name?'.format(args.vg))
        sys.exit(1)

    if args.swap:
      try:
        subprocess.check_call(['lvcreate', '-y', '-n', 'lv_swap', '-L', '500M', '-i', str(len(parts)), args.vg], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to create swap lv /dev/{0}/lv_swap, but failed. Invalid VG name?'.format(args.vg))
        sys.exit(1)
      time.sleep(1)
      try:
        subprocess.check_call(['mkswap', '/dev/{0}/lv_swap'.format(args.vg)], stdout=None, stdin=devnull, stderr=None)
      except:
        print('Tried to initiate swap lv /dev/{0}/lv_swap, but failed. Invalid VG name?'.format(args.vg))
        sys.exit(1)
      try:
        subprocess.check_call(['swapon', '/dev/{0}/lv_swap'.format(args.vg)], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to use swap lv /dev/{0}/lv_swap, but failed. Invalid VG name?'.format(args.vg))
        sys.exit(1)

    if args.root:
      i=1
      cryptdevs=[]
      for pv in parts:
        cryptdev='root_'+str(i)
        lv='lv_'+cryptdev
        try:
          subprocess.check_call(['lvcreate', '-y', '-n', lv, '-l', '100%PVS', args.vg, part], stdout=devnull, stdin=devnull, stderr=devnull)
        except:
          print('Tried to create use rootfs lv /dev/{0}/{1}, but failed. Please investigate.'.format(args.vg, lv))
          sys.exit(1)

        cryptsetup=subprocess.Popen(['cryptsetup', 'luksFormat', '/dev/{0}/{1}'.format(args.vg,lv), '-'], stdout=devnull, stdin=subprocess.PIPE, stderr=devnull)
        cryptsetup.communicate(bytes('wachtwoord', 'utf-8'))
        cryptsetup.communicate()
        cryptsetup.wait()
        if cryptsetup.returncode != 0:
          print('Tried to encrypt rootfs lv /dev/{0}/{1}, but failed. Please investigate.'.format(args.vg, lv))
          sys.exit(1)
        cryptsetup=subprocess.Popen(['cryptsetup', 'open', '--type', 'luks', '--key-file', '-', '/dev/{0}/{1}'.format(args.vg,lv), cryptdev], stdout=devnull, stdin=subprocess.PIPE, stderr=devnull)
        cryptsetup.communicate(bytes('wachtwoord', 'utf-8'))
        cryptsetup.communicate()
        cryptsetup.wait()
        if cryptsetup.returncode != 0:
          print('Tried to open rootfs lv /dev/{0}/{1}, but failed. Please investigate.'.format(args.vg,lv))
          sys.exit(1)
        cryptdevs.append('/dev/mapper/'+cryptdev)
      try:
        subprocess.check_call(['mkfs.btrfs'] + cryptdevs, stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to create root btrfs filesystem, but failed. Please investigate..'.format(args.vg))
        sys.exit(1)
      try:
        subprocess.check_call(['mount', cryptdevs[0], args.mountpoint], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to mount root btrfs filesystem, but failed. Please investigate..'.format(args.vg))
        sys.exit(1)
      try:
        os.makedirs(args.mountpoint+'/__snapshots')
        subprocess.check_call(['btrfs', 'subvolume', 'create', args.mountpoint+'/__active'], stdout=devnull, stdin=devnull, stderr=devnull)
        subprocess.check_call(['btrfs', 'subvolume', 'create', args.mountpoint+'/__empty'], stdout=devnull, stdin=devnull, stderr=devnull)
        btrfs=subprocess.Popen(['btrfs', 'subvolume', 'list', '-t', args.mountpoint], stdin=devnull, stdout=subprocess.PIPE, stderr=devnull)
        splitter_re=re.compile('\t+')
        for line in btrfs.stdout:
          line=line.decode('utf-8')
          if line[-1] == '\n':
            line=line[:-1]
          ID, gen, top_level, path = splitter_re.split(line)[:4]
          if path=='__active':
            subprocess.check_call(['btrfs', 'subvolume', 'set-default', ID, args.mountpoint], stdout=None, stdin=None, stderr=None)
            break
      except:
        print('Tried to init root btrfs filesystem, but failed. Please investigate..'.format(args.vg))
        sys.exit(1)
      try:
        subprocess.check_call(['umount', args.mountpoint], stdout=devnull, stdin=devnull, stderr=devnull)
        subprocess.check_call(['mount', cryptdevs[0], args.mountpoint], stdout=devnull, stdin=devnull, stderr=devnull)
      except:
        print('Tried to remount root btrfs filesystem, but failed. Please investigate..'.format(args.vg))
        sys.exit(1)
