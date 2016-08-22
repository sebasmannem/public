#!/usr/bin/python2
def help():
  print """This program can be used to read passwords in/from a file.
It is used to define all oracle passwords that should be configured during creation of an Oracle database:
- SYS
- ORADBA
- RMAN_DBA
- DBSNMP
These passwords will be read by 'SBB_CreateDatabase.sh' if no passwords are registered in the environment.
Set the passwords in environmentvariables [USER]_PW and call this script to create a file, or call this script to set the environment from a file.
The programm will check environment variabele PASSWORD and use it as the encryption password.
If the environment variabele PASSWORD is not set, it will ask for one.
The PASSWORD used to create the file should be registered in KeePass.

Usage:"""
  print "  Write to file:",sys.argv[0]," -w [file]"
  print "  Read from file:",sys.argv[0]," -r [file]"
  print """
First implementation would set environment variabeles and the exit, but the environment variabeles would not be changed by this.
This implementation generates an export list so that the calling process could set the environment variables accordingly.
Later versions will support the feature to set the environment variables and then run a (predefinied) script.
To set environment variables in the calling script add this:"""
  print "eval $(./"+sys.argv[0]+" -r /tmp/sebas)"

import getpass, os, sys, cPickle
if (len(sys.argv)<3) or (sys.argv[1] != '-r' and sys.argv[1] != '-w'):
  x=help()
  sys.exit(1)
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
try:
  syspw = os.environ['PASSWORD']
except KeyError:
  print 'What is de sys password?'
  syspw = getpass.getpass()
hash = SHA256.new()
hash.update(syspw)
crypt = AES.new(hash.digest(), AES.MODE_CBC, 'Bassie is ok ole') #print len(hash.digest())

users="SYS","ORADBA","RMAN_DBA","DBSNMP"
passwords={}
if (sys.argv[1] == '-w'):
  try:
    for user in users:
      passwords[user]=os.environ[user+'_PW']
  except:
    print "Environment variabele "+user+"_PW is not set."
    sys.exit(1)
  try:
    pickled=cPickle.dumps(passwords)+'Pickle'
    pickled+=(16-(len(pickled)%16))*' '
    encrypted_pickle=crypt.encrypt(pickled)
  except Exception as inst:
    print "Could not pickle or encrypt"
    sys.exit(1)
  try:
    with open(sys.argv[2],'wb') as f:
      f.write(encrypted_pickle)
  except:
    print "Could not write to file"
    sys.exit(1)
else:
  try:
    with open(sys.argv[2],'rb') as f:
      encrypted_pickle=f.read()
  except:
    print "Could not read from file"
    sys.exit(1)
  try:
    pickled=crypt.decrypt(encrypted_pickle)
    pickled=pickled.rstrip()
    if (pickled[-6:] != 'Pickle'):
      print "Invalid password"
      sys.exit(1)
    pickled=pickled[0:-6]
    passwords=cPickle.loads(pickled)
  except:
    print "Could not unpickle or decrypt"
    sys.exit(1)
  try:
    for user in users:
      print 'export {0}_PW={1}'.format(user,passwords[user])
  except:
    print "Could not set environment variabele "+user+"_PW."
    sys.exit(1)
