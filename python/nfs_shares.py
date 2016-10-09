#!/usr/bin/python
'''
Wishlist:
- merge nfs_client and nfs_server into nfs_host
- --dump_spov (dump server point of view), --dump_cpov (dump client point of view)
- -u (unused shares)
- -e ((everyone) hint to using clients)
- -r (full report, being --dump_spov --dump_cpov -u -e)
- -a (autocollect: run collect.sh yourselve)
- change collect/nfs_shares.sh to python scipt returning csv of mountpoint and export (interpret autofs files instead of grep autofs files)
- -x (output XML)
- -g (generate autofs files)
'''

import socket
import subprocess
import re

DNS={}
nfs_clients={}
nfs_servers={}
nfs_hosts={}

re_export_split=re.compile(' +')
re_mount_split=re.compile('([a-zA-Z.0-9_]+):(/[a-zA-Z0-9_/]+)')
re_split=re.compile('[\t ]+')
re_uncomment = re.compile('#.*')
re_ip = re.compile('^([0-9]{1,3})(?:\.[0-9]{1,3}){3}$')
devnull=open('/dev/null','w')

def IPs_to_HOSTs(IPs):
  ret=[]
  for IP in IPs:
    try:
      ret.append(DNS[IP].hostname())
    except:
      pass
  return ret
def HOSTs_to_IPs(HOSTs):
  ret=[]
  for HOST in HOSTs:
    try:
      ret.append(DNS[HOST].ip())
    except:
      pass
  return ret
def DNSInfo(qry):
  #Kijken ofhij al eens is terug gezocht.
  if qry in DNS.keys():
    h=DNS[qry]
    return h.hostname(), h.ip(), h.resolvable()

  #Nope. DNS en reverse DNS terug zoeken.
  try:
    hostinfo = socket.gethostbyaddr(qry)
    return hostinfo[0], hostinfo[2][0], True
  except Exception as e:
    pass

  #Nope. IP adres zonder reverse DNS?
  if re_ip.match(qry):
    return '', qry, False

  #Nope. DNS zodner reverse DNS?
  try:
    #Als reverse DNS niet goed is ingesteld, geeft gethostbyaddr een fout, maar kan wellicht nog wel een IP opgezocht worden.
    ip = socket.gethostbyname(qry)
    return qry, ip, False
  except:
    pass

  #Nou ik weet het echt niet meer. Unresolvable...
    return qry, '', False
    
class host(list):
  __resolvable  = False
  def __init__(me, hostname):
    if hostname == '(everyone)':
      me.__fqdn = hostname
      me.__ip = ''
      DNS[hostname] = me
    else:
      me.__fqdn, me.__ip, me.__resolvable = DNSInfo(hostname)
    me.__hostname = me.__fqdn.split('.')[0]
    DNS[hostname] = me
    DNS[me.__fqdn] = me
    DNS[me.__hostname] = me
    DNS[me.__ip] = me
  def ip(me):
    return me.__ip
  def hostname(me):
    return me.__hostname
  def fqdn(me):
    return me.__fqdn
  def resolvable(me):
    return me.__resolvable
  def __str__(me):
    return "IP: {0}\nHOSTNAME: {1}".format(me.ip(), me.hostname())

class nfs_server(host):
  __exports={}
  def __init__(me,hostname):
    host.__init__(me,hostname)
    nfs_servers[me.ip()] = me
    nfs_servers[me.hostname()] = me
    exports = subprocess.Popen(('showmount','-e',me.ip()),stdout=subprocess.PIPE, stderr=devnull)
    for l in exports.stdout:
      l=l.replace('\n','')
      if l[0:16] != 'Export list for ':
        exp=nfs_export(l)
        me.append(exp)
        me.__exports[exp.path()]=exp
  def exp_by_path(me,path):
    for exp in me:
      p=exp.path()
      if path[0:len(p)] == p:
        return exp, path[len(p)+1:]
    return False, path
  def __str__(me):
    shares=[str(s) for s in me]
    return "{0}\nSHARES:\n  {1}""".format(host.__str__(me), "\n  ".join(shares))

class nfs_client(host):
  def __init__(me,hostname):
    host.__init__(me,hostname)
    nfs_clients[me.ip()] = me
    nfs_clients[me.hostname()] = me

    me.__invalid_mounts = []
    me.__mounts = []
  def __str__(me):
    mounts=[]
    invalid_mounts=[]
    for s in me.__mounts:
      srv,exp = s
      if srv.resolvable():
        mounts.append(" {0}: {1}".format(srv.hostname(),exp))
      else:
        invalid_mounts.append(" {0}: {1}".format(srv.hostname(),exp))
    return "{0}\nMOUNTS:\n{1}\nINVALID:\n""".format(host.__str__(me), "\n".join(mounts), "\n".join(invalid_mounts))
  def add(me,exp,mp=False,sz=False,us=False,conffl=False):
    m=re_mount_split.search(exp)
    if m:
      
      srv_name,exp =m.groups()
      try:
        srv=nfs_servers[srv_name]
      except Exception as e:
        srv=nfs_server(srv_name)
        nfs_servers[srv_name]=srv
      me.__mounts.append(nfs_mount(me,srv,exp,mp,sz,us,conffl))
  def mounts(me):
    return me.__mounts

