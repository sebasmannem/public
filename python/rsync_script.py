#!/usr/bin/python2

if __name__ == "__main__":
  import os
  import sys
  import subprocess
  import re

  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-r", "--reverse", action="store_true", dest="reverse", default=False, help="Rollback changes (Change new values to old).")
  parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Show rsync output.")
  parser.add_option("-c", "--ctl_file", dest="ctl_file", help="File that specifies what to sync where. The file should have 3 columns separated by spaces: source, dest, subfolders (comma seperated list)")
  parser.add_option("-e", "--example", action="store_true", dest="example", default=False, help="Display example and exit.")
  (options, args) = parser.parse_args()

  if options.example:
    print """#- Create a file with two lines:
echo '192.168.1.100:/vol/vol_nfs/common storagesrv100.domain.com:/otacommon /all/mp1,/all/mp2
nas100:/vol/vol_nfs/axway_axway_a_data nfs100.domain.org:/a_data_vol/axway_a_data /' > /tmp/sync.conf

#- Call this script to sync:
/stage/oracle/scripts/python/rsync_script.py -c /tmp/sync.conf
#  This will sync the subfolders ./all/mp1 and ./all/mp2 from '192.168.1.100:/vol/vol_nfs/common' to 
#  'nfs100.domain.org:/otacommoracle_vol/common' and sync all from 
#  'nas100:/vol/vol_nfs/a_data' to 'nfs100.domain.org:/a_data_vol/a_data'

#- Or you can sync back:
/stage/oracle/scripts/python/rsync_script.py -c /tmp/sync.conf -r
#  This will sync the subfolders ./all/mp1 and ./all/mp2 from 
#  'nfs100.domain.org:/otacommoracle_vol/common' back to '192.168.1.100:/vol/vol_nfs/common_oracle_nfs'
#  and sync all back from 'nfs100.domain.org:/a_data_vol/a_data' to 
#  'nas100:/vol/vol_nfs/a_data'.
"""
    sys.exit(0)

  devnull=open('/dev/null')
  if options.verbose:
    out=sys.stdout
  else:
    out=devnull

  re_comment=re.compile('#.*')
  re_split=re.compile('[\t ]+')

  for p in ('/mnt/from','/mnt/to'):
    try:
      os.makedirs(p)
    except Exception, e:
      if e.errno != 17:
        print e.msg
        sys.exit(1)
    subprocess.call(['umount',p],stdout=devnull,stderr=devnull)

  issues=0
  f=open(options.ctl_file)
  for line in f:
    l = re_split.split(re_comment.sub('', line.replace('\n','')))
    if len(l) < 3: continue
    sync_from, sync_to, subfolders = l[0:3]
    if options.reverse:
      sync_from, sync_to = sync_to, sync_from
    try:
      subprocess.check_call(['mount',sync_from,'/mnt/from'])
      subprocess.check_call(['mount',sync_to,'/mnt/to'])
    except Exception, e:
      print "Mounting failed: %s." % (str(e))
    for subfolder in subfolders.split(','):
      if subfolder[0] == '/':
        subfolder=subfolder[1:]
      if subfolder[-1] == '/':
        subfolder=subfolder[:-1]
      try:
        os.makedirs('/mnt/to/'+subfolder)
      except Exception, e:
        if e.errno != 17:
          print e.msg
          continue
      try:
        subprocess.check_call(['rsync','-av','--exclude','.snapshot','--delete', '/mnt/from/'+subfolder+'/','/mnt/to/'+subfolder],stdout=out,stderr=out)
        print "Syncing subfolder %s from %s to %s succeeded." % (subfolder, sync_from, sync_to)
      except Exception, e:
        issues+=1
        print "Syncing subfolder %s from %s to %s failed." % (subfolder, sync_from, sync_to)

    for p in ('/mnt/from','/mnt/to'):
      subprocess.check_call(['umount',p])
  f.close()

  if issues:
    print 'There where %n issues.' % issues
    exit(issues)
