#!/usr/bin/python
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
module: pg_hba
short_description: Adds, removes or modifies an rule in a pg_hba file.
description:
   - The fundamental function of the module is to create, or delete lines in pg_hba files.
   - The lines in the file should be in a typical pg_hba form and lines should be unique per key (type, databases, users, source).
     If they are not unique and the SID is 'the one to change', only one (for present) or no (for absent) of the SID's will remain.
version_added: "2.2"
options:
  dest:
    description:
      - path to pg_hba file to modify.
    required: true
    default: ''
  backup:
    description:
      - If set, create a backup of the pg_hba before it is modified.
        The location of the backup is returned in the C(backup) variable by this module.
    required: false
    default: false
  create:
    description:
      - create an pg_hba file if none should exists.
      - When set to false, an error is raised when pg_hba file doesn't exist.
    required: false
    default: false
  owner:
    description:
      - owner of the pg_hba file (almost always postgres, or sometimes enterprisedv).
    required: false
    default: postgres
  group:
    description:
      - group owner of the pg_hba file (almost always oinstall).
    required: false
    default: postgres
  mode:
    description:
      - file mode a newly created file should have
    required: false
    default: 640
  contype:
    description:
      - type of the rule. Use emptystring if you don't want to change file, but only want to read contents.
    required: true
    default: "host"
    choises: [ "local", "host", "hostssl", "hostnossl", "" ]
  databases:
    description:
      - databases this line applies to
    required: false
    default: "all"
  users:
    description:
      - users this line applies to
    required: false
    default: "all"
  source:
    description:
      - The source address/net where the connections could come from
      - Will not be used for entries of type=local
      - You can also use keywords 'all', 'samehost', and 'samenet'
    required: false
    default: "samehost"
  netmask:
    description:
      - The netmask of the source address.
    required: false
    default: ""
  method:
    description:
      - authentication method to be used.
    required: false
    default: "md5"
    choices: [ "trust", "reject", "md5", "password", "gss", "sspi", "krb5", "ident", "peer", "ldap", "radius", "cert", "pam" ]
  options:
    description:
      - Additional options for the auth-method
    required: false
    default: ""
  order:
    description:
      - The entries will be written out in a specific order.
      - With this option you can control by wich field they are ordered first, second and last.
      - s=source, d=databases, u=users
    required: false
    default: "sdu"
    choices: [ "sdu", "sud", "dsu", "dus", "usd", "uds" ]
  state:
    description:
      - The line(s) will be added/modified when state=present and removed when state=absent
    required: false
    default: present
    choices: [ "present", "absent" ]
notes:
   - The default authentication assumes that on the host, you are either logging in as or
     sudo'ing to an account with appropriate permissions to read and modify the file.
   - This module also returns the pg_hba info. You can find it in pg_hba, in format: (type='',databases='',users='', source='',method='',options='')
author: Sebastiaan Mannem
   - This module will sort
