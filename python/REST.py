#!/usr/bin/python

def formatted(item, indent=0):
  if type(item) is dict:
    ret="\n"
    for k in sorted(item.keys()):
      ret+="{0}{1}: {2}\n".format(indent*"  ", k, formatted(item[k], indent+2))
  elif type(item) is list:
    ret="list:\n"
    for e in sorted(item):
      ret+="{0}{1}\n".format(indent*"  ", formatted(e, indent+2))
  elif type(item) is unicode:
    try:
      return str(item)
    except:
      return item.__repr__()
  elif type(item) is str:
    return item
  elif type(item) is bool:
    return item.__repr__()
  elif type(item) is int:
    return str(item)
  elif not item:
    return "None"
  else:
    return "unknown: "+item.__repr__()
  return ret

def buildIPOObject(root, subDefinitions):
  try:
    rootObj = subDefinitions[root]
  except:
    return root

  try:
    props = rootObj['properties']
  except:
    return root
  
  ret = {}
  for subName in props:
    subType = subDefinitions[root]['properties'][subName]['type']
    ret[subName] = buildIPOObject(subType, subDefinitions)
  return ret

if __name__ == "__main__":
  from optparse import OptionParser
  import urllib2
  import urllib
  import os
  import json
  import sys
  parser = OptionParser(usage='''Usage: %prog [options] [folders]''')
  parser.add_option("-u", "--url", dest="url", default="https://vip00000a44a001.frs00000.localdns.nl:8443", help="The url of ICO.")
  parser.add_option("--item", "--id", dest="itemid", default=False, help="The id of the item to process.")
  parser.add_option("-a", "--action", dest="action", default='list', help="What should I do? (list, show, start).")
  parser.add_option("-t", "--type", dest="itemtype", default='c', help="What type of object(s)? (offering, category, parameters).")
  parser.add_option("--limit", dest="list_limit", default=100, help="Limit items in list.")
  parser.add_option("--username", dest="username", help="List all the available offerings.")
  parser.add_option("-p", "--password", dest="password", help="List all the available offerings.")
  parser.add_option("--uncached", dest="cached", default=True, action="store_false", help="Refresh cached version of exposed items before using it.")
  parser.add_option("-x", "--debug", dest="debug", default=False, action="store_true", help="Debuging option.")
  (options, args) = parser.parse_args()

  password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()

  if options.username:
    usr=options.username
    if options.password:
      pw=options.password
    else:
      try:
        pw=os.environ['ICO_PW']
      except:
        print("Please specify your ICO password")
        pw=raw_input()
    password_manager.add_password(None, options.url, usr, pw)

  auth = urllib2.HTTPBasicAuthHandler(password_manager) # create an authentication handler
  opener = urllib2.build_opener(auth) # create an opener with the authentication handler
  urllib2.install_opener(opener) # install the opener...


  action=options.action.lower()[0]
  ICOType=options.itemtype.lower()[0]

  if ICOType == 'c':
    if action == 'l':
      url="{0}/orchestrator/v2/categories?_limit={1}".format(options.url, options.list_limit)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      j=json.loads(handler.read())
      if options.debug:
        print(formatted(j))
      cats={}
      for cat in j['items']:
        cats[cat['item']['id']] = cat
      for i in sorted(cats.keys()):
        cat=cats[i]
        item=cat['item']
        print("{0:10}: {1}".format(i, item['name']))
        if options.debug:
          print(cat)
    elif action == 's':
      url="{0}/orchestrator/v2/categories/{1}".format(options.url, options.itemid)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      j=json.loads(handler.read())
      if options.debug:
        print(j)

      url="{0}/orchestrator/v2/offerings?category={1}".format(options.url, options.itemid)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      j=json.loads(handler.read())
      offs={}
      for off in j['items']:
        offs[off['item']['id']] = off

      j['offerings'] = offs2 = []
      for i in sorted(offs.keys()):
        off=offs[i]
        item=off['item']
        offs2.append("{0:10}: {1}".format(i, item['name']))
        if options.debug:
          print(off)
      print formatted(j)

    else:
      print "unknown action. Please specify one with -a [list, show]."
      sys.exit(1)

  elif ICOType == 'o':
    if action == 'l':
      url="{0}/orchestrator/v2/offerings?_limit={1}".format(options.url, options.list_limit)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      j=json.loads(handler.read())
      offs={}
      for off in j['items']:
        offs[off['item']['id']] = off
      for i in sorted(offs.keys()):
        off=offs[i]
        item=off['item']
        print("{0}: {1}".format(i, item['name']))
        if options.debug:
          print(off)
    elif action == 's':
      url="{0}/orchestrator/v2/offerings/{1}".format(options.url, options.itemid)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      json_offering=json.loads(handler.read())
      if options.debug:
        print(formatted(json_offering))

      process_name=json_offering['item']['process']
      process_app_id=json_offering['item']['process_app_id']
      if options.debug: 
        print "process_name: {0}, process_app_id {1}".format(process_name, process_app_id)

      if options.cached:
        f=open('/tmp/sebas.txt', 'r')
        json_exposed = json.loads(f.read())
        f.close()
      else:
        url="{0}/rest/bpm/wle/v1/exposed".format(options.url)
        print url
        request = urllib2.Request(url)
        handler = urllib2.urlopen(request)
        exposed = handler.read()
        f=open('/tmp/sebas.txt', 'w')
        f.write(exposed)
        f.close()
        json_exposed = json.loads(exposed)

      for item in json_exposed['data']['exposedItemsList']:
        if item['display'] == process_name and item['processAppID'] == process_app_id:
          json_offering['exposed']=item
          break

      if options.debug:
        print formatted(json_offering['exposed'])

      url="{0}/rest/bpm/wle/v1/processModel/{1}?".format(options.url, json_offering['exposed']['itemID'])
      url+=urllib.urlencode({'processAppId': process_app_id, 'parts': 'all'})
      if options.debug:
        print url
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      json_processmodel = json.loads(handler.read())
      IPOType = json_processmodel['data']['DataModel']['inputs']['inputParameterObject']['type']
      subTypes = json_processmodel['data']['DataModel']['validation']
      IPOObject = {IPOType: buildIPOObject(IPOType, subTypes)}
      IPOObjectJSON = json.dumps(IPOObject)

      json_offering['inputParameterObject'] = IPOObject
#      print formatted(IPOObject)

      print formatted(json_offering)
    else:
      print "unknown action. Please specify one with -a [list, show, start]."
      sys.exit(1)
  elif ICOType == 'p':
    if action == 'list':
      url="{0}/orchestrator/v2/offerings/{1}/parameters".format(options.url, options.itemid)
      request = urllib2.Request(url)
      handler = urllib2.urlopen(request)
      j=json.loads(handler.read())
      print(formatted(j))
    else:
      print "unknown action. Please specify one with -a [list]."
      sys.exit(1)

  else:
    print "unknown item type '{0}'. Please specify one with -t [offering, category, parameters].".format(options.itemtype)
