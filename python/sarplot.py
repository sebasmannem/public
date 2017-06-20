#!/usr/bin/python3
'''
import multiprocessing
multiprocessing.cpu_count()
'''
import glob

numcpus = None

import datetime
#Lets just set dt to today for now
dt = datetime.datetime.now()
dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

import re
line_re     = re.compile('^([0-9]{2}:){2}[0-9]{2} +')
date_re     = re.compile('^ *([0-9]{2}/){2}[0-9]{2} *$')
numcpus_re  = re.compile('\(([0-9]*) CPU\)')
splitter_re = re.compile('[ \t]+')

import subprocess

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create graph from sar data.')
    parser.add_argument('-s', '--start', help='Startdate of graph')
    parser.add_argument('-e', '--end', help='Enddate of graph')
    parser.add_argument('-l', '--lines', help='Lines to add to graph (, seperated)')
    parser.add_argument('-f', '--outfile', help='Send output to file instead of x11 window.')
    
    options = parser.parse_args()

    if options.outfile:
        import matplotlib
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    samples = {}
    for f in glob.iglob('/var/log/sa/sa[0-9][0-9]'):
        sar = subprocess.Popen(['/usr/bin/sar', '-f', f], stdout=subprocess.PIPE, env={'LANG': 'en_US.UTF-8'})
        for l in sar.stdout:
            try:
                l=l.decode()
                l=l.strip()
                if line_re.search(l):
                    cols = splitter_re.split(l)
                    hour, minute, second = tuple([ int(n) for n in cols[0].split(':') ])
                    timestamp = dt + datetime.timedelta(0, hour*3600 + minute * 60 + second)
                    if cols[1] == 'LINUX':
                        m = numcpus_re.search(l)
                        if m:
                            numcpus = int(m.groups(1)[0])
                            continue
                        else:
                            print(l)
                    elif cols[1] == 'CPU':
                        HDR = cols[2:]
                        continue
                    elif cols[1] == 'all':
                        factor = numcpus
                    else:
                        factor = 1
                    try:
                        sample = [ factor * float(f) for f in cols[2:] ]
                        samples[timestamp] = sample
                    except Exception as e:
                        print(e)
                        print(l)
                else:
                    cols=l.split('\t')
                    try:
                        if date_re.search(cols[1]):
                            dt = datetime.datetime.strptime(cols[1].strip(), '%m/%d/%y')
                    except:
                        pass
                    try:
                        m = numcpus_re.search(cols[3])
                        if m:
                            numcpus = int(m.groups(1)[0])
                    except Exception as e:
                        pass
            except Exception as e:
                print(e)
    
    numlines = max([ len(samples[ts]) for ts in samples ])
    x        = sorted(samples.keys())

    if options.start:
        defaultstart = x[0].strftime('%Y-%m-%d %H:%M:%S')
        start = datetime.datetime.strptime(options.start + defaultstart[len(options.start):], '%Y-%m-%d %H:%M:%S')
    else:
        start = x[0]

    if options.end:
        defaultend   = x[-1].strftime('%Y-%m-%d %H:%M:%S')
        end = datetime.datetime.strptime(options.end + defaultend[len(options.end):], '%Y-%m-%d %H:%M:%S')
    else:
        end   = x[-1]
    print(start.strftime('%Y-%m-%d %H:%M:%S'))
    print(end.strftime('%Y-%m-%d %H:%M:%S'))
    x = [ dt for dt in x if dt > start and dt < end ]

    if options.lines:
        enabled_lines = [ int(l) for l in  options.lines.split(',') ]
    else:
        enabled_lines = [ l for l in range(numlines) ]

    lines = []
    for n in range(numlines):
        if n not in enabled_lines:
            continue
        line = []
        for ts in x:
            try:
                v = samples[ts][n]
            except:
                v = 0
            line.append(v)
        lines.append(line)
    
    fig, ax = plt.subplots()
    for i in range(len(lines)):
        line, = ax.plot(x, lines[i], '-', linewidth=2, label=HDR[i])
    
    fig.autofmt_xdate()
    ax.legend(loc='upper left')
    if options.outfile:
        plt.savefig(options.outfile)
    else:
        plt.show()
