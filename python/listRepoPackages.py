#!/usr/bin/env python2
import urllib2
import argparse
import xml.etree.ElementTree as ET
import zlib

def get_ns_from_tag(tag):
    if '}' in tag:
        return { 'default': root.tag.split('}')[0].lstrip('{')}
    else:
        return { 'default': '' }

def tag_without_ns(tag):
    if '}' in tag:
        return tag.split('}')[1]
    else:
        return tag

parser = argparse.ArgumentParser(description='Lists all packages in a yum repo')
parser.add_argument('-u', '--url', default='http://dl.fedoraproject.org/pub/epel/7/x86_64/', help='url of repo to list packages from')

options = parser.parse_args()

repo = options.url
if repo[-1] != '/':
    repo += '/'

url=repo+"/repodata/repomd.xml"
request = urllib2.Request(url)
handler = urllib2.urlopen(request)
repomd={}
root = ET.XML(handler.read())
ns = get_ns_from_tag(root.tag)

for data in root.findall('default:data', ns):
    location = data.find('default:location', ns)
    repomd[data.attrib['type']] = location.attrib['href']

url=repo+repomd['primary']
request = urllib2.Request(url)
handler = urllib2.urlopen(request)
decompressed_data=zlib.decompress(handler.read(), 16+zlib.MAX_WBITS)
root = ET.XML(decompressed_data)
ns = get_ns_from_tag(root.tag)

pcks = []
for package in root.findall('default:package', ns):
    pck = {}
    for e in package:
        tag=tag_without_ns(e.tag)
        if tag in ['name','arch']:
            pck[tag] = e.text
        elif tag == 'location':
            pck['location'] = repo+e.attrib['href']
        elif tag == 'version':
            pck['version'] = e.attrib['ver']
    pcks.append(pck)

print(pcks)
