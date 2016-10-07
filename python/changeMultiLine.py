#!/usr/bin/env python2
import argparse
import re

parser = argparse.ArgumentParser(description='Relace a multiline text. Find by re and replace by another text.')
parser.add_argument('-r', '--regexp', help='regexp to search for (e.a. "my_list\s[.*?]")')
parser.add_argument('-n', '--newtext', help='new tekst to insert instead of found tekst (e.a. my_list [ "val1", "val2" ])')
parser.add_argument('-f', '--file', help='file to process.', nargs='+')

options = parser.parse_args()

#find_re = re.compile(options.regexp, re.MULTILINE)

for filename in options.file:
    with open(filename,'r') as f:
        s=f.read()
    m=find_re(s)
    for match in m.groups():
        print(m)

