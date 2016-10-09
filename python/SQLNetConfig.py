#!/usr/bin/python2
background_info='''
This library delivers a series of objects for interpreting SQLNet Config Files like tnsnames.ora and listener.ora.
One might look at http://www.orafaq.com/wiki/SQL*Net for more info on this subject.
This library delivers:
list       > SNCGroup  : a list like object defining a group of SQLNetConfig entries/SQLNetConfig subgroups.
                         examples are:
                         - reading a SQLNet File results in one SNCgroup with nested sub SNCGroups and SNCValues.
                         - a TNSNames Entry would be a SNCgroup with nested sub SNCGroups and SNCValues
str        > SNCElement: a string like object beholding a SNC value. Actually this is only used as parent for other subtypes of SNCValues
SNCElement > SNCComment: a string like object beholding a commentline from a SQLNet file
SNCElement > SNCString : a string like object beholding a string (everyting inside single or double quotes) from a SQLNet entry.
SNCElement > SNCMarker : a string like object beholding a marker wich marks the beginning or end of a group. This would typically be a round bracket ("(", or ")") tailed by some whispace.
SNCElement > SNCKey    : a string like object beholding a 'name = ' like string It should be a key holding a value.

One can read a SQLNet file and dump it's contents in the initialisation of a SNCGroup like this:
with open('/path/to/mySQLNETfile') as f:
  mySNC=SNCGroup(f.read())
this would result in:
- reading the file and parsing to the object init procedure
- Spliting the string in a one dimensional array of SNCElement subtype objects
- Adding subgroups with sub-sub groups with ... and with SNCElement subtypes in the end.

Example:
Reading tnsnames with:
# Comment
RMAN_CAT =
  (DESCRIPTION =
...

Would eventually create:
SNCFile(), beholding
- SNCComment('# Comment\n')
- SNCGroup(), beholding
  - SNCValue('RMAN_CAT =\n  ')
  - SNCGroup(), beholding
    - SNCMarker('(')
    - SNCValue('(DESCRIPTION =\n      ')
etc.
'''

import re
qt_re = re.compile("\A'.+?'")
dqt_re = re.compile('\A".+?"')
groupmark_re = re.compile('\A[()]')
comment_re = re.compile('\A\s*#[^\n]*\n?')
#key_re = re.compile('''\A\s*(\S+)\s*=\s*''')
key_value_re = re.compile('''\A(\s*\S+\s*=\s*)([^()#"'=]+|\()?''')
nextpart_re = re.compile('''\A\s*.?''')
hastext_re = re.compile('\S')
whitespace_re = re.compile('\s+')
trim_re = re.compile('\A\s*(.*?)\s*\Z')
rest_re = re.compile('''\A[^()#"'=]*''')

class SNCGroup(list):
  def __repr__(self):
    return "['(', " + ', '.join([ item.__repr__() for item in self ]) + ", ')']"
  def __str__(self):
    return "(" + ''.join([ item.__str__() for item in self ]) + ")"
  def formatted(self,spacer,level):
    ret='\n'+spacer*level+'('
    ret+=''.join([item.formatted(spacer,level+1) for item in self])
    ret+=')'
    return ret
    