'''

EXAMPLES = '''
# Grant user blaat from host 1.2.3.4/32 access to database bladie using md5 password authentication.
- pg_hba: user=blaat source=1.2.3.4 database=bladie method=md5
'''

import os
import pwd
import grp
import stat
import re

class TouchError(Exception):
    pass

def touch(path, owner, group, mode):
    try:
        fstat = os.stat(path)
        return
    except:
        pass
    try:
        f=open(path, 'w')
        f.close()
        fstat = os.stat(path)
    except:
        raise TouchError('Could not create file {0}. Please become a user with sufficient permissions.'.format(path))
    try:
        usr = pwd.getpwnam(owner)
    except:
        raise TouchError('User {0} is unknown on this system. Please specify a valid owner for the file.'.format(owner))
    try:
        group = grp.getgrnam(group)
    except:
        raise TouchError('Group {0} is unknown on this system. Please specify a valid owner for the file.'.format(group))
    try:
        mode=int(str(mode),8)
    except:
        raise TouchError("Could not convert '{0}' form octal to int. Please specify a valid mode in octal form (e.a. 777, 640, etc.).".format(mode))
    if mode > 511 or mode < 0:
        raise TouchError("Please specify octal mode between 000 and 777.".format(mode))
    try:
        if stat.S_IMODE(fstat.st_mode) != mode:
            os.chmod(path, mode)
        if fstat.st_uid != usr.pw_uid or fstat.st_gid != group.gr_gid:
            os.chown(path, usr.pw_uid, group.gr_gid)
    except:
        raise TouchError("Could not set owner, group or permissions on file. Please become a user with sufficient permissions.".format(mode))

class IPError(Exception):
    pass

def ipv4_to_int(ip):
    if type(ip) is int:
        return ip
    elif type(ip) is str:
        ip_ar = ip.split(".")
        if len(ip_ar) != 4:
            raise IPError("Invalid IP: {0}. We need 4 numbers in an IP".format(ip))
        ip=0
        for i in ip_ar:
            try:
                i=int(i)
            except:
                raise IPError("IP part {0} must be numeric".format(i))
            if i<0 or i>255:
                raise IPError("IP part {0} must be from 0-255".format(i))
            ip=ip*256+i
        return ip
    else:
        raise IPError("{0} has an invalid type for an IP.".format(ip.__repr__()))

def int_to_ipv4(i):
    try:
        i = int(i)
    except:
        raise IPError("{0} is not an integer.".format(i.__repr__()))
    ip = []
    for x in range(4):
        ip.append(str(int(i/2**(8*(3-x)) % 256)))
    return '.'.join(ip)

def prefix_to_ipv4netmask(base):
    if type(base) is str:
        base=base.replace('/','')
    try:
        base=int(base)
    except:
        raise IPError("invalid numeric expression for ipv4 network base {}".format(base))
    return int_to_ipv4((2**base-1) * 2** (32-base))

def ipv6_to_int(ip):
    normalized = ip
    if '.' in normalized:
        #Normalize: Replace ipv4 part for ipv6 equivalent
        m = ipv4part_re.search(normalized)
        ipv6part = ''.join('%02x'%int(i) for i in m.group(0).split('.'))
        ipv6part = ipv6part[:4] + ':' + ipv6part[4:]
        normalized = normalized.replace(m.group(0), ipv6part)
    if '::' in ip:
        #Normalize: Replace :: for correct number of 0000 parts
        missing = 9 - normalized.count(':')
        normalized = normalized.replace('::', ":".join(['']+['0000']*missing+['']))
        normalized.strip(':')
        normalized = normalized.replace('::',':')
    parts = normalized.split(':')
    if len(parts) < 8:
        raise IPError('IPv6 seems to consist of too less parts')
    elif len(parts) > 8:
        raise IPError('IPv6 seems to consist of too much parts')
    #Normalize: Every part should have 4 digits
    for i in range(parts):
        if len(parts[i]) != 4:
            part = '0000' + parts[i]
            parts[i] = part[-4:]
    return int(parts.replace(':',''),16)

def int_to_ipv6(i):
    try:
        rest = int(i)
    except:
        raise IPError("{0} is not an integer.".format(i.__repr__()))

    # Split into hex parts
    ipv6 = []
    for i in range(8):
        part = rest % 16**4
        rest = rest / 16**4
        ipv6.append(str(part))

    #join with ':' as seperator
    ipv6 = ':'.join(ipv6[::-1])

    #Find largest repetion of zero fields and replace by '::'
    obsoletes = [ m.group(0) for m in ipv6_obs_re.finditer(ipv6) ]
    if len(obsoletes) > 0:
        obsoletes = sorted(obsoletes, key=len)
        largest_obsolete = obsoletes[-1]
        ipv6 = ipv6.replace(obsoletes, '::', 1)

    #Strip leading zeros per field
    parts = ipv6.split(':')
    for i in range(len(parts)):
        part = parts[i]
        if len(part) == 0:
            continue
        part = part.lstrip('0')
        if len(part) == 0:
            part = '0'
        parts[i] = part
    return ':'.join(parts)

def prefix_to_ipv6netmask(base):
    if type(base) is str:
        base=base.replace('/','')
    try:
        base=int(base)
    except:
        raise IPError("invalid numeric expression for ipv6 network base {}".format(base))
    return int_to_ipv6((2**base-1) * 2** (128-base))


PgHbaMethods = [ "trust", "reject", "md5", "password", "gss", "sspi", "krb5", "ident", "peer", "ldap", "radius", "cert", "pam" ]
PgHbaTypes = [ "local", "host", "hostssl", "hostnossl" ]
PgHbaOrders = [ "sdu", "sud", "dsu", "dus", "usd", "uds"]
PgHbaHDR = [ 'type', 'db', 'usr', 'src', 'mask', 'method', 'options']

split_re = re.compile('\s+')


# See http://stackoverflow.com/questions/53497/regular-expression-that-matches-valid-ipv6-addresses for more info...
IPV4SEG   = '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])'

IPV4ADDR  = '('+IPV4SEG+'\.){3,3}'+IPV4SEG

IPV6SEG   = '[0-9a-fA-F]{1,4}'

IPV6ADDR  = '(('+IPV6SEG+':){7,7}'+IPV6SEG+'|'           # 1:2:3:4:5:6:7:8
IPV6ADDR += '('+IPV6SEG+':){1,7}:|'                      # 1::
IPV6ADDR += '('+IPV6SEG+':){1,6}:'+IPV6SEG+'|'           # 1::8               1:2:3:4:5:6::8   1:2:3:4:5:6::8
IPV6ADDR += '('+IPV6SEG+':){1,5}(:'+IPV6SEG+'){1,2}|'    # 1::7:8             1:2:3:4:5::7:8   1:2:3:4:5::8
IPV6ADDR += '('+IPV6SEG+':){1,4}(:'+IPV6SEG+'){1,3}|'    # 1::6:7:8           1:2:3:4::6:7:8   1:2:3:4::8
IPV6ADDR += '('+IPV6SEG+':){1,3}(:'+IPV6SEG+'){1,4}|'    # 1::5:6:7:8         1:2:3::5:6:7:8   1:2:3::8
IPV6ADDR += '('+IPV6SEG+':){1,2}(:'+IPV6SEG+'){1,5}|'    # 1::4:5:6:7:8       1:2::4:5:6:7:8   1:2::8
IPV6ADDR += IPV6SEG+':((:'+IPV6SEG+'){1,6})|'            # 1::3:4:5:6:7:8     1::3:4:5:6:7:8   1::8
IPV6ADDR += ':((:'+IPV6SEG+'){1,7}|:)|'                  # ::2:3:4:5:6:7:8    ::2:3:4:5:6:7:8  ::8       ::       
IPV6ADDR += 'fe80:(:'+IPV6SEG+'){0,4}%[0-9a-zA-Z]{1,}|'  # fe80::7:8%eth0     fe80::7:8%1  (link-local IPv6 addresses with zone index)
IPV6ADDR += '::(ffff(:0{1,4}){0,1}:){0,1}'+IPV4ADDR+'|'  # ::255.255.255.255  ::ffff:255.255.255.255  ::ffff:0:255.255.255.255 (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
IPV6ADDR += '('+IPV6SEG+':){1,4}:'+IPV4ADDR+')'          # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33 (IPv4-Embedded IPv6 Address)

ipv4_re     = re.compile('^\s*'+IPV4ADDR+'(/\d{1,2})?\s*$')
ipv4part_re = re.compile(IPV4ADDR)
ipv6_re     = re.compile('^\s*'+IPV6ADDR+'(/\d{1,3})?\s*$')
ipv6_obs_re = re.compile('(\s|:)(0000:)+')

class PgHbaError(Exception):
    pass

class PgHba(object):
    """
        PgHba object to read/write entries to/from.

        pg_hba_file - the pg_hba file almost always /etc/pg_hba
        Note: I copied this from crontab module to the oratab module and then forward to the PgHba module and modified as needed...
    """
    def __init__(self, pg_hba_file=None, order="sdu"):
        if order not in PgHbaOrders:
            raise PgHbaError("invalid order setting {0} (should be one of '{1}').".format(order, "', '".join(PgHbaOrders)))
        self.pg_hba_file = pg_hba_file
        self.rules      = None
        self.comment    = None
        self.changed    = True
        self.order      = order

        #self.databases will be update by add_rule and gives some idea of the number of databases (at least that are handled by this pg_hba)
        self.databases  = set(['postgres', 'template0','template1'])

        #self.databases will be update by add_rule and gives some idea of the number of users (at least that are handled by this pg_hba)
        #since this migth also be groups with multiple users, this migth be totally off, but at least it is some info...
        self.users      = set(['postgres'])

        # select whether we dump additional debug info through syslog
        self.syslogging = False

        self.read()

    def read(self):
        # Read in the pg_hba from the system
        self.rules = {}
        self.comment = []
        # read the pg_hbafile
        try:
            f = open(self.pg_hba_file, 'r')
            for l in f:
                l=l.strip()
                #uncomment
                if '#' in l:
                    l, comment = l.split('#', 1)
                    self.comment.append('#'+comment)
                rule = self.line_to_rule(l)
                if rule:
                    self.add_rule(rule)
            f.close()
            self.changed = False
        except IOError, e:
            raise PgHbaError("pg_hba file '{0}' doesn't exist. Use create option to autocreate.".format(self.pg_hba_file))

    def line_to_rule(self, line):
        #split into sid, home, enabled
        if split_re.sub('', line) == '':
            #empty line. skip this one...
            return None
        cols = split_re.split(line)
        if len(cols) < 4:
            raise PgHbaError("File {0} has a rule with too few columns: {1}.".format(self.pg_hba_file, line))
        if cols[0] not in PgHbaTypes:
            raise PgHbaError("File {0} contains an rule of unknown type: {1}.".format(self.pg_hba_file, line))
        if cols[0] == 'local':
            if cols[3] not in PgHbaMethods:
                raise PgHbaError("File {0} contains an rule of 'local' type where 4th column '{1}'isnt a valid auth-method.".format(self.pg_hba_file, cols[3]))
            cols.insert(3, None)
            cols.insert(3, None)
        else:
            if len(cols) < 6:
                cols.insert(4, None)
            elif cols[5] not in PgHbaMethods:
                cols.insert(4, None)
            if len(cols) < 7:
                cols.insert(7, None)
            if cols[5] not in PgHbaMethods:
                raise PgHbaError("File {0} contains an rule '{1}' that has no valid method.".format(self.pg_hba_file, line))
        rule = dict(zip(PgHbaHDR, cols[:7]))
        self.cleanEmptyRuleKeys(rule)
        rule['line'] = line
        return rule

    def cleanEmptyRuleKeys(self, rule):
        for k in rule.keys():
            if not rule[k]:
                del rule[k]

    def rule2key(self, rule):
        if rule['type'] == 'local':
            source = 'local'
        elif ipv4_re.search(rule['src']):
            if '/' in rule['src']:
                nw, prefix = rule['src'].split('/')
                netmask = prefix_to_ipv4netmask(prefix)
                source = nw+'/'+netmask
            elif 'mask' not in rule.keys():
                source = rule['src']+'/255.255.255.255'
            else:
                source = rule['src']+'/'+rule['mask']
        elif ipv6_re.search(rule['src']):
            if '/' in rule['src']:
                nw, prefix = rule['src'].split('/')
                netmask = prefix_to_ipv6netmask(prefix)
                source = nw+'/'+netmask
            elif 'mask' not in rule.keys():
                source = rule['src']+'/ffff:ffff:ffff:ffff:ffff:ffff'
            else:
                source = rule['src']+'/'+rule['mask']
        else:
            source = rule['src']

        return (source, rule['db'], rule['usr'])

    def rule2weight(self, rule):
        # For networks, every 1 in 'netmask in binary' makes the subnet more specific.
        # Therefore I chose to use prefix as the weight.
        # So a single IP (/32) should have twice the weight of a /16 network.
        # To keep everything in the same wieght scale for IPv6, I chose 
        # - a scale of 0 - 128 from 0 bits to 32 bits for ipv4 and 
        # - a scale of 0 - 128 from 0 bits to 128 bits for ipv6.
        if rule['type'] == 'local':
            #local is always 'this server' and therefore considered /32
            srcweight = 128 #(ipv4 /32 is considered equivalent to ipv6 /128)
        elif ipv4_re.search(rule['src']):
            if '/' in rule['src']:
                #prefix tells how much 1's there are in netmask, so lets use that for sourceweight
                prefix = rule['src'].split('/')[1]
                srcweight = int(prefix) * 4
            elif 'mask' in rule.keys():
               #Netmask. Let's count the 1's in the netmask in binary form.
                bits = "{0:b}".format(ipv4_to_int(rule['mask']))
                srcweight = bits.count('1') * 4
            else:
                #seems, there is no netmask / prefix to be found. Then only one IP applies.
                srcweight = 128 #(ipv4 /32 is considered equivalent to ipv6 /128)
        elif ipv6_re.search(rule['src']):
            if '/' in rule['src']:
                #prefix tells how much 1's there are in netmask, so lets use that for sourceweight
                prefix = rule['src'].split('/')[1]
                srcweight = int(prefix)
            elif 'mask' in rule.keys():
               #Netmask. Let's count the 1's in the netmask in binary form.
                bits = "{0:b}".format(ipv6_to_int(rule['mask']))
                srcweight = bits.count('1') * 4
            else:
                #seems, there is no netmask / prefix to be found. Then only one IP applies.
                srcweight = 128 #(ipv4 /32 is considered equivalent to ipv6 /128)
        else:
            #You can also write all to match any IP address, samehost to match any of the server's own IP addresses, or samenet to match any address in any subnet that the server is directly connected to.
            if rule['src'] == 'all':
                srcweight = 0
            elif rule['src'] == 'samehost':
                srcweight = 128 #(ipv4 /32 is considered equivalent to ipv6 /128)
            elif rule['src'] == 'samenet':
                #Might write some fancy code to determine all prefix's 
                #from all interfaces and find a sane value for this one.
                #For now, let's assume /24...
                srcweight = 96 #(ipv4 /24 is considered equivalent to ipv6 /96)
            elif rule['src'][0] == '.':
                # suffix matching, let's asume a very large scale and therefore a very low weight.
                srcweight = 64 #(ipv4 /16 is considered equivalent to ipv6 /64)
            else:
                #hostname, let's asume only one host matches
                srcweight = 128 #(ipv4 /32 is considered equivalent to ipv6 /128)

        #One little thing: for db and user weight, higher weight means less specific and thus lower in the file.
        #Since prefix is higher for more specific, I inverse the output to align with how dbweight and userweight works...
        srcweight = 128 - srcweight #(higher prefix should be lower weight)

        if rule['db'] == 'all':
            dbweight = len(self.databases) + 1
        elif rule['db'] == 'replication':
            dbweight = 0
        elif rule['db'] in [ 'samerole', 'samegroup']:
            dbweight = 1
        else:
            dbweight = 1 + rule['db'].count(',')

        if rule['usr'] == 'all':
            uweight = len(self.users) + 1
        else:
            uweight = 1

        ret = []
        for c in self.order:
            if c == 'u':
                ret.append(uweight)
            elif c == 's':
                ret.append(srcweight)
            elif c == 'd':
                ret.append(dbweight)

        return tuple(ret)

    def log_message(self, message):
        if self.syslogging:
            syslog.syslog(syslog.LOG_NOTICE, 'ansible: "%s"' % message)

    def is_empty(self):
        if len(self.rules) == 0:
            return True
        else:
            return False

    def write(self, backup_file=None):
        if not self.changed:
            return

        if backup_file:
            fileh = open(backup_file, 'w')
        elif self.pg_hba_file:
            fileh = open(self.pg_hba_file, 'w')
        else:
            filed, path = tempfile.mkstemp(prefix='pg_hba')
            fileh = os.fdopen(filed, 'w')

        fileh.write(self.render())
        fileh.close()

        # return if making a backup
        if backup_file:
            return

    def new_rule(self, contype, databases, users, source, netmask, method, options):
        if method not in PgHbaMethods:
            raise PgHbaError("invalid method {0} (should be one of '{1}').".format(method, "', '".join(PgHbaMethods)))
        if contype not in PgHbaTypes:
            raise PgHbaError("invalid connection type {0} (should be one of '{1}').".format(contype, "', '".join(PgHbaTypes)))
        # Add the job
        rule = dict(zip(PgHbaHDR, [contype, databases, users, source, netmask, method, options]))

        if contype == 'local':
            del rule['src']
            del rule['mask']
        elif '/' in source:
            del rule['mask']
        elif ipv4_re.search(source):
            if not netmask:
                rule['src'] += '/32'
        elif '/' in source:
            if not netmask:
                rule['src'] += '/128'
        else:
            del rule['mask']

        self.cleanEmptyRuleKeys(rule)

        line = [ rule[k] for k in PgHbaHDR if k in rule.keys() ]
        rule['line'] = "\t".join(line)
        return rule

    def add_rule(self, rule):
        key = self.rule2key(rule)
        try:
            oldrule = self.rules[key]
            ekeys = set(oldrule.keys() + rule.keys())
            ekeys.remove('line')
            for k in ekeys:
                if oldrule[k] != rule[k]:
                    raise Exception('')
        except:
            self.rules[key] = rule
            self.changed = True
            if rule['db'] not in [ 'all', 'samerole', 'samegroup', 'replication' ]:
                databases = set(rule['db'].split(','))
                self.databases.update(databases)
            if rule['usr'] != 'all':
                user = rule['usr']
                if user[0] == '+':
                    user = user[1:]
                self.users.add(user)

    def remove_rule(self, rule):
        keys = self.rule2key(rule)
        try:
            del self.rules[keys]
            self.changed = True
        except:
            pass
        
    def get_rules(self):
        ret = []
        for k in self.rules.keys():
            rule = self.rules[k]
            del rule['line']
            ret.append(rule)
        return ret

    def render(self):
        comment = '\n'.join(self.comment)
        sorted_rules = sorted(self.rules.values(), key=self.rule2weight)
        rule_lines = '\n'.join([ r['line'] for r in sorted_rules ])
        result = comment+'\n'+rule_lines
        #End it properly with a linefeed (if not already).
        if result and result[-1] not in ['\n', '\r']:
            result += '\n'
        return result

# ===========================================
# Module execution.
#

def main():
    module = AnsibleModule(
        argument_spec=dict(
            contype=dict(default="host", choices=PgHbaTypes + ['']),
            backup=dict(default=False, type='bool'),
            create=dict(default=True, type='bool'),
            databases=dict(default='all'),
            dest=dict(required=True),
            group=dict(default='postgres'),
            method=dict(default='md5', choices = PgHbaMethods),
            mode=dict(default='640', type='int'),
            netmask=dict(default=''),
            options=dict(default=''),
            order=dict(default="sdu", choices=PgHbaOrders),
            owner=dict(default='postgres'),
            state=dict(default="present", choices=["absent", "present"]),
            source=dict(default='samehost'),
            users=dict(default='all')
        ),
        supports_check_mode = True
    )

    contype  = module.params["contype"]
    if module.check_mode:
        backup = False
    else:
        backup  = module.params['backup']
    create    = module.params["create"]
    databases = module.params["databases"]
    dest      = os.path.expanduser(module.params["dest"])

    group     = module.params["group"]
    method    = module.params["method"]
    mode      = module.params["mode"]
    netmask   = module.params["netmask"]
    options   = module.params["options"]
    order     = module.params["order"]
    owner     = module.params["owner"]
    source    = module.params["source"]
    state     = module.params["state"]
    users     = module.params["users"]

    if create:
        touch(dest, owner, group, mode)
    pg_hba = PgHba(dest, order)

    # if requested make a backup before making a change
    if backup:
        (backuph, backup_file) = tempfile.mkstemp(prefix='pg_hba')
        pg_hba.write(backup_file)

    if contype:
        rule = pg_hba.new_rule(contype, databases, users, source, netmask, method, options)
        if state == "present":
            pg_hba.add_rule(rule)
        else:
            pg_hba.remove_rule(rule)
        if not module.check_mode:
            pg_hba.write()

    ret={}
    if pg_hba.changed:
        ret['changed'] = True

    # retain the backup only if pg_hba file has changed
    if backup:
        if pg_hba.changed:
            ret['backup_file'] = backup_file
        else:
            os.unlink(backup_file)
    ret['pg_hba'] = pg_hba.get_rules()
    ret['rc'] = 0
    module.exit_json(**ret)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.database import *

main()
