#!/usr/bin/python
# copied from postgresql_db and modified for running oracle quries
# -*- coding: utf-8 -*-

# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: oracle_sql
short_description: Run queries on an oracle database.
description:
   - Run queries on an oracle database. Please use other oracle modules if they fit
   - (for instance, they qill be idempotent and this might not be).
version_added: "2.1"
options:
  query:
    description:
      - query to run
    required: true
    default: null
  creates:
    description:
      - query that returns records if the step should not be run
    required: false
    default: null
  removes:
    description:
      - query that returns records if the step should be run
    required: false
    default: null
  user:
    description:
      - The username used to authenticate with
    required: false
    default: null
  password:
    description:
      - The password used to authenticate with
    required: false
    default: null
  host:
    description:
      - Host running the database
    required: false
    default: localhost
  databases:
    description:
       - regexp describing database service names in oratab to connect to
    required: yes
    default: '.*'
  port:
    description:
      - Listener port to connect to.
    required: false
    default: 1521
  sysdba:
    description:
    - connect as sysdba
    required: false
    default: false
  maxresults:
    description:
    - maximum numer of rown returned
    required: false
    default: 100
notes:
   - The default authentication assumes that you are either logging in as or sudo'ing to the C(oracle) account on the host.
   - This module uses I(cx_Oracle), a Python Oracle database adapter. You must ensure that cx_Oracle is installed on
     the host before using this module. If the remote host is the Oracle database server (which is the default case), 
     then Oracle must also be installed on the remote host.
requirements: [ cx_Oracle ]
author: Sebastiaan Mannem
'''

EXAMPLES = '''
# return all owner and names from all objects in all databases
- oracle_sql: databases='D.*" query="select owner, object_name from all_objects"

# create a tale named blaat with one column id (int) in schema of user oracle with password 'secret' in database ORADB
- oracle_sql: query='create table blaat (id int)'
                 user=oracle
                 password=secret
                 database=ORADB
'''

def oratab():
    with open('/etc/oratab') as f:
        for l in f:
            try:
                l=l.strip()
                l=l.split('#')[0]
                sid, home, start = l.split(':')[:3]
                yield {'sid': sid, 'home': home, 'autostart': start}
            except:
                pass


def rows_to_dict_list(cursor, numrows=100):
    try:
        columns = [i[0] for i in cursor.description]
        ret = []
        i=0
        for row in cursor:
            i+=1
            if i > numrows: 
                break
            row=[ str(c) for c in row ]
            ret.append(dict(zip(columns, row)))
        return ret
    except:
        return []

def str2bool(v):
    if isinstance(v, (bool)):
        return v
    elif v.lower() in ("yes", "true", "t", "1"):
        return True
    else:
        return False

# ===========================================
# Module execution.
#

def main():
    module = AnsibleModule(
        argument_spec=dict(
            query=dict(default=""),
            creates=dict(default=""),
            removes=dict(default=""),
            user=dict(default=""),
            password=dict(default=""),
            host=dict(default="localhost"),
            databases=dict(default=".*"),
            port=dict(default="1521"),
            sysdba=dict(default="False"),
            maxresults=dict(default="100")
        ),
        supports_check_mode = True
    )

    query = module.params["query"]
    creates = module.params["creates"]
    removes = module.params["removes"]
    db = module.params["databases"]
    host = module.params["host"]
    port = module.params["port"]
    user = module.params["user"]
    password = module.params["password"]
    sysdba = str2bool(module.params["sysdba"])
    maxresults = int(module.params["maxresults"])
    changed = False

    try:
        import cx_Oracle
    except ImportError, e:
        module.fail_json(msg="unable to load cx_Oracle: {0}. Please set LD_LIBRARY_PATH ({1}) correct and install cx_Oracle package.".format(e, os.environ['LD_LIBRARY_PATH']))

    if sysdba:
        mode=cx_Oracle.SYSDBA
    else:
        mode=0

    failed_dbs = []
    conns={}
    # If no user is specified, we can only connect using OS authntication and that only works on localhost
    if module.params["user"] == "":
        if host == "" or host == "localhost":
            # for local we can use oratab and scan using regexp
            db_re = re.compile(db)
            try:
                dbs = dict([ (l['sid'], l) for l in oratab() if db_re.search(l['sid']) ])
            except Exception, e:
                module.fail_json(msg="unable to read oratab: %s" % e)

            for sid in dbs.keys():
                os.environ['ORACLE_SID']=sid
                os.environ['ORACLE_HOME']=dbs[sid]['home']

                try:
                    conns[sid] = cx_Oracle.connect('/', mode=mode)
                except:
                    failed_dbs.append((sid, "could not connect to database {0} using os authentication".format(sid)))
        else:
            module.fail_json(msg="please specify a user/pw, or try os authentication on localhost")
    else:
        connstr = '{0}/{1}@{2}:{3}/{4}'.format(user, password, host, port, db)
        try:
            conns[db] = cx_Oracle.connect(connstr, mode=mode)
        except Exception, e:
            module.fail_json(msg="could not connect to '{0}' (mode={1}): {2}".format(connstr, mode, e))

    rowdata={}
    skipped_dbs=[]
    changed_dbs=[]
    for sid in conns.keys():
        conn=conns[sid]
        cur=conn.cursor()
        try:
            if removes:
                cur.execute(removes)
                if not cur.fetchone():
                    skipped_dbs.append(sid)
                    continue
            if creates != '':
                cur.execute(creates)
                if cur.fetchone():
                    skipped_dbs.append(sid)
                    continue
            if module.check_mode:
                changed_dbs.append(sid)
                continue
            cur.execute(query)
            rowdata[sid] = rows_to_dict_list(cur, maxresults)
            changed_dbs.append(sid)
        except Exception, e:
           failed_dbs.append((sid, "query {0} failed with error: {1}".format(query, e)))
        

    ret = {}
    ret['query'] = query
    ret['creates'] = creates
    ret['removes'] = removes
    ret['rowdata'] = rowdata
    if len(skipped_dbs) > 0:
        ret['skipped_dbs'] = skipped_dbs
    if len(changed_dbs) > 0:
        ret['changed_dbs'] = changed_dbs
    else:
        ret['changed'] = False
    if len(failed_dbs) > 0:
        ret['failed_dbs'] = failed_dbs
    ret['rc'] = len(failed_dbs)
    module.exit_json( **ret )

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.database import *
if __name__ == '__main__':
    main()