class SNCFile(list):
  def __init__(self, filename=None, doSort = False, format = '  '):
    self.__filename = filename
    self.__doSort = doSort
    self.__format = format
    self.__index = False
  def __str__(self):
    return ''.join([ item.__str__() for item in self ])
  def setFormat(self, spacer):
    self.__format=spacer
  def setSorted(self,value=True):
    self.__doSort=value
  def setFilename(self, filename):
    if self.__filename:
      raise SNCObjectError('Cannot set filename on SNCFile if it is already set.')
    else:
      self.__filename = filename
  def sorted(self):
    srtd=SNCFile(self.__filename, self.__doSort, self.__format)
    body={}
    for piece in self:
      try:
        body[piece.name()] = piece
      except:
        srtd.append(piece)
    srtd+=[body[key] for key in sorted(body.keys())]
    return srtd
  def formatted(self):
    if self.__doSort:
      pieces=self.sorted()
    else:
      pieces=self
    if not self.__format:
      return pieces.__str__()
    else:
      ret=[]
      for piece in pieces:
        output=piece.formatted(self.__format,1)
        if output != '':
          ret.append(output)
      return '\n'.join(ret)+'\n'
  def extend(self, other):
    for item in other:
      self.append(item)
  def __buildIndex(self):
    if not self.__index:
      self.__index = {}
      for i in range(len(self)):
        try:
          self.__index[self[i].name()] = i
        except:
          pass
  def append(self,item):
    self.__buildIndex()
    try:
      self.remove(item.name())
    except:
      pass
    self.insert(len(self),item)
    try:
      self.__index[item.name()]=len(self)
    except:
      pass
  def remove(self,key):
    self.__buildIndex()
    try:
      index=self.__index[key]
      self[index-1]=SNCString('')
      del self.__index[key]
    except:
      pass
  def getElement(self,key):
    self.__buildIndex()
    try:
      index=self.__index[key]
      return self[index]
    except:
      return False
  def listServices(self):
    self.__buildIndex()
    keys=self.__index.keys()
    if self.__doSort:
      keys.sort()
    return keys
  def readFile(self, filename=None):
    if not filename:
      filename = self.__filename
    if not filename:
      raise SNCObjectError("Cannot read file without setting filename")
    source=open(filename,'r')
    self.parse(source.read())
    source.close()
  def writeFile(self, filename=None):
    if not filename:
      filename = self.__filename
    if not filename:
      raise SNCObjectError("Cannot write file without setting filename")
    dest = open(filename,'w+')
    dest.write(self.formatted())
    print "Succesfully written to "+options.outfile
  def parse(self, TNSString):
    stack=[]
    current=self
    while TNSString != '':
      nextpart=nextpart_re.search(TNSString).group(0)
      if nextpart[-1] == '#':
        m = comment_re.search(TNSString)
        if not m:
          raise SNCInconsistentError("'#', but comment_re doesn't work. This should be impossible...\n"+TNSString.__repr__())
        slice=m.group(0)
        current.append(SNCComment(slice))
        TNSString=TNSString[len(slice):]
      elif nextpart[-1] == '(':
        if len(nextpart) > 1:
          current.append(SNCString(nextpart[:-1]))
        new=SNCGroup()
        current.append(new)
        stack.append(current)
        current=new
        TNSString=TNSString[len(nextpart):]
      elif nextpart[-1] == ')':
        if len(nextpart) > 1:
          current.append(SNCString(nextpart[:-1]))
        try:
          current=stack.pop()
        except:
          raise SNCInconsistentError("Less open group markers '(', than close group markers ')'.")
        TNSString=TNSString[len(nextpart):]
      elif nextpart[-1] == "'":
        m = qt_re.search(TNSString)
        if not m:
          raise SNCInconsistentError("Start of text, but no end. TNSString is not consistent.\n"+TNSString.__repr__())
        slice=m.group(0)
        current.append(SNCText(slice))
        TNSString=TNSString[len(slice):]
      elif nextpart[-1] == '"':
        m = dqt_re.search(TNSString)
        if not m:
          raise SNCInconsistentError("Start of text, but no end. TNSString is not consistent.\n"+TNSString.__repr__())
        slice=m.group(0)
        current.append(SNCText(slice))
        TNSString=TNSString[len(slice):]
      else:
        m = key_value_re.search(TNSString)
        if m:
          slice, key, value = m.group(0,1,2)
          if value == '(':
            value = SNCGroup()
            new=SNCKey(key, value)
            current.append(new)
            stack.append(current)
            current=new
          else:
            value = SNCString(value)
            current.append(SNCKey(key, value))
        else:
          m = rest_re.search(TNSString)
          slice = m.group(0)
          current.append(SNCString(slice))
        TNSString=TNSString[len(slice):]

class SNCElement(str):
  def __init__(self, value):
    self.__trimname = trim_re.search(value).group(1)
  def formatted(self,spacer,level):
    return self.__trimname

class SNCComment(SNCElement):
  def __init__(self, value):
    self.__trimname = trim_re.search(value).group(1)
    rest= comment_re.sub(value,'',1)
    if rest != '':
      raise SNCObjectError("Invalid SNCComment:\n"+value.__repr__()+"\n")
  def formatted(self,spacer,level):
    return spacer*(level-1)+self.__trimname

class SNCText(SNCElement):
  def __init__(self, value):
    SNCElement.__init__(self, value)
    if value[0] not in ('"',"'") or  value[-1] !=  value[0]:
      raise SNCObjectError("Invalid SNCText (should start and end with quotes ['] or with double quotes [\"]):"+value.__repr__()+"\n")

class SNCString(SNCElement):
  def __init__(self, value):
    SNCElement.__init__(self, value)


class SNCKey():
  def __init__(self, key, value):
    self.__name = key
    self.__trimname = trim_re.search(key.replace('=','')).group(1)
    self.__value = value
  def __repr__(self):
    return self.__name.__repr__() + self.__value.__repr__()
  def __str__(self):
    return self.__name+self.__value.__str__()
  def name(self):
    return self.__trimname
  def append(self, value):
    self.__value.append(value)
  def formatted(self,spacer,level):
    ret=''
    if level<=1:
      ret+='\n'
    ret += self.__trimname + ' = ' + self.__value.formatted(spacer, level)
    return ret
    
class SNCError(StandardError):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class SNCInconsistentError(SNCError):
  def __init__(self, value):
    self.value = value

