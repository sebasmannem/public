#!/bin/python2

if __name__ == "__main__":
  import csv, re
  from sys import stdin, stdout, stderr
  from optparse import OptionParser, OptionGroup

  parser = OptionParser(usage='''Usage: %prog [options]
You can pipe (cat *.csv | %prog) the downloaded csv's into %prog and he will show some general summaries, like:
- How much is paid by/to per destination account.
- How much is paid/received per month.''')
  parser.add_option("-a", "--accounts", dest="accounts", help="Accounts that are your own.", default="")
  parser.add_option("-s", "--start", dest="start", help="A date from which to start. Format: YYYYMMDD. You can input a part only (e.a. 2013, will start at 20130101).", default="")
  parser.add_option("-e", "--end", dest="end", help="A date until whee to process. Format: YYYYMMDD. You can input a part only (e.a. 2013, will end at 20131231).", default="")
  parser.add_option("-m", "--month", dest="month", help="Specify a single month to process. Format: YYYYMM. Same as setting -e and -s to [month].", default="")
  parser.add_option("-f", "--filter", dest="filter", help="Only show some accounts.", default="")

  (options, args) = parser.parse_args()

  re_IBAN = re.compile('^([A-Z]{2})([0-9]{2})([A-Z]{4})([0-9]{10})$')
  re_Date = re.compile('[0-9]{2,4}-[0-9]{2}-[0-9]{2,4}')
  re_Time = re.compile('[0-9]{2}:[0-9]{2}(:[0-9]{2})?')
  re_BA = re.compile('^(.*?) / ([A-Z]+)')
  #NL078744-SODEXO / GOUDA         008 381063 MJW5FT               ING BANK NV PASTRANSACTIES
  rdr = csv.reader(stdin, delimiter=',', quotechar='"')
  myRek=options.accounts.split(",")

  if options.month != '':
    if options.start == '': options.start = options.month
    if options.end   == '': options.end   = options.month
  if len(options.start)<8:
    options.start=options.start+'00000000'[len(options.start)-8:]
  if len(options.end)<8:
    options.end=options.end+'99999999'[len(options.end)-8:]

  if options.filter != '':
    myFilter = options.filter.split(',')
  else:
    myFilter = None

  rekeningen = {}
  dagen = {}
  maanden = {}
  for flds in rdr:
    if flds[0].isdigit():
      dt=flds[0]
      oms=flds[1]
      if dt < options.start or dt > options.end:
        continue
      rek=flds[3]
      rekIBAN=re_IBAN.match(rek)
      if rekIBAN:
        rek=rekIBAN.group(4).lstrip('0')
      if rek in myRek:
        continue
      if rek == '':
        if flds[4] == 'GM':
          rek='giromaat'
          oms='Geld opemen met pin'
        elif flds[4] == 'BA':
          BA=re_BA.match(flds[8])
          if BA:
            rek=BA.group(1)
            oms="te {}".format(BA.group(2))
            #NL078744-SODEXO / GOUDA         008 381063 MJW5FT               ING BANK NV PASTRANSACTIES      
          else:
            rek='bet.aut.'
            oms='Betalen met pin'
        elif flds[4] == 'DV':
          rek='bankkosten'
          oms='Rente ed'
        else:
          rek=flds[1]
          rek=re_Date.sub('',rek)
          rek=re_Time.sub('',rek)
          rek=rek.strip()
          oms=''
      if myFilter:
        if rek not in myFilter:
          continue
      bedrag=float(flds[6].replace(',','.'))
      mnd=dt[0:6]
      if flds[5] == 'Af':
        pm=(0,bedrag)
        bedrag=0-bedrag
      else:
        pm=(bedrag,0)
      if rekeningen.has_key(rek):
        rekeningen[rek] = (rekeningen[rek][0] + bedrag, rekeningen[rek][1])
      else:
        rekeningen[rek] = (bedrag, oms)
      if dagen.has_key(dt):
        dagen[dt] = (pm[0]+dagen[dt][0],pm[1]+dagen[dt][1])
      else:
        dagen[dt] = pm
      if maanden.has_key(mnd):
        maanden[mnd] = (pm[0]+maanden[mnd][0],pm[1]+maanden[mnd][1])
      else:
        maanden[mnd] = pm

  keysize=max(len(rek) for rek in rekeningen.keys())
  omssize=max(len(rekeningen[rek][1]) for rek in rekeningen)
  numsize=9
  linesize=keysize+omssize+numsize+10

  print "-"*linesize
  print "| {3:^{0}s} | {4:^{1}s} | {5:^{2}s} |".format(keysize,omssize,numsize,'Account','Descr.', 'Total')
  print "-"*linesize
  for key in sorted(rekeningen,key= lambda rek: rekeningen[rek]):
    bedrag,oms = rekeningen[key]
    if key == '':
      key = 'Pinnen'
      oms = ''
    print "| {3:>{0}s} | {4:<{1}s} | {5:>{2}.2f} |".format(keysize,omssize,numsize,key,oms,bedrag)
  print "-"*linesize


  print "-"*43
  print "| {0:^6s} | {1:^8s} | {2:^8s} | {3:^8s} |".format('Month','earned','paid','Nett')
  print "-"*43
  for key in sorted(maanden.keys()):
    bij,af = maanden[key]
    print "| {0:<6s} | {1:>8.2f} | {2:>8.2f} | {3:>8.2f} |".format(key,bij,af,bij-af)
  print "-"*43
