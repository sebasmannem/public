#!/usr/bin/python2
if __name__ == "__main__":
  from optparse import OptionParser
  import subprocess
  import re
  re_comment=re.compile('#.*')
  re_ltrim=re.compile('^\s*')
  re_name_val=re.compile("\s*(\S[^=]*\S)\s*=\s*(\S[^=]*\S)\s*")

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-c", "--config_file", dest="config_file", help="File that contains sysctl config to be added.")
  parser.add_option("-r", "--reconfigure", dest="reconfigure", help="Actually change /etc/sysctl.conf and reload config.", default=False, action="store_true")

  (options, args) = parser.parse_args()

  config={}
  sysctl=subprocess.Popen(['/sbin/sysctl','-a'],stdout=subprocess.PIPE)
  for line in sysctl.stdout:
    m=re_name_val.search(line)
    if m:
      name,val=m.groups()
      config[name]=val

  append=[]
  append_needed=False
  f=open(options.config_file)
  for line in f:
    line=line.replace('\n','')
    line=re_ltrim.sub('',line)
    if re_comment.match(line):
      append.append(line)
    else:
      l=re_comment.sub('',line)
      m=re_name_val.search(l)
      if m:
        name,val=m.groups()
        val=val.replace(' ','\t')
        if config[name] != val:
          append_needed=True
          append.append(line)
  f.close()
  if append_needed:
    if options.reconfigure:
      f=open('/etc/sysctl.conf','a')
      f.write('\n')
      for l in append:
        f.write(l+'\n')
      f.close()
      subprocess.check_call(['/sbin/sysctl','-p'])
    else:
      for l in append:
        print(l)
