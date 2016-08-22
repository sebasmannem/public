#!/usr/bin/python
from sys import argv,stdin
col=int(argv[1])
output={}
for line in stdin:
  a=line.split(' ')
  if a[0][0:3] != 'dm-':
    continue 
  key=int(a[0][3:])
  val=float(a[col])
  try:
    count,sum,min,max=output[key]
    count+=1
    sum+=val
    if min > val: min=val
    if max < val: max=val
    output[key]=count,sum,min,max
  except:
    output[key]=1,val,val,val

print 'dev      min    max    avg'
print '=========================='
for key in output:
  count=output[key][0]
  min=output[key][2]
  max=output[key][3]
  avg=float(output[key][1])/output[key][0]
#  print '%s: count=%d min=%f max=%f avg=%f' %(key,count,min,max,avg)
  print 'dm-%-2d %6.2f %6.2f %6.2f' %(key,min,max,avg)