class nfs_export():
  def __init__(me,line):
    me.__path, cli_names=re_export_split.split(line)
    me.__clis=cli_names.split(',')
    me.__clis_using=set()
    for cli in cli_names.split(','):
      if not cli in nfs_clients.keys():
        cli_obj = nfs_client(cli)
        nfs_clients[cli]=cli_obj
  def path(me):
    return me.__path
  def add_using_client(me, cli):
    me.__clis_using.add(cli.ip())
  def clients(me):
    return set(me.__clis)
  def valid_clients(me):
    ret=set()
    for cli_name in me.__clis:
      cli=nfs_clients[cli_name]
      if cli.resolvable():
        if cli.ip() == '':
          print cli.hostname()
        ret.add(cli.ip())
    return ret
  def clients_using_export(me):
    ret=set()
    for cli_name in me.__clis_using:
      cli=nfs_clients[cli_name]
      if cli.resolvable():
        ret.add(cli.ip())
    return ret
  def formatted(me, format=False):
    if not format:
      format = lambda x: x
    return "{0}:\n    CLIENTS: {1}\n    VALID: {2}\n    USERS: {3}".format(me.__path, ','.join(sorted(me.__clis)), ','.join(sorted(format(me.valid_clients()))), ','.join(sorted(format(me.clients_using_export()))))
  def __str__(me):
    return me.formatted(IPs_to_HOSTs)

class nfs_mount():
  def __init__(me,cli,srv,exp,mp,sz,us,conffl):
    me.__srv=srv
    me.__client=cli
    me.__export, me.__subfolder = srv.exp_by_path(exp)
    me.__mp,me.__sz,me.__us,me.__conffl = mp,sz,us,conffl
    if me.__export:
      me.__export.add_using_client(cli)
  def export(me):
    if me.__export:
      return "{0}:{1} ({2}/{3} used)".format(me.__srv.hostname(), me.__export.path(),me.__us,me.__sz)
    else:
      return "{0}:{1} ({2}/{3} used, unmatched)".format(me.__srv.hostname(), me.__subfolder,me.__us,me.__sz)
  def __str__(me):
    return "{0}/{1}".format(me.export(), me.__subfolder)

if __name__ == "__main__":
  from sys import stdin, stderr
  from optparse import OptionParser, OptionGroup
  import signal
  re_hostname = re.compile('[a-zA-Z0-9.]+')

  def signal_handler(signal, frame):
    print('Exit!')
    os._exit(0)
  signal.signal(signal.SIGINT, signal_handler)

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-s", "--nfs_servers", dest="nfs_servers", help="Comma seperated list of NFS servers to report on.", default="")
  parser.add_option("-c", "--nfs_clients", dest="nfs_clients", help="Comma seperated list of clients to report on.", default="")
  parser.add_option("--dump_spov", dest="spov", help="Report a Server Point of View.", action="store_true", default=False) 
  parser.add_option("--dump_cpov", dest="cpov", help="Report a Client Point of View.", action="store_true", default=False)
  parser.add_option("-r", "--report", dest="report", help="Generate a full report (spov, cpov, unused, everyone, shares).", action="store_true", default=False)
  parser.add_option("-f", "--file", dest="inputfile", help="File to read collected client info from. default=stdin", default='')

  parser.add_option("--shares", dest="shares", help="Generate a list of shares used by the clients.", action="store_true", default=False)

  (options, args) = parser.parse_args()

  if options.inputfile == '':
    infile=stdin
  else:
    infile=open(options.inputfile, 'r')

  for l in infile:
    re_uncomment.sub('',l)
    cols=re_split.split(l)
    if len(cols) < 3: continue
    cli_name=mp=exp=sz=us=conffl=False
    try:
      cli_name=cols[0]
      mp=cols[1]
      exp=cols[2]
      sz=cols[3]
      us=cols[4]
      conffl=cols[5]
    except:
      pass
    try:
      cli=nfs_clients[cli_name]
    except:
      cli = nfs_client(cli_name)
    cli.add(exp,mp,sz,us,conffl)

  nfs_srvrs_fltr = set()
  if options.nfs_servers != "":
    for s in options.nfs_servers.lower().split(','):
      h,ip,r=DNSInfo(s)
      nfs_srvrs_fltr.add(h)
  else:
    for s in nfs_servers:
      nfs_srvrs_fltr.add(nfs_servers[s].hostname())

  nfs_clis_fltr = set()
  if options.nfs_clients != "":
    for s in options.nfs_clients.lower().split(','):
      h,ip,r=DNSInfo(s)
      nfs_clis_fltr.add(h)
  else:
    for s in nfs_clients:
      nfs_clis_fltr.add(nfs_clients[s].hostname())

  if options.spov:
    for s in nfs_srvrs_fltr:
      print nfs_servers[s]

  if options.shares:
    print "SHARES NEEDED FOR THIS CLUSTER OF CLIENTS:"
    shares=set()
    for h in nfs_clis_fltr:
      try:
        c=nfs_clients[h]
        for m in c.mounts():
          shares.add(m.export())
      except Exception as e:
        stderr.write("unknown client {1}.\n".format(h,e))
    for s in sorted(shares):
      print "- {0}".format(s)
