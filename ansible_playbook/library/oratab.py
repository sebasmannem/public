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
module: oratab
short_description: Adds, removes or modifies an oracle SID in an oratab file.
description:
   - The fundamental function of the module is to create, or delete lines in oratab files.
   - The lines in the file should be in a form of 'SID:HOME:ENABLED' and SID's should be unique.
     If they are not unique and the SID is 'the one to change', only one (for present) or no (for absent) of the SID's will remain.
version_added: "2.2"
options:
  dest:
    description:
      - path to oratab file to modify.
    required: false
    default: /etc/oratab
  backup:
    description:
      - If set, create a backup of the oratab before it is modified.
        The location of the backup is returned in the C(backup) variable by this module.
    required: false
    default: false
  create:
    description:
      - create an oratab file if none should exists.
      - When set to false, an error is raised when oratab file doesn't exist.
    required: false
    default: false
  owner:
    description:
      - owner of the oratab file (almost always oracle).
    required: false
    default: oracle
  group:
    description:
      - group owner of the oratab file (almost always oinstall).
    required: false
    default: oinstall
  mode:
    description:
      - file mode a newly created file should have
    required: false
    default: 664
  sid:
    description:
      - name of SID (almost always name of the database).
    required: true
    default: null
    aliases: [ "dest" ]
  home:
    description:
      - path of the oracle home to be used.
      - required for state=present
    required: false
    default: null
  enabled:
    description:
      - When enabled=yes, dbstart auto will start the database and dbshut auto wil stop it.
    required: false
    default: YES
    choices: [ "yes", "no" ]
  state:
    description:
      - The line(s) will be added/modified when state=present and removed when state=absent
    required: false
    default: present
    choices: [ "present", "absent" ]
  sorted:
    description:
      - Write the output in sorted form.
      - When "yes", first comments and other lines containing no actual sid info will be written.
      - After that all sids will be written out, sorted by sid.
      - Please be aware that sorted will make every sid unique (as it should be already)
    required: false
    default: NO
    choises: [ "yes", "no" ]

notes:
   - The default authentication assumes that you are either logging in as or
     sudo'ing to the oracle account on the host.
   - this module also returns the SID info. You can find it in oratab, in format: (SID='',HOME='',ENABLED='Y'/'N')
