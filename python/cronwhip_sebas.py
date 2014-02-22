#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2011-2013  Xyne
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# (version 2) as published by the Free Software Foundation.
#
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Rewrite of the original cronwhip in Perl.

import argparse
import datetime
import glob
import re
import shlex
import subprocess
import sys
import time


# Notes
# (minute, hour, monthday, month, weekday)
# (0-59, 0-23, 1-31, 1-12, 0-7)

# Define special times.
SPECIALS = {
#   'reboot' : # ?
  '@yearly'  : '0 0 1 1 *',
  '@monthly' : '0 0 1 * *',
  '@weekly'  : '0 0 * * 0',
  '@daily'   : '0 0 * * *',
  '@hourly'  : '0 * * * *'
}
SPECIALS['@annually'] = SPECIALS['@yearly']
SPECIALS['@midnight'] = SPECIALS['@daily']

MONTHS = dict(zip(
  ('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'),
  (str(x) for x in range(1,13))
))

DAYS = dict(zip(
  ('sun','mon','tue','wed','thu','fri','sat'),
  (str(x) for x in range(7))
))


TIME_DISPLAY_FMT = "%Y-%m-%d %H:%M"
TIME_DISPLAY_EXAMPLE = 'YYYY-mm-dd HH:MM'


def parse_crontab(tab):
  """
  Parse the contents of a crontab.
  """
  reg = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S.*)$')

  for line in tab.split('\n'):
    entry = line.strip()
    # Skip comments and blank lines.
    if not entry or entry[0] == '#':
      continue
    elif entry[0] == '@':
      special = entry.split(None, 1)[0]
      try:
        entry = entry.replace(special, SPECIALS[special])
      except KeyError:
        raise ValueError("failed to parse crontab entry (%s)" % line)
    m = reg.match(entry)
    if m:
      yield list(m.groups())
    else:
      raise ValueError("failed to parse crontab entry (%s)" % line)



def replace_asterisks(entry):
  """
  Replace asterisks with corresponding ranges.
  """
  entry[0] = entry[0].replace('*', '0-59')
  entry[1] = entry[1].replace('*', '0-23')
  entry[2] = entry[2].replace('*', '1-31')
  entry[3] = entry[3].replace('*', '1-12')
  entry[4] = entry[4].replace('*', '0-6')
  return entry



def replace_names(entry):
  """
  Replace month and weekday names with corresponding numerical values.
  """
  entry[3] = entry[3].lower()
  for m,v in MONTHS.items():
    if m == entry[3]:
      entry[3] = v
      break
  entry[4] = entry[4].lower()
  for d,v in DAYS.items():
    if d == entry[4]:
      entry[4] = v
      break
  return entry



def insert_tuples(entry):
  """
  Replace ranges, lists and single entries with corresponding tuples.
  """
  for i in range(5):
    ns = set()
    for rng in entry[i].split(','):
      if '-' in rng:
        if '/' in rng:
          rng, step = rng.split('/',1)
          step = int(step)
        else:
          step = 1
        a,b = [int(x) for x in rng.split('-',1)]
        b += 1
        ns |= set(range(a,b)[::step])
      else:
        ns.add(int(rng))
    # Make sure 7 is in there if Sunday is specified, because the time_struct
    # range is 0-6 with Monday as 0, thus the comparison will be made by adding
    # 1.
    if i == 4 and 0 in ns:
      ns.add(7)
    entry[i] = tuple(sorted(ns))
  return entry



# This may be a lazy way to do it, but it works.
def should_be_run(entry, t):
  """
  Check if an entry should be run at a given time.

  Accepts a struct_time object.
  """
  if not t.tm_min in entry[0]:
    return False
  elif not t.tm_hour in entry[1]:
    return False
  elif not t.tm_mday in entry[2]:
    return False
  elif not t.tm_mon in entry[3]:
    return False
  elif not t.tm_wday+1 in entry[4]:
    return False
  else:
    return True



def get_missed_cron_jobs(crontab, start, end=None, localtime=True, first_only=True):
  """
  Parse the given crontab and return cronjobs that would have been run
  in the given interval.
  """
  if isinstance(start, time.struct_time):
    start = time.mktime(start)
  if end == None:
    end = time.time()
  elif isinstance(end, time.struct_time):
    end = time.mktime(end)
  if localtime:
    t_end = time.localtime(end)
  else:
    t_end = time.gmtime(end)
  for entry in parse_crontab(crontab):
    entry = insert_tuples(replace_asterisks(replace_names(entry)))
    if start is None:
      yield entry[5], t_end
    else:
      # Brute force replay... there may be a better way but this works perfectly.
      for t in range(int(start), int(end), 60):
        if localtime:
          t = time.localtime(t)
        else:
          t = time.gmtime(t)
        if should_be_run(entry, t):
          yield entry[5], t
          if first_only:
            break



