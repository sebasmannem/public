#!/usr/bin/python2
if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  from sys import stderr
  import subprocess
  import os
  import glob
  import re
  import sys

  parser = OptionParser(usage='Usage: %prog [options] [folders]. Call without options for more examples')
  parser.add_option("-a", "--action", dest="action", help="What to do? options are: advise, examples, create, auto.", default="examples")
  parser.add_option("-l", "--loud", dest="silent", action="store_false", help="Extra output on stderr", default=True)
  parser.add_option("-v", "--volumename", dest="volume", default="Volume{0:0>2}", help="Naming convention. Default: Volume00, volume01 - Volume99.")


  (options, args) = parser.parse_args()

  if options.action=='examples':
    print '''This script is meant to autocreate striped logical volumes from multiple drives.
The input should be one or more disks without partitions.
The output depends on the action (-a).
The following can be done:
- Show this info:
  sudo {0} -a explain
- Show an advise (what the create command would do):
  sudo {0} -a advise
- Create a volume group of devices of the same size:
  sudo {0} -a create -v Volume01 /dev/sdb /dev/sdc /dev/sdd
- Create all volume groups as the advise has reported:
  sudo {0} -a auto

Please be aware that this script can only attached devices of the same size (in MiB).
Devices with different sizes will end up in differenet Volumes.'''.format(__file__)
    exit()

  if os.getuid() != 0:
    print "Please run as root (use sudo)"
    exit(1)

  devnull=open('/dev/null','a')
  if options.silent:
    stderr=devnull
  parted=False
  try:
    import parted
  except:
    if options.action=='auto':
      stderr.write("\nInstalling pyparted.\n")
      subprocess.call(['yum','-y','install','pyparted'],stdout=stderr,stderr=stderr)
    else:
      print "pyparted is needed. Please install with\nsudo yum install pyparted"
      exit(1)
  if not parted:
    try:
      import parted
    except:
      print "pyparted is needed and autoinstall dit not finish correctly. Please install by hand with\nsudo yum install pyparted"
      exit(1)

  #drives=glob.glob('/dev/[vs]d*')
  drives=set()
  stderr.write("\nHarvesting block devices with lsblk.\n")
  p=subprocess.Popen(['lsblk','-d','-o','NAME','-n'], stdout=subprocess.PIPE, stderr=stderr)
  for d in p.stdout:
    d=d.replace('\n','')
    drives.add('/dev/'+d)

  volumes=set()
  stderr.write("\nHarvesting volume groups.\n")
  p=subprocess.Popen(['vgs','--noheadings','-o','vg_name'], stdout=subprocess.PIPE, stderr=stderr)
  for v in p.stdout:
    v=v.replace('\n','')
    v=v.replace(' ','')
    volumes.add(v)

  if len(args) > 0:
    empty_drives=set(args)
    invalid=empty_drives-drives
    if len(invalid) > 0:
      print "Some arguments are not drives:\n - %s" % ("\n - ".join(invalid))
      print "Please only specify one ore more devices of:\n - %s" % ("\n - ".join(drives))
      exit(1)
  else:
    empty_drives=set(drives)

  drv_by_size={}
  for d in sorted(empty_drives):
    stderr.write("\nInspecting {0}.\n".format(d))
    try:
      dev=parted.Device(d)
      dsk=parted.Disk(dev)
      if len(dsk.partitions) > 0:
        stderr.write("Drive is not empty. Skipping.\n")
        empty_drives.discard(d)
        continue
    except parted.DiskLabelException:
      pass
    except Exception as e:
      stderr.write("Exception: {0}\n".format(e))
      continue
    size=dev.getLength('MiB')
    if size in drv_by_size:
      drv_by_size[size].add(dev)
    else:
      drv_by_size[size]=set([dev])

  if options.action=='create':
    if len(drv_by_size)>1:
      print "Cannot use create command for multiple drives with different sizes (MiB).\nPlease use advise to inspect what groups can be made..."
      exit(1)
    #Alternatief: Zoek de kleinste size en koppel alle drives daar maar aan.

  if options.action=='auto' and len(drv_by_size)>0 and options.volume.format(0) == options.volume.format(1):
    print "Your volumename descriptor (-v) cannot be used with multiple volumes and multiple volumes would be created.\n Please specify a different -v (or skip it) and try again, or use action 'advise' and examin the output."
    exit(1)

  if options.action=='advise':
    print "I would create the following volumes:"

  errs=0
  v=0
  next_vol=options.volume.format(v)
  for s in drv_by_size:
    while next_vol in volumes:
      v+=1
      next_vol=options.volume.format(v)
    drvs=drv_by_size[s]
    if options.action=='advise':
      drvnames=sorted([d.path for d in drvs])
      print "  sudo {0} -a create -v '{1}' {2} # size: {3} MiB".format(__file__, next_vol, " ".join(drvnames),s*len(drvnames))
    else:
      try:
        drvnames=[]
        for dev in drvs:
          disk=parted.freshDisk(dev, 'msdos')
          geometry = parted.Geometry(device=dev, start=1, length=dev.getLength() - 1)
          filesystem = parted.FileSystem(type='ext3', geometry=geometry)
          partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, fs=filesystem, geometry=geometry)
          disk.addPartition(partition=partition, constraint=dev.optimalAlignedConstraint)
          partition.setFlag(parted.PARTITION_LVM)
          disk.commit()
          drvnames.append(dev.path+'1')
        subprocess.check_call(['pvcreate']+drvnames,stdout=stderr, stderr=stderr)
        subprocess.check_call(['vgcreate',next_vol]+drvnames,stdout=stderr, stderr=stderr)
        subprocess.check_call(['lvcreate','-n','LogVol01','-i',str(len(drvnames)),'-I','1M','-l', '100%FREE',next_vol],stdout=stderr, stderr=stderr)
        subprocess.check_call(['mkfs.ext4','/dev/mapper/{0}-LogVol01'.format(next_vol)],stdout=stderr, stderr=stderr)
      except Exception, e:
        print 'Error occurred during creation of {0}:\n{1}'.format(next_vol,e)
        errs+=1
    v+=1
    next_vol=options.volume.format(v)
