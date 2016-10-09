#!/usr/bin/python
import os, sys
children=[]
for i in range(15):
  pid=os.fork()
  if pid:
    children.append(pid)
  else:
    a=0
    for x in xrange(10000000):
      a+=x
    sys.exit(0)
for child in children:
  os.waitpid(child, 0)