def run_job(job, shell='/bin/sh'):
  """
  Run a cronjob.
  """
  # Not sure about the best way to parse "%".
  cmd = [shell]
  inp = None
  for word in shlex.split(job):
    if inp == None:
      if word[0] == '%':
        inp = word[1:]
      else:
        cmd.append(word)
    else:
      if word[0] == '%':
        c = '\n'
      else:
        c = ' '
      inp += c + word[1:]
  run_cmd(cmd, inp)



def cmd_to_str(cmd):
  """
  Convert a list command to a shell-escaped string command.
  """
  return ' '.join(shlex.quote(x) for x in cmd)


def print_tag_and_message(tag, msg):
  """
    Simple STDERR output formatter.
  """
  sys.stderr.write(tag)
  msg = msg.strip()
  if '\n' in msg:
    for line in msg.split('\n'):
      sys.stderr.write('\n  ' + line)
  else:
    sys.stderr.write(' ' + msg)
  sys.stderr.write('\n')



def run_cmd(cmd, inp=None):
  """
  Run a command and pass the optional input to stdin.

  Returns output from stdout.
  """
  p = subprocess.Popen(
    cmd,
    shell=False,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
  )
  if inp:
    output, error = p.communicate(input=inp.encode())
  else:
    output, error = p.communicate()
  e = p.wait()
  if e != 0:
    print_tag_and_message('command exited with {:d}:'.format(e), cmd_to_str(cmd))
    if inp:
      print_tag_and_message('stdin:', inp)
    print_tag_and_message('stderr:', error.decode())
    sys.exit(1)
  return output.decode()



def get_crontab(args=None):
  """
  Read the default crontab.
  """
  cmd = ['crontab', '-l']
  if args:
    cmd += args
  return run_cmd(cmd)



def get_last_shutdown_interval_from_wtmp(wtmp_paths=None):
  """
  Parse the output of "last -x" to get the last shutdown time.
  """
  cmd = ['last', '-x']
  if wtmp_paths:
    cmds = [cmd + ['-f', p] for p in wtmp_paths]
  else:
    cmds = [cmd]

  for cmd in cmds:
    last = run_cmd(cmd)
    # Reverse it so get the time when the file begins and then step through it.
    lines = last.strip().split('\n')
    lines.reverse()
    begins = ' '.join(lines[0].split()[1:])
    begin_t = time.strptime(begins, 'begins %a %b %d %H:%M:%S %Y')
    year = begin_t.tm_year
    last_t = begin_t
    shutdown = None
    # Step through all entries to make sure no years are skipped.
    # I do not know if this will catch everything.
    # It may also be overkill as is.
    for line in lines[2:]:
      l = line.split()
      mon = l[-6]
      mday = l[-5]
      hhmm = l[-4]
      sfmt = '%s %s %s %s'
      tfmt = '%Y %b %d %H:%M'
      # Rotated wtmp files may use "gone - no logout" as the end time.
      try:
        t = time.strptime(sfmt % (year, mon, mday, hhmm), tfmt)
      except ValueError:
        continue
      if t.tm_mon < last_t.tm_mon:
        year += 1
        t = time.strptime(sfmt % (year, mon, mday, hhmm), tfmt)
      last_t = t
      if l[0] == 'shutdown':
        shutdown = (t, l[-1])

    if shutdown:
      down = shutdown[0]
      delta = shutdown[1][1:-1]
      if '+' in delta:
        d, hm = delta.split('+',1)
      else:
        d = 0
        hm = delta
      h,m = hm.split(':',1)
      delta = datetime.timedelta(days=int(d), hours=int(h), minutes=int(m))
      up = (datetime.datetime.fromtimestamp(time.mktime(down)) + delta).timetuple()
      return down, up
  return None, None



def parse_time_arg(s, named_times):
  """
  Parse a command-line time argument.
  """
  try:
    return named_times[s]
  except KeyError:
    try:
      return time.strptime(s, TIME_DISPLAY_FMT)
    except ValueError:
      return None



