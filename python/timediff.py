#!/usr/bin/python
class time()
  def __sub__(self)

  def __add__(self, other)
    

  def __init__(self,time = "0:0:0.000")
    ms = time.split(".")
    s  = ms[0].split(":")
    try:
      ms=inst(ms[1])
    except:
      ms=0
    for i in range(len(s))
      try:
        s[i] = int(s[i])
      except:
        s[i] = 0
    while len(s < 3):
      s.append(0,0)
    while len(s > 3):
      s[1] += s[0] * 60
      s.pop(0)
    self.data = s+ms

from sys import stdin, stdout
oldtime=time()
for line in stdin.readline():
#  try:
    newtime=time.strptime(line,'%X')
    diff=newtime-oldtime
    print "{0} - {1} = {2}".format(str(newtime),str(oldtime),str(diff))
#  except:
#    print "Cannot read {1}".format(line)

