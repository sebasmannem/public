#!/usr/bin/python2
import re
import subprocess
parted=False
try:
  import parted
except:
  print "pyparted is needed. Please install with\nsudo yum install pyparted"
  exit(1)
from sys import stderr, stdout

disks={}

class LVM_VG(dict):
  #VG containing LV's
  name=None
  extent_size=0
  def __init__(self,vg_name,vg_extent_size):
    self.name=vg_name
    self.extent_size=vg_extent_size
  def PVs(self):
    ret=set()
    for lv_name in self:
      myLV=self[lv_name]
      for seg_start in myLV:
        seg=myLV[seg_start]
        for stripe in seg:
          ret.add(stripe.pv.part)
    return ret
  def partitions(self):
    parts={}
    for pv in self.PVs():
      parts[pv.path] = pv
    return parts
  def disks(self):
    dsks={}
    for pv in self.PVs():
      dsks[pv.disk.device.path] = pv.disk
    return dsks
  def disks_freespace(self):
    dsks=self.disks()
    for d in dsks:
      dsk=dsks[d]
      dsks[d]=0
      if dsk.primaryPartitionCount = dsk.maxPrimaryPartitionCount:
        continue
      try:
        freeGeo=d.getFreeSpacePartitions()[-1].geometry
        if freeGeo.start >= pv.disk.getPrimaryPartitions()[-1].geometry.end:
          dsks[d]=freeGeo.length * pv.disk.device.sectorSize
      except:
        pass
    for pv in self.PVs():
      dsk_path=pv.disk.device.path
      try:
        dsks[dsk_path]+=pv.free
      except:
        dsks[dsk_path]=pv.free
    return dsks
  def __repr__(self):
    ret=self.name+'\n'
    for lv_name in self:
      myLV=self[lv_name]
      ret+='  {0}:\n'.format(myLV.name)
      for seg_start in myLV:
        seg=myLV[seg_start]
        ret+='    {0}:\n'.format(seg.start)
        for stripe in seg:
          ret+='      {0}({1})\n'.format(stripe.pv.name(),stripe.start)
    return ret

class LVM_LV(dict):
  #LV containing lvsegs
  name=None
  def __init__(self,lv_name):
    self.name=lv_name

class LV_segment(list):
  #lvseg containing pvsegs
  start=None
  size=None
  def __init__(self,seg_start,seg_size):
    self.start, self.size = seg_start,seg_size

class PV_segment():
  #pvseg on pv
  pv=None
  start=None
  size=None
  def __init__(self,pv,pvseg_start,pvseg_size):
    self.pv, self.start, self.pvseg_size = pv, pvseg_start, pvseg_size
    pv[pvseg_start]=self

class LVM_PV(dict):
  #pv containing pvsegs
  part=None
  VG=None
  size=None
  free=None
  VG=None
  def __init__(self,part, VG,size,free):
    self.part, self.VG, self.size, self.free = part, VG, size*VG.extent_size, free*VG.extent_size
  def name(self):
    return self.part.path
  def disk(self):
    return self.part.disk
  def number(self):
    return self.part.number

