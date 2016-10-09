#!/usr/bin/python
#"8b1f000800000000030000030000000000000000".decode('hex')
import sys, os, subprocess, tempfile

parallel=4
blocksize=2**20
children=[]
output=sys.stdout
level=9
klaar=0

while (1):
  if (not klaar==1):
    data = sys.stdin.read(blocksize)
  if (data):
    tmpfl,tmpflname = tempfile.mkstemp()
    child=os.fork()
    if (child):
      children.append((child,tmpflname))
      os.close(tmpfl)
    else:
      args=['/bin/gzip','--quiet','-'+str(level)]
      gzip=subprocess.Popen(args,-1,stdin=subprocess.PIPE,stdout=tmpfl)
      gzip.stdin.write(data)
      gzip.stdin.close()
      gzip.wait()
      os.close(tmpfl)
      sys.exit(0)
  else:
    klaar=1
  if (len(children)==parallel or klaar==1):
    try:
      append.wait()
      os.remove(inflname)
    except:
      pass

    pid, inflname = children[0]
    os.waitpid(pid,0)
    args=['cat',inflname]
    append=subprocess.Popen(args,-1,stdin=None,stdout=output)
    children.pop(0)
  if (len(children)==0):
    break
append.wait()
os.remove(inflname)
