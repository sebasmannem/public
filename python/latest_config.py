#!/usr/bin/env python
import sys
settings={}
for l in sys.stdin:
    #take out comment
    l=l.split('#')[0]
    if '=' in l:
        k,v = l.split('=',1)
        k=k.strip()
        v=v.strip()
        settings[k]=v

for k in sorted(settings.keys()):
    print("{0} = {1}".format(k,settings[k]))
