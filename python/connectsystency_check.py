#!/bin/env python
'''
This is a very simple tool to test connectivity and consitency.
The tool expects an Oracle database (SID, User and Password) to connect.
Withoud User/PW, the database will connect to the Instance set by ORACLE_SID with OS authentication.
The tool expects some table in the database where the config (what to monitor) is specified.
The tool expects some other tables in the database to store logging.
The tool can monitor Windows servers (only to connect to RDP port),
Linux servers (uses ssh to place file on homedir and checks consistency),
Oracle databases (connects to database and stores parameter to check consistency),
URLs (connects and downloads content from preset page).
'''
import socket
import re
import cx_Oracle
import paramiko
import datetime
import time
import threading
import urllib
import sys
import os
import gzip

global verbosity
verbosity = {'display':2, 'logfile':(3, os.path.expanduser('~/connectsystency_check'), False),'db':(0, False, '/')}

def logHandler(severity, msg):
  global verbosity
  msg="{0}: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S'), msg)
  if verbosity['display'] >= severity:
    print(msg)
  if verbosity['logfile'][0] >= severity:
    if verbosity['logfile'][2]:
      logfile=verbosity['logfile'][2]
    else:
      try:
        today=datetime.date.today()
        logfilename='{0}_{1}.log.gz'.format(verbosity['logfile'][1],today.strftime('%Y%m%d'))
        logfile=gzip.open(logfilename,'a')
        verbosity['logfile']=(verbosity['logfile'][0],verbosity['logfile'][1],logfile)
      except:
        print("Could not write to logfile")
    try:
      logfile.write(msg+"\n")
    except:
      print("Could not write to logfile")

  if verbosity['db'][0] >= severity and verbosity['db'][1]:
    try:
      cur = verbosity['db'][1]
      cur.execute("select 1 from dual")
    except:
      cur = False
    if not cur:
      try:
        con = cx_Oracle.connect(verbosity['db'][2])
        cur = con.cursor()
        verbosity['db'] = (verbosity['db'][0],cur,verbosity['db'][2])
      except:
        print('Could not connect to logdatabase')
    try:
      cur.execute("insert into logging (severity, message) values (:sev, :msg)",sev = severity, msg = msg)
      cur.connection.commit()
    except:
      print('Could not log to logdatabase')

class MonitorredObject():
  def __init__(self, settings, constr):
    self.configconstr = constr
    configcn=cx_Oracle.connect(constr)
    self.settings, self.con = settings, configcn
    self.cur = configcn.cursor()
    self.connstr = self.settings['CONNECTSTRING']
  def ping(self):
    #Later ook ping inbouwen
    return True
  def check_port(self, port, timeout=1):
    # Create a TCP socket
    s = socket.socket()
    s.settimeout(timeout)
    try:
      s.connect((self.connstr, port))
      return True
    except socket.error, e:
      return False
  def check_state(self):
    try:
      self.cur.execute("select 1 from dual")
    except:
      self.cur = False
    if not self.cur:
      try:
        configcn=cx_Oracle.connect(self.configconstr)
        self.cur = configcn.cursor()
      except:
        logHandler(1,'Connection to config DB died.')
    if self.cur:
      state = self.get_state()
      if state != self.settings['LASTSTATE']:
        logHandler(4, "{0} - State is different ({1} != {2})".format(self.settings['CONNECTSTRING'], self.settings['LASTSTATE'], state))
        self.cur.execute("insert into STATECHANGELOG(OBJECT,PREVSTATE,NEWSTATE,MESSAGE) values (:obj,:prev, :new, :msg)",obj = self.settings['ID'],prev=self.settings['LASTSTATE'],new = state, msg = '')
        self.cur.execute("update objects set LASTSTATE=:state where ID = :id",state = state,id = self.settings['ID'])
        self.settings['LASTSTATE'] = state
      else:
        logHandler(5, "{0} - State is the same ({1})".format(self.settings['CONNECTSTRING'], state))
      now = datetime.datetime.now()
      self.sync_message(now.__str__())
      self.con.commit()
    
  def sync_message(self,message):
    #Dummy, wordt normaal overruled in de definitie van het specifieke object
    self.settings['LASTVAL'] = message
    try:
      self.cur.execute("update objects set LASTVAL=:last where ID = :id",last = message,id = self.settings['ID'])
      self.con.commit()
    except cx_Oracle.OperationalError:
      self.cur=self
    self.settings['LASTVAL'] = message
    pass
  def get_state(self):
    #Dummy, wordt normaal overruled in de definitie van het specifieke object
    return 0