author: Sebastiaan Mannem
'''

EXAMPLES = '''
# Add DB1:/u01/app/oracle/prod/db:yes to oratab (creating file if it doesn't exist).
- oratab: sid=db1 home=/u01/app/oracle/prod/db enabled=yes create=yes
'''

import os
import pwd
import grp
import stat
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
        raise TouchError('Could not create file {0}. Please becoma a user with sufficient permissions.'.format(path))
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

class OraTabError(Exception):
    pass

class OraTab(object):
    """
        OraTab object to read/write oracle SID info to/from.

        oratab_file - the oratab file almost always /etc/oratab
        Note: I copied this from crontab module and modiefied as needed...
    """
    def __init__(self, oratab_file=None, dosort=False):
        self.oratab_file = oratab_file
        self.dosort      = dosort
        self.lines       = None
        self.changed     = True

        # select whether we dump additional debug info through syslog
        self.syslogging = False

        self.read()

    def read(self):
        # Read in the oratab from the system
        self.lines = []
        # read the oratabfile
        try:
            f = open(self.oratab_file, 'r')
            for l in f:
                try:
                    l=l.strip()
                    #uncomment
                    t=l.split('#')[0]
                    #split into sid, home, enabled
                    sid, home, enabled = t.split(':')[0:3]
                    enabled = enabled.upper() == 'Y'
                except:
                    sid, home, enabled = None, None, None
                finally:
                    self.lines.append((sid, home, enabled, l))
                
            f.close()
            self.changed = False
        except IOError, e:
            raise OraTabError("oratab file '{0}' doesn't exist. use create option to autocreate.".format(self.oratab_file))
        except:
            raise OraTabError("Unexpected error:", sys.exc_info()[0])

    def log_message(self, message):
        if self.syslogging:
            syslog.syslog(syslog.LOG_NOTICE, 'ansible: "%s"' % message)

    def sids(self):
        return set([ l[0] for l in self.lines if l[0] ])

    def is_empty(self):
        if len(self.sids()) == 0:
            return True
        else:
            return False

    def write(self, backup_file=None):
        if not self.changed:
            return

        if backup_file:
            fileh = open(backup_file, 'w')
        elif self.oratab_file:
            fileh = open(self.oratab_file, 'w')
        else:
            filed, path = tempfile.mkstemp(prefix='oratab')
            fileh = os.fdopen(filed, 'w')

        fileh.write(self.render())
        fileh.close()

        # return if making a backup
        if backup_file:
            return

    def add_sid(self, sid, home, enabled):
        # Add the job
        line = ":".join([sid, home, 'Y' if enabled else 'N'])
        if sid in self.sids():
            found = False
            for i in range(len(self.lines)):
                if i > len(self.lines):
                    break
                lsid, lhome, lenabled, lline = self.lines[i]
                if sid==lsid:
                    if not found:
                        if lline != line:
                            self.lines[i] = (sid, home, enabled, line)
                            self.changed = True
                    else:
                        self.lines.pop(i)
                        self.changed = True
                    found = True
        else:
            self.lines.append((sid, home, enabled, line))
            self.changed = True

    def remove_sid(self, sid):
        for i in range(len(self.lines)):
            lsid, lhome, lenabled, lline =self.lines[i]
            if sid==lsid:
                self.lines.pop(i)
                self.changed = True

    def get_entries(self):
        hdr=['sid', 'home', 'enabled']
        ret=[]
        for l in self.lines:
            if l[0]:
                l=list(l)
                ret.append(dict(zip(hdr,l[0:3])))
        return ret

    def render(self):
        """
        Render this oratab as it would be written in the oratab file.
        """
        if self.dosort:
            #First find comment lines
            comment      = [ l[3] for l in self.lines if not l[0] ]
            #Then sort all lines
            sorted_lines = sorted(self.lines, key=lambda line: line[0])
            #And find the sid lines in the sorted lines
            sorted_sids  = [ l[3] for l in sorted_lines if l[0] ]
            #And finish by adding the two together to one list again
            lines        = comment + sorted_sids
        else:
            lines = [ l[3] for l in self.lines ]
        #Merge all lines to one big string with linefeeds
        result='\n'.join(lines)
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
            backup=dict(default=False, type='bool'),
            create=dict(type='bool', default='yes'),
            dest=dict(default='/etc/oratab'),
            enabled=dict(type='bool', default='yes'),
            group=dict(default='oinstall'),
            home=dict(default=''),
            mode=dict(default='664', type='int'),
            owner=dict(default='oracle'),
            sid=dict(default='',aliases=['name']),
            sorted=dict(type='bool', default='no'),
            state=dict(default="present", choices=["absent", "present"])
        ),
        supports_check_mode = True
    )
    if module.check_mode:
        backup = False
    else:
        backup  = module.params['backup']
    create  = module.params["create"]
    dest    = module.params["dest"]
    enabled = module.params["enabled"]
    group   = module.params["group"]
    home    = module.params["home"]
    mode    = module.params["mode"]
    owner   = module.params["owner"]
    sid     = module.params["sid"]
    dosort  = module.params["sorted"]
    state   = module.params["state"]

    # Ensure all files generated are only writable by the owning user.  Primarily relevant for creating the orafile.
#    os.umask(mode)
    if create:
        touch(dest, owner, group, mode)
    oratab = OraTab(dest, dosort)

    # if requested make a backup before making a change
    if backup:
        (backuph, backup_file) = tempfile.mkstemp(prefix='oratab')
        oratab.write(backup_file)

    if sid:
        if state == "present":
            oratab.add_sid(sid, home, enabled)
        else:
            oratab.remove_sid(sid)
        if not module.check_mode:
            oratab.write()

    ret={}
    if oratab.changed:
        ret['changed'] = True

    # retain the backup only if oratab file has changed
    if backup:
        if oratab.changed:
            ret['backup_file'] = backup_file
        else:
            os.unlink(backup_file)
    ret['oratab'] = oratab.get_entries()
    module.exit_json(**ret)

# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.database import *

try:
    main()
except Exception, e:
    module.fail_json(msg=str(e))
