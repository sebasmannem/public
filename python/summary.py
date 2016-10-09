#!/bin/env python
class storage(dict):
  def __init__(self,name,size=0,free=0,reserved=0):
    self.name,self.size,self.free,self.reserved =name,size,free,reserved
  def __add__(self,other):
    if len(other) > 0 and other.name in self:
      for item in other.keys():
        self[other.name]+=other[item]
    else:
      self[other.name]=other
    if len(self) > 0:
      self.size=self.free=self.reserved=0
      for key in self:
        self.size += self[key].size
        self.free += self[key].free
        self.reserved += self[key].reserved
    return self
  def __str__(self):
    ret=self.outlined()
    return ret
  def outlined(self,outline=""):
    ret=[]
    ret.append("{0}Name: '{1}', Size: {2}, Used: {3}, Reserved: {4}, Free: {5}, FreePercent: {6}%".format(outline,self.name,self.size,self.size-self.free-self.reserved,self.reserved,self.free,100*float(self.free)/self.size))
    for key, value in sorted(self.iteritems(), key=lambda (k,v): v.free):
      ret.append(outline+"{0}".format(self[key].outlined(outline+"  ")))
    return "\n".join(ret)

if __name__ == "__main__":
  from re import split
  from optparse import OptionParser, OptionGroup
  import csv

  parser = OptionParser()
  parser.add_option("-i", "--inputfile", dest="inputfile", help="The file to read the asm data from (default /tmp/collect_asm_diskgroups.txt).", default='/tmp/collect_asm_diskgroups.txt')
  parser.add_option("-c", "--clusterinfo", dest="clusterfile", help="The file to read the cluster info from (default /tmp/collect_srvinfo.csv).", default='/tmp/collect_srvinfo.csv')
  parser.add_option("-r", "--reserve", dest="reserve", help="The amount of used space to reserve on free space (default 0.2).", type='float',default=0.2)
  (options, args) = parser.parse_args()

  clusters={}
  with open(options.clusterfile) as csvfile:
    csvreader = csv.reader(csvfile, delimiter=';', quotechar='"')
    for cols in csvreader:
      srv,cluster=cols[1][:10].lower(),cols[-1]
      clusters[srv]=cluster
  srvrs=storage('all')
  with open(options.inputfile) as inputfile:
    for line in inputfile:
      line=line.replace('\n','')
      cols=split('[\t ]+',line)
      d,fg,dg,redundancy,srv,free,size=cols[3],cols[6],cols[2],cols[8],cols[0][0:10].lower(),float(cols[-2]),float(cols[-1])
      d=storage(d,size,free,options.reserve*(size-free))
      fg=storage(fg)
      fg+=d
      dg="{0} ({1})".format(dg,redundancy)
      dg=storage(dg)
      dg+=fg
      if srv in clusters:
        srv=clusters[srv]
      srv=storage(srv)
      srv+=dg
      srvrs+=srv
    print srvrs