class Linux(MonitorredObject):
  timeout = 3
  def check_message(self):
    ret = False
    try:
      ssh = paramiko.SSHClient()
      t = threading.Timer(self.timeout,ssh.close)
      t.start()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(self.settings['CONNECTSTRING'])
      ftp = ssh.open_sftp()
      rfile = ftp.open('connectsystency.lastval', mode='r', bufsize=-1)
      lastmsgremote = rfile.read()
      rfile.close()
      lastmsglocal = self.settings['LASTVAL']
      if lastmsgremote == lastmsglocal:
        ret = True
      else:
        logHandler(6, '{0} - RemoteMessage ({1}) != LocalMessage ({2})'.format(self.settings['CONNECTSTRING'],lastmsgremote,lastmsglocal))
    except Exception as e:
      logHandler(8, e)
    try:
      ssh.close()
      t.cancel()
    except Exception as e:
      logHandler(8, e)
    return ret
  def sync_message(self, message):
    try:
      ssh = paramiko.SSHClient()
      t = threading.Timer(self.timeout,ssh.close)
      t.start()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(self.settings['CONNECTSTRING'])
      ftp = ssh.open_sftp()
      rfile = ftp.open('connectsystency.lastval', mode='w', bufsize=-1)
      rfile.write(message)
      rfile.close()
      self.settings['LASTVAL'] = message
    except Exception as e:
      logHandler(8, e)
    try:
      self.cur.execute("update objects set LASTVAL=:last where ID = :id",last = message,id = self.settings['ID'])
      self.con.commit()
    except cx_Oracle.OperationalError:
      self.cur=self

    except Exception as e:
      logHandler(8, e)
    try:
       ssh.close()
       t.cancel()
    except Exception as e:
      logHandler(8, e)
  def get_state(self):
    if not self.ping():
      state=1
    elif not self.check_port(22):
      state=2
    elif not self.check_message():
      state=3
    else:
      state=4
    return state

class Windows(MonitorredObject):
  def get_state(self):
    if not self.ping():
      state=1
    elif not self.check_port(3389):
      state=2
    else:
      state=4
    return state
  
class OraDB(MonitorredObject):
  timeout = 3
  def sync_message(self, message):
    logHandler(7, "OraDB->sync_message")
    try:
      oracon = cx_Oracle.connect('{1}/{2}@{0}'.format(self.settings['CONNECTSTRING'],self.settings['USR'],self.settings['PW']))
      t = threading.Timer(self.timeout,oracon.cancel)
      t.start()
      try:
        oracur = oracon.cursor()
        oracur.execute("update lastval set value = :lastval", lastval = message)
        oracon.commit()
        self.settings['LASTVAL'] = message
        self.cur.execute("update objects set LASTVAL=:last where ID = :id",last = message,id = self.settings['ID'])
        self.con.commit()
      except:
        self.con.cancel()
      finally:
        oracur.close()
    except:
      pass
    try:
      oracon.close()
      t.cancel()
    except:
      pass
  def get_state(self):
    logHandler(7, "OraDB->get_state")
    try:
      oracon = cx_Oracle.connect('{1}/{2}@{0}'.format(self.settings['CONNECTSTRING'],self.settings['USR'],self.settings['PW']))
      t = threading.Timer(self.timeout,oracon.cancel)
      t.start()
      try:
        oracur = oracon.cursor()
        oracur.execute("select value from lastval")
        t.cancel()
        r = oracur.fetchone()
        if r[0] == self.settings['LASTVAL']:
          state = 4
        else:
          state = 3
          logHandler(6, '{0} - RemoteMessage ({1}) != LocalMessage ({2})'.format(self.settings['CONNECTSTRING'],lastmsgremote,lastmsglocal))
      except Exception as e:
        logHandler(8, e)
        state = 2
      finally:
        oracur.close()
    except Exception as e:
      logHandler(8, e)
      state = 1
    try:
      oracon.close()
    except Exception as e:
      logHandler(8, e)
      pass
    return state

