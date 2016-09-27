#!/usr/bin/env python2
import urllib2
import argparse
import xml.etree.ElementTree as ET
import zlib
import re
import sys

def get_ns_from_tag(tag):
    if '}' in tag:
        return { 'default': tag.split('}')[0].lstrip('{')}
    else:
        return { 'default': '' }

def tag_without_ns(tag):
    if '}' in tag:
        return tag.split('}')[1]
    else:
        return tag

def listoflists_to_gnrtr(listoflists):
    mylist=listoflists.pop()
    if len(listoflists)>0:
        for sub in listoflists_to_gnrtr(listoflists):
            if not sub:
                continue
            for e in mylist:
                ret=tuple(sub+(e,))
                yield ret
    else:
        for e in mylist:
            yield (e,)

class repo_exception(Exception):
    pass

class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"

def repo2dict(repo):
    if repo[-1] != '/':
        repo += '/'
    try:
        url=repo+"/repodata/repomd.xml"
        request = urllib2.Request(url)
        handler = urllib2.urlopen(request)
    except:
        raise repo_exception('No ./repodata/repomd.xml')

    repomd={}
    try:
        root = ET.XML(handler.read())
    except:
        raise repo_exception('Invalid ./repodata/repomd.xml')
    ns = get_ns_from_tag(root.tag)
    
    try:
        for data in root.findall('default:data', ns):
            location = data.find('default:location', ns)
            repomd[data.attrib['type']] = location.attrib['href']
        url=repo+repomd['primary']
    except:
        raise repo_exception('Could not find <data type="primary"> in ./repodata/repomd.xml')
    try:
        request = urllib2.Request(url)
        handler = urllib2.urlopen(request)
    except:
        raise repo_exception('Could not read "primary.xml.gz" from repo.')
    try:
        decompressed_data=zlib.decompress(handler.read(), 16+zlib.MAX_WBITS)
    except:
        raise repo_exception('Could not decompress "primary.xml.gz".')
    try:
        root = ET.XML(decompressed_data)
    except:
        raise repo_exception('Could not parse "primary.xml.gz".')
    ns = get_ns_from_tag(root.tag)

    pcks = []
    for package in root.findall('default:package', ns):
        try:
            pck = {}
            for e in package:
                tag=tag_without_ns(e.tag)
                if tag in ['name','arch']:
                    pck[tag] = e.text
                elif tag == 'location':
                    rpm_url = repo+e.attrib['href']
                    try:
                        dummy=urllib2.urlopen(HeadRequest(rpm_url))
                        pck['location'] = rpm_url
                    except:
                        raise repo_exception('Package {0} does not exist.'.format(rpm_url))
                elif tag == 'version':
                    pck['version'] = e.attrib['ver']
            pcks.append(pck)
        except Exception, e:
            print(e)
    if len(pcks) == 0:
        raise repo_exception('No package info found.')
    return pcks

def urls_generator(urls):
    '''
    The idea of this function, is that you can parse a url containing lists, 
    and that it will expand this to a list of all the possible urls.
    '''
    list_finder_re = re.compile('\[(.*?)\]')
    url_lists=list_finder_re.findall(urls)
    lists=[]
    for l in url_lists:
        urls=urls.replace("["+l+"]","{"+str(len(lists))+"}",1)
        lists.append(l.split(','))
    for elements in listoflists_to_gnrtr(lists):
        yield urls.format(*elements)

    
parser = argparse.ArgumentParser(description='Lists all packages in a yum repo')
parser.add_argument('-u', '--urls', default='http://testbase.splendiddata.com/postgrespure/3/[centos/7,fedora/23,rhel/7Server,sles/12]/[x86_64,ppc64le]/', help='urls of repos to check packages from. you can use expansion with [value1,value1])')

options = parser.parse_args()
repos={}
print("Scanning repos ({0}):".format(options.urls))
for repo in urls_generator(options.urls):
    try:
        repos[repo] = repo2dict(repo)
    except Exception, e:
        print(" - {0}: {1}".format(repo, e))
print

packages_per_repo={}
packages_per_repo['All']=set()
for repo in repos.keys():
    packages_per_repo[repo] = set([ p['name'] for p in repos[repo] ])
    packages_per_repo['All']|=packages_per_repo[repo]

print("Packages per repo:\n")
for repo in sorted(packages_per_repo.keys()):
    print("Repo: {0}".format(repo))
    existing=packages_per_repo[repo]
    if len(existing) > 0:
        print("Existing:\n - {0}".format('\n - '.join(sorted(existing))))
    missing=packages_per_repo['All'] - packages_per_repo[repo]
    if len(missing) > 0:
        print("Missing:\n - {0}".format('\n - '.join(sorted(missing))))
    print