class SNCObjectError(SNCError):
  def __init__(self, value):
    self.value = value

if __name__ == "__main__":
  from sys import exit, stdin, stdout, stderr, exc_info
  from optparse import OptionParser, OptionGroup
  from time import strftime
  from shutil import copy

  usage='''Usage: %prog [options] [infiles]
%prog receives tns entries from stdin and writes the to stdout or outfile (-o).
%prog  can be used with the following options:'''
  parser = OptionParser(usage=usage)
  parser.add_option("-o", "--outfile", dest="outfile", help="The file to store the output. Without, stdout will be used instead.", default=False)
  parser.add_option("-s", "--sort", action="store_true", dest="sort", help="Sort services before outputting. This option overrules --noformat.", default=False)
  parser.add_option("-e", "--element", dest="element", help="Only show first element with name 'ELEMENT'. Cannot be used in combination with -l.", default=False)
  parser.add_option("-l", "--list", action="store_true", dest="list", help="Only list service names. Cannot be used in combination with -e.", default=False)
  parser.add_option("-p", "--path", dest="path", help="A path/subpath expression specifying which subtrees in the TNS to process for delete and add entries. This parameter affects the operation of -d --delete_by_path and stdin.", default="")
  parser.add_option("-d", "--delete", dest="deletelist", help="A comma seperated list of entries to delete.", default="")
  parser.add_option("--delete_by_path", dest="delbypath", help="A path/subpath expression identifying entries to delete. Every item with a corresponding subtree will be removed. use with -p to remove only sub items with a given sub-sub item.", default="")
  parser.add_option("-r", "--replace", action="store_true", dest="replace", help="Replace output file (don't read it before parsing other input).", default=False)
  parser.add_option("--nostdin", action="store_false", dest="stdin", help="Don't read from stdin.", default=True)
  parser.add_option("--format", dest="format", help="Set spacer for output format (default '  ').", default='  ')
  parser.add_option("--noformat", action="store_false", dest="format", help="Do not reformat the output (not recommended).", default='  ')
  parser.add_option("--nobackup", action="store_false", dest="backup", help="Do not create backup before changing the file (not recommended).", default=True)
  parser.add_option("--explain", action="store_true", dest="explain", help="Show additional help on this script.", default=False)

  group = OptionGroup(parser, "All other options", '''All other options are considered input files.
First the contents of outfile will be read (if -r is not used of course) and applied to the internal TNS structure.
Then contents from all other input files will be read and applied.
Then stdin will be read and applied.
Then -d items will be removed.

Please be aware that duplicate entries are always replaced by the last one read.
Outfile (or stdout) will never contain duplicate entries.''')
  parser.add_option_group(group)

  (options, args) = parser.parse_args()

  if options.explain:
    print(background_info)
    exit(0)

  tnsoutfile=SNCFile()
  tnsoutfile.setSorted(options.sort)
  tnsoutfile.setFormat(options.format)

  if options.outfile:
    tnsoutfile.setFilename(options.outfile)
    if options.element:
      usage()
      stderr.write('Savety: Cannot output one element to file. Use > if you really do want to.\n')
      exit(1)
    elif options.list:
      usage()
      stderr.write('Savety: Cannot output service names to file. Use > if you really do want to.\n')
      exit(1)
    if not options.replace:
      tnsoutfile.readFile()

  for infile in args:
    tnsoutfile.readFile(infile)


  if options.path != "":
    print "Subpath not supported yet"
    exit(1)
    tnsoutfile.setSubpath(options.path)

  if options.stdin:
    tnsoutfile.parse(stdin.read())

  if options.delbypath:
    print "Delbypath not supported yet"
    exit(1)
    try:
      delbypath=options.delbypath
      delbypath, val = delbypath.split('=')
      path=delbypath.split('/')
      tnsoutfile.delByPath(path, val)
    except Exception, exc:
      sterr.write('Invalid parameter for --delete_by_path ({0}, but should be in format /GRAND/PARENT/CHILD=VALUE).\n'.format(options.delbypath))
      exit(1)

  for eleName in options.deletelist.split(","):
    tnsoutfile.remove(eleName)

  if options.element:
    element=tnsoutfile.getElement(options.element)
    if element:
      print element.formatted(options.format,0)
      exit(0)
    else:
      stderr.write('Unknown element '+options.element+'\n')
      exit(1)

  if options.list:
    for item in tnsoutfile.listServices():
      print item
    exit(0)

  if not options.outfile:
    stdout.write(tnsoutfile.formatted())
    exit(0)

  if options.backup:
    backupfile=options.outfile+'.'+strftime('%Y%m%d%H%M%S')
    print 'Backing up to: '+backupfile
    copy(options.outfile,backupfile)

  tnsoutfile.writeFile()