class URL(MonitorredObject):
  url2dns = re.compile('\/[a-zA-Z0-9.]+\.[a-zA-Z]+\/')
  def __init__(self, settings, constr):
    MonitorredObject.__init__(self, settings, constr)
    self.URL=self.settings['CONNECTSTRING']
    m = self.url2dns.search(self.settings['CONNECTSTRING'])
    if m:
      self.connstr = m.group(0).replace('/','')
    else:
      self.connstr = ''
  def get_state(self):
    if not self.ping():
      state=1
    elif not self.check_port(80):
      state=2
    else:
      try:
        f = urllib.urlopen(self.URL)
        logHandler(9, f.read())
        state=4
      except:
        state=3
    return state

def rows_to_dict_list(cursor):
    columns = [i[0] for i in cursor.description]
    return [dict(zip(columns, row)) for row in cursor]

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  import signal
  import datetime
  import glob

  def signal_handler(signal, frame):
    logHandler(1, 'Exit!')
    logfile=verbosity['logfile'][2]
    logfile.close()
    os._exit(0)

  signal.signal(signal.SIGINT, signal_handler)

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-c", "--configdb", dest="configdb", help="The SID of the Oracle database to use for config, logging and local check results.", default='')
  parser.add_option("-u", "--user", dest="dbuser", help="The user to connect to DB. Without user the Instance definied by ORACLE_SID is connected with OS Authentication (like sqlplus /).", default='')
  parser.add_option("-p", "--password", dest="dbpassword", default='', help="Password to connect to the database.")
  parser.add_option("-i", "--interval", dest="interval", type="int", default=10, help="Interval between the polls.")
  parser.add_option("-l", "--logfile", dest="logfile", default="~/connectsystency_check", help="Write to logfile.")
  parser.add_option("-v", "--verbosity", dest="verbosity", type="int", default=4, help="Set verbosity level (0-9) for stdout.")
  parser.add_option("--logfile_verbosity", dest="logfile_verbosity", type="int", default=7, help="Verbosity level for logfile (0-9).")
  parser.add_option("--db_verbosity", dest="db_verbosity", type="int", default=8, help="Verbosity level for db logging (0-9).")
  parser.add_option("-d", "--display", dest="display", action="store_true", default=False, help="Show the log entries with severity 1 (restart/configDB error) and 6 (local message != remote message).")
  parser.add_option("--display_days", dest="display_days", type="int", default=365, help="Number of days to display. 0: Only today, 1 also yesterday, etc. Default = 365.")
  parser.add_option("-k", "--keep", dest="keep", type="int", default=365, help="Number of days of logging to keep in DB and in logfiles. Default = 365.")
  parser.add_option("-f", "--follow", dest="follow", action="store_true", default=False, help="Keep track of the objects status.")

  (options, args) = parser.parse_args()

  verbosity['display'] = options.verbosity
  verbosity['logfile'] = (options.logfile_verbosity, os.path.expanduser(options.logfile), False)

  if options.dbuser == '':
    constr = '/'
  else:
    constr = '{0}/{1}@{2}'.format(options.dbuser, options.dbpassword, options.configdb)

  if options.display:
    configcn = cx_Oracle.connect(constr)
    cur = configcn.cursor()
    cur.execute('select severity, message from LOGGING where SEVERITY in (1,6) and trunc(sysdate) - trunc(occurred) <= :days order by 2,1', {'days':options.display_days})
    print("-"*138)
    print("|{0:^8}| {1:^125} |".format('severity','Message'))
    print("-"*138)
    for r in cur:
      print('| {0:^6} | {1:125} |'.format(r[0],str(r[1])[0:125]))
    print("-"*138)
    exit(0)
  elif options.follow:
    cur = False

    while True:
      if not cur:
        try:
          configcn = cx_Oracle.connect(constr)
          cur = configcn.cursor()
        except:
          print("Database not available. Trying again in {0} seconds.".format(options.interval))

      try:
        cur.execute("select name, laststate, lastval from objects order by 1")
        os.system('clear')
        print("-"*70)
        print("| {0:^25} | {1:^5} | {2:^30} |".format('Name','State', 'Last message'))
        print("-"*70)
        for r in cur:
          print('| {0:<25} | {1:^5} | {2:<30} |'.format(r[0],r[1],r[2]))
        print("-"*70)
        time.sleep(options.interval)
      except:
        cur = False

  logHandler(1, "Started.")

  while True:
    try:
      configcn = cx_Oracle.connect(constr)
      cur = configcn.cursor()
      verbosity['db'] = (options.db_verbosity, cur, constr)
      cur.execute('select * from objects')
      rows = rows_to_dict_list(cur)
      objs = []
      for r in rows:
        if r['TYPE'] == 'D':
          obj = OraDB(r, constr)
        elif r['TYPE'] == 'L':
          obj = Linux(r, constr)
        elif r['TYPE'] == 'W':
          obj = Windows(r, constr)
        elif r['TYPE'] == 'U':
          obj = URL(r, constr)
        objs.append(obj)
      break
    except:
      logHandler(1, "Database not available. Trying again in {0} seconds.".format(options.interval))
      time.sleep(options.interval)

  now = time.time()
  today = datetime.date.today()-datetime.timedelta(1)
  while True:
    if today != datetime.date.today():
      dbclean = logfileclean = True
      logfile=verbosity['logfile'][2]
      logfile.close()
      verbosity['logfile']= (verbosity['logfile'][0], verbosity['logfile'][1], False)
      today = datetime.date.today()

    if dbclean:
      try:
        logHandler(2, "Cleaning logtable from database.")
        configcn = cx_Oracle.connect(constr)
        cur = configcn.cursor()
        cur2 = configcn.cursor()
        verbosity['db'] = (options.db_verbosity, cur, constr)
        cur.execute("select distinct to_char(occurred,'yyyy-mm-dd') occ from logging where trunc(sysdate) - trunc(occurred) > :keep order by 1 desc", {'keep':options.keep})
        for r in cur:
          logHandler(2, "Cleaning day {0} from database.".format(r[0]))
          cur2.execute("delete from logging where to_char(occurred,'yyyy-mm-dd') = :dt",{'dt':r[0]})
        dbclean=False
      except:
        logHandler(1, "Error occurred during cleaning log in config database. Trying again after next round.".format(options.interval))

    if logfileclean:
      logHandler(2, "Cleaning logfiles.")
      keepdate= datetime.datetime.today()-datetime.timedelta(days=options.keep)
      for f in glob.iglob(verbosity['logfile'][1]+'_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].log.gz'):
        try:
          logfiledate=datetime.datetime.strptime(f[-15:-7],'%Y%m%d')
          if logfiledate < keepdate:
            os.remove(f)
            logHandler(2, "Logfile {0} succesfully removed.".format(f))
        except:
          logHandler(2,'Could not remove file {0}. Will try again tomorow.'.format(f))
      logfileclean = False

    logHandler(3, "Checking")
    for o in objs:
      try:
        o.check_state()
      except Exception as e:
        logHandler(8, e)
    while now < time.time():
      now += options.interval
    time.sleep(now-time.time())