def initVGs():
  VGs={}
  PVs={}
  disks={}

  re_split=re.compile('[ \t]+')
  dsk_re=re.compile('([/a-z]*)([0-9]*)')

  p=subprocess.Popen(['pvs','--segments','--nosuffix','--noheadings','--units','B','-ovg_name,vg_extent_size,seg_start,seg_size,stripes,pv_name,pv_size,pv_free,pvseg_start,pvseg_size,lv_name'], stdout=subprocess.PIPE, stderr=stderr)
  for l in p.stdout:
    l=l.replace('\n','')
    c=re_split.split(l)
    try:
      empty,vg_name,vg_extent_size,seg_start,seg_size,stripes,pv_name,pv_size,pv_free,pvseg_start,pvseg_size = c[0:10]
    except:
      continue
    try:
      VG=VGs[vg_name]
    except:
      VG=LVM_VG(vg_name, vg_extent_size)
      VGs[vg_name]=VG
    try:
      PV=PVs[pv_name]
    except:
      m=dsk_re.match(pv_name)
      disk_path=m.group(1)
      try:
        disk=disks[disk_path]
      except:
        dev=parted.Device(disk_path)
        disk=parted.Disk(dev)
        disks[disk_path] = self.disk
      pv_part=disk.getPartitionByPath(part_name)
      PV=LVM_PV(pv_part,VG,pv_size,pv_free)
      PVs[pv_name]=PV
    if len(c) > 10:
      try:
        lv_name=c[10]
        LV=VG[lv_name]
      except:
        LV=LVM_LV(lv_name)
        VG[lv_name]=LV
      try:
        seg=LV[seg_start]
      except Exception:
        seg=LV_segment(seg_start,seg_size)
        LV[seg_start]=seg
      seg.append(PV_segment(PV,pvseg_start,pvseg_size))
  return VGs

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  import os
  import glob
  import sys

  parser = OptionParser(usage='Usage: %prog [options] [folders]. Call without options for more examples.')
  parser.add_option("-r", "--reboot", dest="reboot", action="store_true", help="Expand with reboot.", default=False)
  parser.add_option("-n", "--noreboot", "--hot", dest="hot", action="store_true", help="Expand without reboot.", default=False)
  parser.add_option("-c", "--cleandisk", dest="clean", help="Specifify a cleandisk to cleanup after -h option.", default=False)
  parser.add_option("-v", "--volumegroup", dest="VG", default="", help="Specify volume to expand.", default=False)
  parser.add_option("-l", "--logicalvolume", dest="LV", default="", help="Specify volume to expand.", default=False)
  parser.add_option("-s", "--size", dest="size", default=0, help="Specify how much to expand LV.")
  parser.add_option("-f", "--force", dest="force", action="store_true", help="Bypass some safety precautions.", default=False)
  parser.add_option("--verbose", dest="verbose", action="store_true", help="Additional output.", default=False)

  (options, args) = parser.parse_args()

  if not options.reboot and not options.hot:
    print '''This script is meant to autogrow striped logical volumes on multiple drives.
There are basically three ways:
- With a reboot. The script will grow the partitions and ask for a reboot to effectuate the changes.
  Then the script will (grow the PV's and the LV.
- Without a reboot. The script will add new partitions, create PV's, add them to the VG and grow the LV.
- Without a reboot and with one cleandisk. The script will:
  - do the same as with the previous option.
  - will partition the cleandisk, and add to the VG
  - will do the following disk by disk untill all have been repartitioned:
    - move everything from one other disk to the 'disk just added'.
    - will remove the 'just cleaned disk' from the VG, repartition the cleaned disk, add to the VG again
    In the end: 
      - The clean disk will contain 1 partition and data, 
      - all other disks, except the last that was processed, will also contain one partition and data.
      - the disk that was last pocessed will be empty
  - After that the script will advise on removing this empty disk.
  This option does not require a reboot and leaves a clean configuration.
  However, this option is also the most resource intensive (IOPS) option, and might take a long time to finish.
  And it temporarilly needs an extra disk.

The following procedures are advised:
- To read this, call script without options:
  {0}
- To find out some help and the options that are applicable:
  {0} -h
- If a reboot is possible (like a dataguard standby), just use the -r option.
  {0} -r -v VG [-l LV [-s SIZE_TO_ADD]]
- If no reboot is possible, and there are only 1, or 2 primary partitions, use -h without -c.
  {0} -h -v VG [-l LV [-s SIZE_TO_ADD]]
- If there are 3 partitions, use -h with -c, to leave 'disks with one partition only'.
  {0} -r -c CLEAN_DISK -v VG [-l LV [-s SIZE_TO_ADD]]
'''.format(__file__)
    exit()

  if os.getuid() != 0:
    print "Please run as root (use sudo)"
    exit(1)

  devnull=open('/dev/null','a')
  if not options.verbose:
    stderr=devnull
    stdout=devnull
  
  #Lees alle LVM info in.
  VGs=initVGs()

  '''
  for vg_name in VGs:
    VG=VGs[vg_name]
    print VG
    print VG.disks(),VG.partitions()
#    print "{0} uses disks {1}".format(vg_name,','.join(sorted(myVG.disks())))
  exit(0)'''

  #Zoek VG
  try:
    VG=VGs[options.VG]
  except:
    if not options.VG:
      print "Please specify the volume group to grow"
    else:
      print "The specified volume group could not be found on this system"
    exit(1)

  #Zoek LV
  try:
    LV=VG[options.LV]
  except:
    if not options.LV:
      print "Please specify the logical volume to grow"
    else:
      print "The specified logical volume could not be found on this volume group"
    exit(1)

  #Zoek laatste LVseg
  lastseg=LV[sorted(LV.keys())[-1]]
  dsks=[pseg.pv.disk.device.path for pseg in lastseg]
  if len(dsks) > len(set(dsks)):
    print "Issue: last logical segment {0} of LV {1}.{2} contains more than one stripes on same disk.".format(lastseg.start, VG.name, LV.name)
    print "PV per stripe: {0}".format(",".join(disks))
    exit(1)

  #kijk per disk of er voldoende free space beschikbaar is.
  dsks_free=VG.disks_freespace()
  sizeperdisk=options.size/len(dsks_free)
  toGrow=0
  for d in dsks:
    free=dsks_free[d]
    if free < sizeperdisk:
      print "Please add {0:10.2} MiB to disk {1}".format( float(sizeperdisk-free)/2**20,d)
      toGrow+=1
  if toGrow>0:
    exit(1)

  #Voeg evt partities toe
  for path, dsk in VG.disks.items():
    if path in dsks:
      if dsk.primaryPartitionCount = dsk.maxPrimaryPartitionCount:
        continue
      freeGeo=dsk.getFreeSpacePartitions()[-1].geometry
      if freeGeo.start >= dsk.getPrimaryPartitions()[-1].geometry.end:
        filesystem = parted.FileSystem(type='ext3', geometry=geometry)
        partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, fs=filesystem, geometry=freeGeo)
        disk.addPartition(partition=partition, constraint=dev.optimalAlignedConstraint)
        partition.setFlag(parted.PARTITION_LVM)
        disk.commit()
        subprocess.check_call(['pvcreate',partition.path],stdout=stdout, stderr=stderr)
        subprocess.check_call(['vgextend',options.VG,partition.path],stdout=stdout, stderr=stderr)

  #Opnieuw VG info inlezen.
  VGs=initVGs()
  VG=VGs[options.VG]
  LV=VG[options.LV]
  lastseg=LV[sorted(LV.keys())[-1]]
  dsks=[pseg.pv.disk.device.path for pseg in lastseg]


  #Kijk hoeveel je de LV in eens kunt vergroten (per disk grootste vrije ruimte, kleinste hiervan over alle disks) en vergroot.
  #reinit
  #Blijf dit doen tot er niet meer vergoot kan worden, of de LV groot genoeg is

  #Als er een cleandisk is:
  #Partition de cleandisk, voeg toe aan VG
  #Kijk of alle pvsegs van de verschillende lvsegs op dezelfde disk staan.
  #Eventueel fixen door te schuiven naar de cleandisk en daarna per disk door te schuiven
  #Breng alles van laatste disk naar cleandisk
  #repart laatste disk
  # breng alles van eennalaatste disk naar laatste disk
  # etc. tot alles klaar is
  #Vertel welke disk weg mag

  dsks=VG.disks()


    try:
      freeGeo=disk.getFreeSpacePartitions()[-1].geometry
      if freeGeo.start < disk.getPrimaryPartitions()[-1].geometry.end:
        #No new free space after last partition
        continue
      freePart=parted.Partition(disk=disk, type=_ped.PARTITION_NORMAL, fs=None, geometry=dev.optimalAlignedConstraint.solveNearest(freeGeo))
      disk.addPartition(freePart,dev.optimalAlignedConstraint)
      disk.commit()

  exit(0)

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
          if options.reboot:
            disk.maximizePartition(disk.partitions[-1],dev.optimalAlignedConstraint)
            disk.commitToDevice()
          else:
            geometry = parted.Geometry(device=dev, start=1, length=1)
            for p in disk.getFreeSpacePartitions():
              if p.geometry.length > geometry.length:
                geometry = p.geometry
            filesystem = parted.FileSystem(type='ext3', geometry=geometry)
            partition = parted.Partition(disk=disk, type=parted.PARTITION_NORMAL, fs=filesystem, geometry=geometry)
            disk.addPartition(partition=partition, constraint=dev.optimalAlignedConstraint)
            partition.setFlag(parted.PARTITION_LVM)
            disk.commit()
            subprocess.check_call(['pvcreate',partition.path],stdout=stdout, stderr=stderr)
            subprocess.check_call(['vgextend',options.VG,partition.path],stdout=stdout, stderr=stderr)
            #drvnames.append(partition.path)
            subprocess.check_call(['lvresize','-i',str(len(drvnames)),'-I','1M','-l', '+100%FREE','/dev/{$0}/$1'.format(options.VG,options.LV)],stdout=stdout, stderr=stderr)
      except Exception, e:
        print 'Error occurred during creation of {0}:\n{1}'.format(next_vol,e)
        errs+=1
  #Ergens hier moet een reboot geinitieerd worden. Daarna moet de PVs en LV resize worden.
  subprocess.check_call(['lvresize','-i',str(len(drvnames)),'-I','1M','-l', '+100%FREE','/dev/{$0}/$1'.format(VG,LV)],stdout=stdout, stderr=stderr)

  v+=1
  next_vol=options.volume.format(v)













  #drives=glob.glob('/dev/[vs]d*')
  drives=set()
  stdout.write("\nHarvesting block devices with lsblk.\n")
  p=subprocess.Popen(['lsblk','-d','-o','NAME','-n'], stdout=subprocess.PIPE, stderr=stderr)
  for d in p.stdout:
    d=d.replace('\n','')
    drives.add('/dev/'+d)

  volumes=set()
  stdout.write("\nHarvesting volume groups.\n")
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
    stdout.write("\nInspecting {0}.\n".format(d))
    try:
      dev=parted.Device(d)
      dsk=parted.Disk(dev)
      if len(dsk.partitions) > 0:
        stdout.write("Drive is not empty. Skipping.\n")
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

