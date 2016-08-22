#!/bin/env python
import re
from datetime import datetime,timedelta
import time
#Export: Release 11.2.0.3.0 - Production on Sat May 24 20:44:09 2014
#Import: Release 10.2.0.5.0 - 64bit Production on Sunday, 27 April, 2014 21:14:22
re_start=re.compile('^(Import|Export).* on [a-zA-Z]*,?(.*)$')
re_time=re.compile('\d?\d:\d\d:\d\d')
re_year=re.compile('\d{4}')
re_month=re.compile('[A-Z][a-z]+')
re_day=re.compile(' (\d{1,2}) ')

#. . exported "SPXP_SPX"."IFM_LA_WERTE"                   8.507 GB 30399448 rows
#. . imported "SM2P_SPX"."MA_BENUTZERFELD"                1.581 MB   52304 rows
re_row=re.compile('^. . (im|ex)ported "(\w+)"."(\w+)" *([0-9.]+) ([a-zA-Z]?)B +(\d+) rows$')
#Job "ORADBA"."impdp_D031P_SHDP_SPX_D030P_SPX" completed with 9 error(s) at 01:16:50
#Job "ORADBA"."SYS_EXPORT_FULL_01" successfully completed at 21:26:58
re_end=re.compile('^Job .* completed.* at (\d\d:\d\d\:\d\d)$')
re_errors=re.compile('with (\d+) error\(s\)')
re_human=re.compile('([0-9.]+)([a-zA-Z]?)')

try:
  from humanfriendly import parse_size
except:
  def parse_size(val):
    human=re_human.search(val)
    if human:
      num,metric=human.groups()[-2:]
      if metric=='':
        factor=1
      else:
        factor=2**(('bkmgtp'.find(metric.lower()))*10)
      return float(num)*factor
    else:
      return 0

def parseFile(file):
  global jobs
  for line in file:
    line=line.replace("\n","")
    started=re_start.search(line)
    if started:
      myjob={'tables': 0, 'bytes': 0, 'rows': 0, 'schemas': set(), 'type': started.groups()[0]}
      started=started.groups()[1]
      startyear=re_year.search(started)
      startyear=startyear.group(0)
      startmonth=re_month.search(started)
      startmonth=startmonth.group(0)[0:3]
      starttime=re_time.search(started)
      starttime=starttime.group(0)
      startday=re_day.search(started)
      startday=startday.group(1)
      startdate=" ".join((startday,startmonth,startyear))
      myjob['starttime']=datetime.strptime(" ".join((startdate,starttime)),'%d %b %Y %H:%M:%S')
    row=re_row.search(line)
    if row:
      linetotals=row.groups()[-5:]
      myjob['schemas'].add(linetotals[0])
      myjob['tables']+=1
      myjob['bytes']+=parse_size(linetotals[2]+linetotals[3])
      myjob['rows']+=int(linetotals[4])
    ended=re_end.search(line)
    if ended:
      endtime=ended.groups()[-1]
      myjob['endtime']=datetime.strptime(startdate+' '+endtime,'%d %b %Y %H:%M:%S')
      if  myjob['endtime']< myjob['starttime']:
        myjob['endtime']+=timedelta(days=1)
      jobs.append(myjob)


#      duration=endtime-starttime
      #vanaf 2.7 bestaat de total_seconds() method...
#      duration=duration.days*24*3600+duration.seconds
#      print "type: {0},started: {1}, ended: {2}, duration: {3}, schemas: {4}, tables: {5}, bytes: {6:6.4e}, rows: {7} speed: {8:6.4e} B/s".format(type,starttime.strftime('%d %B %Y %H:%M:%S'),endtime.strftime('%d %B %Y %H:%M:%S'),duration,",".join(schemas),tables,bytes,rows,float(bytes)/duration)

if __name__ == "__main__":
  from sys import stdin
  from optparse import OptionParser, OptionGroup
  import csv

  parser = OptionParser()
  parser.add_option("-s", "--stdin", dest="stdin", action="store_true", help="The amount of used space to reserve on free space (default 0.2).", default=False)
  (options, args) = parser.parse_args()

  jobs=[]

  if options.stdin:
    parseFile(stdin)
  for f in args:
    inputfile=open(f)
    parseFile(inputfile)
    inputfile.close()

  jobs=sorted(jobs, key=lambda job: job['starttime'])
  print "{0:^6} | {1:^20} | {2:^20} | {3:^6} | {4:^50} | {5:^4} | {6:^10} | {7:^10} | {8:^10}".format('type','start','stop','dur (s)','schemas','tbls','GB','rows','MB/s')
  print '-'*160
  for job in jobs:
    duration=job['endtime']-job['starttime']
    #vanaf 2.7 bestaat de total_seconds() method...
    duration=duration.days*24*3600+duration.seconds
    print "{0:6} | {1:>20} | {2:>20} | {3:6} | {4:50} | {5:4} | {6:10.4f} | {7:10} | {8:10.4f}".format(job['type'],job['starttime'].strftime('%d %b %Y %H:%M:%S'),job['endtime'].strftime('%d %b %Y %H:%M:%S'),duration,",".join(job['schemas']),job['tables'],float(job['bytes'])/2**30,job['rows'],float(job['bytes'])/duration/2**20)