def parse_time_arg_or_die(s, *args, **kwargs):
  """
  Parse a command-line time argument or exit with an error.
  """
  t = parse_time_arg(s, *args, **kwargs)
  if t is None:
    sys.exit('error: failed to parse time argument "{}"'.format(s))
  else:
    return t



def parse_args(args=None):
  """
  Parse command-line arguments.
  """
  parser = argparse.ArgumentParser(
    description='Run missed cronjobs that would have been run while the system was down. It should be run once right after startup.',
    epilog='The start and end times may be given with the format "{}" or as "now", "shutdown" or "reboot".'.format(TIME_DISPLAY_EXAMPLE),
  )
  parser.add_argument(
    '-n', '--dry-run', action='store_true',
    help='Print the list of cronjobs that would be run.'
  )
  parser.add_argument(
    '-v', '--verbose', action='store_true',
    help='Switch to verbose mode.'
  )
  parser.add_argument(
    '--start',
    help='Start of missed interval. If none is given, the system shutdown time recorded in wtmp will be used.'
  )
  parser.add_argument(
    '--end',
    help='End of missed interval. If none is given, the system reboot time recorded in wtmp will be used.'
  )
  parser.add_argument(
    '--interval', type=float,
    help='The length of the missed interval, in hours. Non-integer values are allowed. The interval is calculated from the start time, unless the "end" option is given without the "start" option. For example, use "--end now --interval 2" to run all jobs from the last 2 hours."'
  )
  parser.add_argument(
    '--show-missed', action='store_true',
    help='Show the list of missed cronjobs.'
  )
  parser.add_argument(
    '--skip', metavar='<filepath>',
    help='A list of jobs, one per line, that should not be run. Only the command should be included on the line.'
  )
  return parser.parse_args(args)



def main_original(args=None):
  args = parse_args(args)
  wtmp_paths = sorted(glob.glob('/var/log/wtmp*'))
  shutdown, reboot = get_last_shutdown_interval_from_wtmp(wtmp_paths)
  now = time.gmtime(time.time())
  named_times = {
    'now' : now,
    'shutdown' : shutdown,
    'reboot' : reboot,
  }

  if args.interval:
    interval = datetime.timedelta(hours=args.interval)
  else:
    interval = None

  if args.start:
    start = parse_time_arg_or_die(args.start, named_times)
    if interval:
      end = (datetime.datetime.fromtimestamp(time.mktime(start)) + interval).timetuple()
    elif args.end:
      end = parse_time_arg_or_die(args.end, named_times)
    else:
      end = reboot

  elif args.end:
    end = parse_time_arg_or_die(args.end, named_times)
    if interval:
      start = (datetime.datetime.fromtimestamp(time.mktime(end)) - interval).timetuple()
    else:
      start = shutdown

  elif args.interval:
    start = shutdown
    end = (datetime.datetime.fromtimestamp(time.mktime(start)) + interval).timetuple()

  else:
    start = shutdown
    end = reboot

  if start is not None and end is not None and start >= end:
    a = time.strftime(TIME_DISPLAY_FMT, start)
    b = time.strftime(TIME_DISPLAY_FMT, end)
    sys.exit('error: invalid interval [{}, {}]'.format(a,b))

  if start is None:
    print_tag_and_message('warning:', '''failed to detect last shutdown interval
(this may be due to missing wtmp files or incomplete output from "last -x")
''')
#     sys.exit(1)
  crontab = get_crontab()

  skipped = set()
  try:
    if args.skip:
      with open(args.skip, 'r') as f:
        for line in f:
          skipped.add(line.rstrip('\n'))
  except FileNotFoundError:
    print_tag_and_message('warning:', '{} does not exist'.format(args.skip))

  if args.show_missed:
#     print(time.strftime(TIME_DISPLAY_FMT,start), "down")
    for job, t in sorted(
      get_missed_cron_jobs(crontab, start, end, first_only=False),
      key=lambda x: x[1]
    ):
      if job in skipped:
        continue
      else:
        print(time.strftime(TIME_DISPLAY_FMT,t), job)
#     print(time.strftime(TIME_DISPLAY_FMT,end), "up")
  else:
    for job, t in get_missed_cron_jobs(crontab, start, end):
      if job in skipped:
        continue
      elif args.dry_run:
        print(job)
      else:
        if args.verbose:
          print(job)
        run_job(job)


def run(main, *args, **kwargs):
  try:
    main(*args, **kwargs)
  except KeyboardInterrupt:
    pass
  except Exception as e:
    print_tag_and_message('error:', str(e))

if __name__ == '__main__':
  run(main_original)
