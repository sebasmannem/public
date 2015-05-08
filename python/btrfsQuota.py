#!/usr/bin/env python3

def bytes2human(n, format="%(value)i%(symbol)s"):
    """
    >>> bytes2human(10000)
    '9K'
    >>> bytes2human(100001221)
    '95M'
    """
    symbols = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    for symbol in reversed(symbols[1:]):
        if n >= prefix[symbol]:
            value = float(n) / prefix[symbol]
            return format % locals()
    return format % dict(symbol=symbols[0], value=n)

def human2bytes(s):
    """
    >>> human2bytes('1M')
    1048576
    >>> human2bytes('1G')
    1073741824
    """
    symbols = ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    letter = s[-1:].strip().upper()
    num = s[:-1]
    assert num.isdigit() and letter in symbols
    num = float(num)
    prefix = {symbols[0]:1}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])


import argparse
import subprocess

parser = argparse.ArgumentParser(
    description='Gives quotas from a BTRFS filesystem in a readable form'
)
parser.add_argument(
    '--unit', metavar='U', type=str,
    default='G',
    help='SI Unit, [B]ytes, K, M, G, T, P',
)
parser.add_argument(
    'mount_point', metavar='PATH', type=str,
    default='/',
    help='BTRFS mount point',
)
sys_args = parser.parse_args()
mount_point = sys_args.mount_point

subvolume_data = dict()
cmd = ["btrfs",  "subvolume", "list", mount_point]
for line in subprocess.check_output(cmd).splitlines():
    args = str(line, encoding='utf8').split()
    subvolume_data[int(args[1])] = args[-1]

print("subvol\t\t\t\t\t\tgroup         total    unshared")
print("-" * 79)
cmd = ["btrfs", "qgroup", "show", mount_point]
for line in subprocess.check_output(cmd).splitlines():
    args = str(line, encoding='utf8').split()

    try:
        subvolume_id = args[0].split('/')[-1]
        subvolume_name = subvolume_data[int(subvolume_id)]
    except:
        subvolume_name = "(unknown)"

    try:
        try:
            gid, total, unshared = args[0:3]
        except:
            continue
        try:
            total, unshared = bytes2human(float(total))+'iB', bytes2human(float(unshared))+'iB'
        except ValueError:
            pass
        if '/' in gid:
          print("%s\t%s\t%s %s" % (
            subvolume_name.ljust(40),
            gid,
            total.rjust(10), 
            unshared.rjust(10), 
        ))
    except IndexError:
        pass
