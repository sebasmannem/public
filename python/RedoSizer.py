#!/usr/bin/env python2

def total_seconds(td):
    ret = (td.microseconds + (td.seconds + td.days * 24.0 * 3600) * 10**6) / 10**6
    return max([0.5,ret])

import datetime
import argparse
import sys
import math

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument(dest='files', nargs='+', help='the files to proces')
parser.add_argument('--start', dest='dtstart', default='Mon Jan 01 00:00:00 1900', help='only proces starting this date/time. Formatted as --alertformat.')
parser.add_argument('--end', dest='dtend', default='Fri Dec 31 23:59:59 2100', help='only proces until this date/time. Formatted as --alertformat.')
parser.add_argument('--alertformat', dest='dtalertformat', default='%a %b %d %H:%M:%S %Y', help='format of date time in alertfiles. See https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior for more info.')
parser.add_argument('--string', dest='search', default='(LGWR switch)', help='String that defines a logswitch.')
parser.add_argument('--precission', dest='precission', default=20, type=int, help='Number of groups the samples are split in.')

args = parser.parse_args()
try:
    dtstart=datetime.datetime.strptime(args.dtstart, args.dtalertformat)
    dtend=datetime.datetime.strptime(args.dtend, args.dtalertformat)
except:
    print("Could not proces arguments. Invalid from, until or not matching datetime format?")
    sys.exit(1)

detects=0
dates=[]
for filename in args.files:
    try:
        f=open(filename)
    except:
        print("Could not read file {0}.")
        continue
    for l in f:
        l=l.strip()
        try:
            d=datetime.datetime.strptime(l, args.dtalertformat)
        except:
            pass
        try:
            if args.search in l:
                detects +=1
                if d>dtstart and d<dtend:
                    dates.append(d)
        except:
            pass

sorted_dates=sorted(set(dates))
sphs=[]
for i in range(len(sorted_dates)-1):
    delta = dates[i+1]-dates[i]
    sphs.append(3600.0/total_seconds(delta))

sphs=sorted(sphs)
print("files: {0}".format(", ".join(args.files)))
print("first: {0}".format(min(dates)))
print("last: {0}".format(max(dates)))
print("detects: {0}".format(detects))
print("samples: {0}".format(len(dates)))
print("timedeltas: {0}".format(len(sphs)))
print("min switches/hour: {0}".format(min(sphs)))
print("avg switches/hour: {0}".format(sum(sphs)/len(sphs)))
print("max switches/hour: {0}".format(max(sphs)))

hdr='| sample | switches / hour |'
print(len(hdr)*'-')
print(hdr)
print(len(hdr)*'-')

stepsize = float(len(sphs)) / (args.precission - 1)
for n in range(args.precission - 1):
    i = int(n * stepsize)
    print("| {0:6} | {1:15.4f} |".format(i, sphs[i]))
print("| {0:6} | {1:15.4f} |".format(len(sphs), sphs[-1]))

print(len(hdr)*'-')

