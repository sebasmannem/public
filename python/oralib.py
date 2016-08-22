#!/bin/env python2
import re
import subprocess
import cx_Oracle
import SQLNetConfig
import os
comment_re=re.compile('#.*')

def oratab(file='/etc/oratab'):
  ret={}
  with open('/etc/oratab','r') as f:
    for l in f:
      l=comment_re.sub('',l[:-1])
      try:
        SID,HOME,Autostart = l.split(':')
      except:
        continue
      ret[SID.upper()] = {'HOME': HOME, 'Autostart': Autostart}
  return ret

def runningDBs():
  ret=[]
  ps_re=re.compile('^(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)')
  p=subprocess.Popen(['ps','-ef'],stdout=subprocess.PIPE)
  for l in p.stdout:
    try:
      uid, pid, parent, util, startdate, tty, starttime, cmd = ps_re.search(l).groups()[0:8]
      if uid == 'oracle' and cmd[0:9] == 'ora_pmon_':
        ret.append(cmd[9:])
    except:
      pass
  return ret

def rows_to_dict_list(cursor):
    columns = [i[0] for i in cursor.description]
    return [dict(zip(columns, row)) for row in cursor]

class connection(object):
  def __init__(self, settings):
    self.settings=settings
    self.__conn = None
    self.SID = None
    SID=''
    if 'SID' in settings:
      if settings['SID'] != '':
        SID='@'+settings['SID']
    try:
      self.connstring='{1}/{2}{0}'.format(SID,settings['USR'],settings['PW'])
    except KeyError:
      self.connstring='/'
      if SID != '':
        self.SID=settings['SID']

  def runSQL(self, qry):
    try:
      oracur = self.__conn.cursor()
    except:
      self.open()
      oracur = self.__conn.cursor()

    if 'TIMEOUT' in self.settings:
      t = threading.Timer(self.settings['TIMEOUT'], oracon.cancel)
      t.start()

    oracur.execute(qry)
    self.__conn.commit()

    return rows_to_dict_list(oracur)

  def close(self):
    try:
      conn, self.__conn = self.__conn, None
      conn.close()
      t.cancel()
    except:
      pass

  def open(self):
    if self.SID:
      ORGSID=os.environ['ORACLE_SID']
      os.environ['ORACLE_SID']=self.SID

    self.__conn = cx_Oracle.connect(self.connstring)

    if self.SID:
      os.environ['ORACLE_SID']=ORGSID

class connections(dict):
  def __init__(self, settings, SIDs):

