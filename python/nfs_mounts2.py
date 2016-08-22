#!/usr/bin/python2

#Backup to /root/config_backup/
def sizeof_fmt(num, suffix='B'):
  for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
    if abs(num) < 1024.0:
      return "%3.1f%s%s" % (num, unit, suffix)
    num /= 1024.0
  return "%.1f%s%s" % (num, 'Yi', suffix)

if __name__ == "__main__":
  mounts={}
  import re
  import os
  from sys import exit, stderr
  import datetime
  import shutil

  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-r", "--reverse", action="store_true", dest="reverse", default=False, help="Rollback changes (Change new values to old).")
  parser.add_option("--nonhuman", action="store_false", dest="human", default=True, help="Show numbers in human reable format.")
  parser.add_option("-c", "--convert", dest="convert", default=False, help="Convert old shares to new locations. Please specify path to conversion list")
  parser.add_option("--remount", action="store_true", dest="remount", default=False, help="Reload autofs and remount changed mounts.")
  (options, args) = parser.parse_args()

  re_comment=re.compile('#.*')
  re_split=re.compile('[\t ]+')
  convertlist=[]

  if options.convert:
    f=open(options.convert)
    for line in f:
      l = re_split.split(re_comment.sub('', line.replace('\n','')))
      if len(l) <2: continue
      if options.reverse:
        from_share, to_share = l[1::-1]
      else:
        from_share, to_share = l[0:2]
      convertlist.append((from_share, to_share))
    f.close()
    try:
      os.makedirs('/root/config_backup')
    except Exception, e:
      if e.errno != 17:
        print e.msg
        exit(1)

  try:
    remounts=set()
  except:
    import sets
    remounts=sets.Set()

  fname='/etc/mtab'
  f=open(fname)
  lines=f.readlines()
  f.close()
  for i in range(len(lines)):
    l = re_split.split(re_comment.sub('', lines[i].replace('\n','')))
    if len(l) < 2: continue
    share,mount=l[0],l[1]
    if not ':' in share: continue
    new_share = ''
    for from_share, to_share in convertlist:
      if from_share in share:
        new_share = share.replace(from_share, to_share)
    mounts[mount]=(fname,i,share, '')
    if new_share != '':
      remounts.add(mount)

  fname='/etc/fstab'
  f=open(fname)
  lines=f.readlines()
  f.close()
  converted_lines=lines[:] #Copy the list
  is_dirty=False
  for i in range(len(lines)):
    l = re_split.split(re_comment.sub('', lines[i].replace('\n','')))
    if len(l) < 2: continue
    share,mount=l[0],l[1]
    if not ':' in share: continue
    new_share = ''
    for from_share, to_share in convertlist:
      if from_share in share:
        new_share = share.replace(from_share, to_share)
        is_dirty=True
        converted_lines[i] = lines[i].replace(share, new_share,1)
    mounts[mount]=(fname,i,share, new_share)
    if new_share != '':
      remounts.add(mount)
  if is_dirty:
    try:
      now=datetime.datetime.now()
      new_file_name = '/root/config_backup/%s-%s' % (os.path.basename(fname),now.strftime('%d-%m-%Y_%H:%M:%S'))
      shutil.copy2(fname,new_file_name)
      f=open(fname,'w')
      for l in converted_lines:
        f.write(l)
      f.close()
      print "Conversion of %s has finished succesfully" % (fname)
    except Exception, e:
      stderr.write('Conversion of %s has has failed.\n' % (fname))
      stderr.write(e)
      stderr.write('\n')

  master=open('/etc/auto.master')
  for mline in master:
    ml = re_split.split(re_comment.sub('', mline.replace('\n','')))
    if len(ml) < 2: continue
    mp, fname=ml[0],ml[1]
    if not os.path.isfile(fname):
      stderr.write('Invalid filename: %s\n' % (fname))
      continue
    if os.access(fname, os.X_OK):
      stderr.write('autofs file %s is executable. Result cannot be detemined.\n' % (fname))
      continue
  
    f=open(fname)
    lines=f.readlines()
    f.close()
    converted_lines=lines[:] #Copy the list
    is_dirty=False
    for i in range(len(lines)):
      l = re_split.split(re_comment.sub('', lines[i].replace('\n','')))
      if len(l) < 3: continue
      mount,share = os.path.join(mp,l[0]),l[2]
      if not ':' in share: continue
      new_share = ''
      for from_share, to_share in convertlist:
        if from_share in share:
          new_share = share.replace(from_share, to_share)
          is_dirty=True
          converted_lines[i] = lines[i].replace(share, new_share,1)
      mounts[mount]=(fname,i,share, new_share)
    if is_dirty:
      try:
        now=datetime.datetime.now()
        new_file_name = '/root/config_backup/%s-%s' % (os.path.basename(fname),now.strftime('%d-%m-%Y_%H:%M:%S'))
        shutil.copy2(fname,new_file_name)
        f=open(fname,'w')
        for l in converted_lines:
          f.write(l)
        f.close()
        print "Conversion of %s has finished succesfully" % (fname)
      except Exception, e:
        stderr.write('Conversion of %s has has failed.\n' % (fname))
        stderr.write(str(e))
        stderr.write('\n')
  master.close()

  print "" #Expres zodat bij collect van de server iig 1 regel in de output komt
  for mp in mounts:
    fname,line,share,new_share=mounts[mp]
    try:
      if '*' in mp:
        #mp contains wildcard characters. Cannot use stat.
        stat = None #stat.f_bsize will throw an exception
      else:
        stat = os.statvfs(mp)
      if options.human:
        size = sizeof_fmt(stat.f_bsize * stat.f_blocks)
        used = sizeof_fmt(stat.f_bsize * (stat.f_blocks-stat.f_bfree))
      else:
        size = stat.f_bsize * stat.f_blocks
        used = stat.f_bsize * (stat.f_blocks-stat.f_bfree)
    except:
      size='?   '
      used='?   '

    print "%-30s %-70s %15s %15s %-20s" % (mp, share, size, used, fname+':'+str(line+1))
    if new_share != "":
      print "-> "+new_share

  if options.remount:
    #import subprocess
    #LET OP: subprocess heeft de voorkeur boven popen2, maar werkt niet onder python 2.3 (RH4)
    import popen2
    print "Reloading autofs"
    p=popen2.Popen4(['service','autofs','restart'])
    for l in p.fromchild:
      print l.replace('\n','')
    if p.wait() !=0 :
      stderr.write("Could not reload autofs.\n")
    

    for mp in remounts:
      print "Umounting %s." % (mp)
      p=popen2.Popen4(['umount',mp])
      for l in p.fromchild:
        print l.replace('\n','')
      if p.wait() !=0 :
        stderr.write("Could not unmount %s.\n" % (mp))

    print "Remounting (mount -a)"
    p=popen2.Popen4(['mount','-a'])
    for l in p.fromchild:
      print l.replace('\n','')
    if p.wait() !=0 :
      stderr.write("Could not remount previously mounted mount points.\n")
