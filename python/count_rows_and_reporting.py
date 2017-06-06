#!/usr/bin/env python2
import sys

import re
re_nontext = re.compile('[^a-zA-Z0-9_-]')

try:
    import psycopg2
except:
    print('please install python-psycopg2 module')
    sys.exit(-2)

def print_exception(e):
    try:
        traceback.print_exc()
    except:
        print('Could not handle exception {}'.format(str(e)))

class pg_database():
    def __init__(self, connstr='', debug=False):
        self.connstr=connstr
        self.cn       = None
        self.debug    = debug

    def __del__(self):
        try:
            self.cn.close()
        except AttributeError:
            pass

    def connect(self):
        try:
            if self.cn.closed == 0:
                if self.replication_role() != 'unknown':
                    return True
        except:
            pass
        try:
            self.cn  = psycopg2.connect(self.connstr)
            self.cn.autocommit = True
            return True
        except psycopg2.OperationalError as e:
            if self.debug:
                print_exception(e)
            self.cn  = None
            return False

    def run_sql(self, sql, params=None):
        if self.debug:
            print('Running:\nqry {0}\ncn: {1}'.format(sql, self.connstr))
        try:
            if self.cn.closed != 0:
                raise Exception('Connection closed')
        except:
            self.connect()
        try:
            cur=self.cn.cursor()
            cur.execute(sql, params)
            if not cur.description:
                #no table data was returned...
                return None
            columns = [i[0] for i in cur.description]
            ret = [dict(zip(columns, row)) for row in cur]
            cur.close()
            return ret
        except psycopg2.DatabaseError as e:
            if self.debug:
                print_exception(e)
                print("On query: {0}\nWith params: {1}".format(sql, repr(params)))
            return None
        except AttributeError as e:
            if self.debug:
                print_exception(e)
                print("On query: {0}\nWith params: {1}".format(sql, repr(params)))
            return None
        except psycopg2.InterfaceError as e:
            if self.debug:
                print_exception(e)
                print("On query: {0}\nWith params: {1}".format(sql, repr(params)))
            return None

    def replication_role(self):
        is_in_recovery = self.run_sql('SELECT pg_is_in_recovery() as is_in_recovery')
        if not is_in_recovery:
            return 'unknown'
        elif is_in_recovery[0]['is_in_recovery']:
            return 'standby'
        else:
            return 'master'

    def begin(self):
        self.run_sql('begin')

    def commit(self):
        self.run_sql('commit')

    def rollback(self):
        self.run_sql('rollback')

    def tables(self):
        return self.run_sql("select table_schema, table_name from information_schema.tables where table_schema = 'public'")

    def numrows(self, schema, table):
        if re_nontext.search(schema):
            raise Exception('Schema name "{0}" can only contain text characters (a-zA-Z0-9)'.format(schema))
        if re_nontext.search(table):
            raise Exception('Table name "{0}" can only contain text characters (a-zA-Z0-9)'.format(table))
        ret = self.run_sql('select count(*) as cnt from "{0}"."{1}"'.format(schema, table))
        if ret:
            return ret[0]['cnt']
        else:
            return None

def connstr2dict(connstr):
    ret={}
    for pair in connstr.split(' '):
        if '=' in pair:
            key, val = pair.split('=',1)
            ret[key] = val
    return ret

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description='Check cluster status and log.')
    parser.add_argument('--hostname', default='', help='Hostname or IP for initial connection. This is used to fetch a list of hosts from the repmgr database.')
    parser.add_argument('-p', '--port', default=5432, help='Port for initial connection.')
    parser.add_argument('-c', '--cluster', default='test', help='Name of repmgr cluster (see repmgr.conf).')
    parser.add_argument('-t', '--conntimeout', default=10, help='Timeout for postgres connections.')
    parser.add_argument('-x', '--debug', action='store_true', help='Enable debugging.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Output line for every table.')

    args = parser.parse_args()
    if re_nontext.search(args.cluster):
        print('A repmgr cluster name can only consist of letters and digits.')
        sys.exit(-3)

    connstr='user=postgres dbname=repmgr connect_timeout={0}'.format(args.conntimeout)
    if args.hostname:
        connstr+='host={0} port={1}'.format(args.hostname, args.port)

    try:
        initial_connection = pg_database(connstr, args.debug)
        connections = [ connstr2dict(c['conninfo']) for c in initial_connection.run_sql('select conninfo from repmgr_{0}.repl_nodes'.format(args.cluster)) ]
        databases   = [ d['datname'] for d in initial_connection.run_sql('select datname from pg_database where datallowconn') ]
    except Exception as e:
        print(e)
        print('Could not read cluster information')
        sys.exit(-4)

    numissues = 0

    for d in databases:
        cons = {}
        master = None
        for c in connections:
            try:
                h=c['host']
                c['dbname'] = d
                connstr = ' '.join([ '{0}={1}'.format(k, c[k]) for k in c.keys() ])
                cons[h] = pg_database(connstr, args.debug)
            except:
                print('Error connecting to {0}'.format(h))
                numissues += 1
        for k in cons.keys():
            try:
                cons[k].begin()
            except Exception as e:
                print(e)
                print('Error starting transaction on {0}'.format(k))
                del cons[k]
                numissues += 1
        for k in cons.keys():
            try:
                c = cons[k]
                if c.replication_role() == 'master':
                    master = c
                    break
            except:
                print('Error checking {0} is a master'.format(k))
                unset(cons[k])
                numissues += 1
        if not master:
            print('Whoops. No server is master.')
            sys.exit(-1)
        for t in master.tables():
            sch, tbl = t['table_schema'], t['table_name']
            line = []
            try:
                nummst = master.numrows(sch, tbl)
            except Exception as e:
                print(e)
                print('Error checking number of rows for "{0}"."{1}" on master'.format(sch, tbl))
                numissues += 1
                break
            for k in cons.keys():
                try:
                    c = cons[k]
                    numstdb = c.numrows(sch, tbl)
                    if nummst != numstdb:
                        print('Number of rows for "{0}"."{1}"."{2}" on master ({3}) differ from "{4} ({5})'.format(d, sch, tbl, nummst, k, numstdb))
                        numissues += 1
                    elif args.verbose:
                        print('Number of rows for "{0}"."{1}"."{2}" on master ({3}) equal to "{4} ({5})'.format(d, sch, tbl, nummst, k, numstdb))
                except:
                    print('Error checking number of rows for "{0}"."{1}" on {2}'.format(sch, tbl, k))
                    numissues += 1
    sys.exit(numissues)
