#!/usr/bin/python

if __name__ == "__main__":
  from optparse import OptionParser, OptionGroup
  import cx_Oracle
  import os

  parser = OptionParser(usage='Usage: %prog [options] [folders]')
  parser.add_option("-u", "--user", dest="user", help="The user to connect to the database instances. default: sys", default='sys')
  parser.add_option("-p", "--password", dest="password", help="The password to the database instances.", default='')
  parser.add_option("-t", "--to", dest="switch_to", default='', help="The database to switch to.")
  parser.add_option("-f", "--from", dest="switch_from", default='', help="the database to switch from.")
#  parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Show all sql that is run (and on which instance).")
  parser.description = '''Use this script to switch to another dataguard instance without using the broker. Please note that SBB_SwitchOver.sh (using the broker) should be used during normal operation. you can use this script only under the following circumstances:
- Broker is out of sync
- upgrade to new patch set or major version

Please specify either --to or --from (or both, but --from would be obsolete).
- Only --from: whatever you do, this should not be primary after operation...
- Only --to: whatever you do, this should be primary after operation...'''
  (options, args) = parser.parse_args()
  SECONDARIES = {}

  if options.password != '':
    PASSWORD=options.password
  else:
    ENVVAR='{0}_PW'.format(options.user.upper())
    try:
      PASSWORD=os.environ[ENVVAR]
    except:
      print "Cannot read environment variable '{0}'. Please set environment variable or use --password.".format(ENVVAR)
      exit(1)

  if options.switch_to == '' and options.switch_from == '':
    try:
      SID=os.environ['ORACLE_SID']
    except:
      print 'You should specify either --switch_to or --switch_from, or set ORACLE_SID (or a combination)'
      exit(1)
    try:
      con = cx_Oracle.connect('{0}/{1}'.format(options.user, PASSWORD), mode=cx_Oracle.SYSDBA)
    except:
      print 'Could not connect to database {0}/{1}@{2}'.format(options.user, PASSWORD, SID)
      exit(1)
  elif options.switch_to.upper() == options.switch_from.upper():
    raise Exception('--switch_to and --switch_from cannot be the same SID')
    exit(1)
  elif options.switch_from != '':
    con = cx_Oracle.connect('{0}/{1}@{2}'.format(options.user, PASSWORD, options.switch_from), mode=cx_Oracle.SYSDBA)
  else:
    con = cx_Oracle.connect('{0}/{1}@{2}'.format(options.user, PASSWORD, options.switch_to), mode=cx_Oracle.SYSDBA)

  cur = con.cursor()
  cur.execute('select DB_UNIQUE_NAME from v$dataguard_config')
  for SID in cur:
    con2 = cx_Oracle.connect('{0}/{1}@{2}'.format(options.user, PASSWORD, SID[0]), mode=cx_Oracle.SYSDBA)
    cur2 = con2.cursor()
    cur2.execute('select db_unique_name, database_role from v$database')
    row = cur2.fetchone()
    if row[1] == 'PRIMARY':
      PRIMARY = row[0],cur2
    else:
      SECONDARIES[row[0].upper()] = cur2
  cur.close()
  con.close() 

  print 'Primary database: {0}'.format(PRIMARY[0])
  for SID in SECONDARIES:
    print 'Standby database: {0}'.format(SID)

  if PRIMARY[0].upper() == options.switch_to.upper():
    print "Database {0} is already primary".format(options.switch_to)
    exit(0)
  else:
    from_sid, from_cur = PRIMARY
    if options.switch_to == '':
      to_sid = SECONDARIES.keys()[0]
      to_cur = SECONDARIES[to_sid]
    elif SECONDARIES.has_key(options.switch_to.upper()):
      to_sid = options.switch_to.upper()
      to_cur = SECONDARIES[to_sid]
    else:
      print "New standby database {0} is unknown in this dataguard configuration.".format(options.switch_to)
      exit(1)

  print "Switchover to {0}".format(to_sid)

  print 'Checking if Recovery is ON at New Primary'
  to_cur.execute("SELECT count(*) FROM v$process WHERE PNAME like 'MRP%'")
  r, = to_cur.fetchone()
  if r > 0:
    print 'Recovery is on'
  else:
    print "Recovery was off. Switching on recovery."
    to_cur.execute("ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT")
    to_cur.execute("select VALUE from  V$DATAGUARD_STATS where NAME='apply finish time'")
    v, = to_cur.fetchone()
    if v != None:
      print "Recovery will take about {0} ('+D H:M:S.mS'). Wait for recover to finish and try again...".format(v)
      exit(1)

  print 'Checking Switch Over status on Old Primary'
  from_cur.execute('SELECT SWITCHOVER_STATUS FROM V$DATABASE')
  r, = from_cur.fetchone()
  if r in ('TO STANDBY','SESSIONS ACTIVE'):
    print 'Old Primary switchover status OK'
  else:
    print "Old Primary switchover status NOT OK ('{0}', should be 'TO STANDBY' or 'SESSIONS ACTIVE')".format(r)
    exit(1)

  print 'Switch over Old Primary to Standby'
  from_cur.execute('ALTER DATABASE COMMIT TO SWITCHOVER TO PHYSICAL STANDBY WITH SESSION SHUTDOWN')

  print 'Checking status of Old Primary after switch to Standby'
  from_cur.execute('SELECT DATABASE_ROLE FROM V$DATABASE')
  r, = from_cur.fetchone()
  if r == 'PHYSICAL STANDBY':
    print 'Old Primary is now Standby'
  else:
    print "Old Primary is not Standby (Role is '{0}' and should be 'PHYSICAL STANDBY')".format(r)
    exit(1)

  print 'Promoting new Primary'
  to_cur.execute('ALTER DATABASE COMMIT TO SWITCHOVER TO PRIMARY')
  to_cur.execute('ALTER DATABASE OPEN')
  to_cur.execute('SELECT DATABASE_ROLE FROM V$DATABASE')
  r, = to_cur.fetchone()
  if r == 'PRIMARY':
    print 'New Primary is now PRIMARY'
  else:
    print "New Primary is not Primary (Role is '{0}' and should be 'PRIMARY')".format(r)
    exit(1)

  print 'Restarting old Primary'
  from_con = from_cur.connection
  from_cur.close()
  dsn = '{0}/{1}@{2}'.format(from_con.username, from_con.password, from_con.dsn)
  try:
    from_con.shutdown(cx_Oracle.DBSHUTDOWN_IMMEDIATE)
  except cx_Oracle.DatabaseError as e:
    msg=str(e)
    if msg[0:9] != 'ORA-01092':
      print e
      exit(1)
  from_con = cx_Oracle.connect(dsn, mode=cx_Oracle.SYSDBA | cx_Oracle.PRELIM_AUTH)
  from_cur = from_con.cursor()

  from_con.startup()
  from_con = cx_Oracle.connect(dsn, mode=cx_Oracle.SYSDBA)
  from_cur = from_con.cursor()
  from_cur.execute('ALTER DATABASE MOUNT')
  from_cur.execute("ALTER DATABASE RECOVER MANAGED STANDBY DATABASE USING CURRENT LOGFILE DISCONNECT")

  from_cur.execute('SELECT DATABASE_ROLE FROM V$DATABASE')
  r, = from_cur.fetchone()
  if r == 'PHYSICAL STANDBY':
    print "Old Primary is now 'PHYSICAL STANDBY'"
  else:
    print "Old Primary role is '{0}' and should be 'PHYSICAL STANDBY'.".format(r)

  print "Switchover completed succesfully..."
