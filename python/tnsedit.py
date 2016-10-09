#!/usr/bin/python2

import re
qt_re = re.compile("\A.+?'")
dqt_re = re.compile('\A.+?"')
remark_re = re.compile('\A#.*?\n')
name_re = re.compile('\s*(\S+)\s*=')
name_value_re = re.compile('\s*(\S+)\s*=\s*(\S+)\s*')
whitespace_re = re.compile('\s+')
text_re = re.compile('''\A.*?[()#"']''', re.DOTALL)

class TNSConfig(list):
  def formatted(self,spcs=2,lvl=0):
    ret=''
    for piece in self:
      if type(piece) == str:
        piece=re.sub('[ \t\n\r]*=[ \t\n\r]*', ' = ', piece.strip(' \t\n\r'))
        if piece == '':
          pass
        elif piece == ')':
          ret+=piece
        elif piece == '(':
          if len(ret) > 0 and ret[-1] != '\n':
            ret+='\n'
          ret+=lvl*spcs*' '+piece
        elif piece[0] == '#':
          ret+=piece+'\n'
        else:
          if lvl<2:
            ret+='\n'
          ret+=piece
      else:
        if len(ret) > 0 and ret[-1] == ')':
          ret+='\n'
        elif ret[-3:] == ' = ':
          ret+='\n'
        ret+=piece.formatted(spcs,lvl+1)
    return ret
  def __str__(self):
    ret=''
    for piece in self:
#      print piece.__repr__()
      if type(piece) == str:
        ret+=piece
      else:
        ret+=str(piece)
    return ret
  def __init__(self, content):
    if content == '':
      return
    content,rest=self.init_element(content)
    for piece in content:
      if type(piece) == str:
        self.append(piece)
      else:
        self.repl_element(piece)
    self.append(rest[0:-1])
  def init_element(self,content):
    data=TNSConfig('')
    while len(content) > 0:
      if content[0] == '#':
        m=remark_re.search(content)
        if not m:
          return data, content
        piece=m.group(0)
        content=content[len(piece):]
        data.append(piece)
      elif content[0] == '"' or content[0] == "'":
        if content[0] == '"':
          m=dqt_re.search(content)
        else:
          m=qt_re.search(content)
        if not m:
          return data, content
        piece=m.group(0)
        content=content[len(piece):]
        data.append(piece)
      elif content[0] == '(':
        element=TNSConfig('')
        data.append(element)
        element.append(content[0])
        content=content[1:]
        piece,content = self.init_element(content)
        element.append(piece)
      elif content[0] == ')':
        data.append(content[0])
        content = content[1:]
        m=whitespace_re.match(content)
        if m:
          piece=m.group(0)
          data.append(piece)
          content = content[len(piece):]
        return data, content
      else:
        m=text_re.search(content)
        if not m:
          return data, content
        piece = m.group(0)[0:-1]
        content = content[len(piece):]
        element=TNSConfig('')
        data.append(element)
        element.append(piece)
        while content[0] == '(':
          element.append(content[0])
          content=content[1:]
          piece,content = self.init_element(content)
          element.append(piece)
          if len(content) == 0: break
    return data, content
  def name(self):
    try:
      m=name_re.search(self[0])
      return m.group(1)
    except:
      return False
  def sub_names(self):
    ret = []
    for sub in self:
      try:
        ret.append(sub.name())
      except:
        pass
    return ret
  def del_element(self, name):
    for i in range(len(self)):
      try:
        while self[i].name() == name:
          self.pop(i)
      except:
        pass
  def del_by_path(self, path, val):
    ret=False
    if path[0][0] == '!':
      path[0]=path[0][1:]
      removetree = True
    elif len(path) == 1:
      removetree = True
    else:
      removetree = False

    re_path = re.compile(path[0])
    re_value = re.compile('{0}\s*=\s*{1}'.format(path[0],val))
    i=0
    while i<len(self):
      try:
        e=self[i]
        if len(path) > 1:
          name = e.name()
          if name:
            m=re_path.search(name)
            if m:
              ret = e.del_by_path(path[1:], val)
          else:
            ret = e.del_by_path(path, val)
        else:
          if re_value.search(str(e)):
            ret=True
        if ret and removetree:
          self.pop(i)
          self.pop(i-1)
          i-=2
      except Exception, exc:
        pass
      i+=1
    return ret
  def get_element(self, name):
    for i in range(len(self)):
      try:
        if self[i].name() == name:
          return self[i]
      except:
        pass
  def repl_element(self, new):
    if type(new)==str:
      new=TNSConfig(new)
      new.append('\n\n')
    name=new.name()
    if not name:
      self.append(new)
      return
    for i in range(len(self)):
      try:
        if self[i].name() == name:
          self[i]=new
          return new
      except:
        pass
    self.append(new)
    return new
  def sort(self):
    tmp=[]
    ret=TNSConfig('')
    for item in self:
      try:
        name=item.name()
        tmp.append(name)
      except:
        ret.append(item)
    tmp.sort()
    for name in tmp:
      ret.append(self.get_element(name))
    return ret

if __name__ == "__main__":
  from sys import exit, stdin, stdout, stderr
  from optparse import OptionParser, OptionGroup
  from time import strftime
  from shutil import copy

  usage='''Usage: %prog [options] [infiles]
%prog receives tns entries from stdin and writes the to stdout or outfile (-o).
%prog  can be used with the following options:'''
  parser = OptionParser(usage=usage)
  parser.add_option("-o", "--outfile", dest="outfile", help="The file to store the output. Without, stdout will b used instead.", default=False)
  parser.add_option("-s", "--sort", action="store_true", dest="sort", help="Sort services before outputting. This options also implies -f.", default=False)
  parser.add_option("-e", "--element", dest="element", help="Only show first element with name 'ELEMENT'. Cannot be used in combination with -l.", default=False)
  parser.add_option("-l", "--list", action="store_true", dest="list", help="Only list service names. Cannot be used in combination with -e. -o will be used as input file.", default=False)
  parser.add_option("-d", "--delete", dest="deletelist", help="A comma seperated list of entries to delete from ouput.", default="")
  parser.add_option("-p", "--delete_by_path", dest="delete_by_path", help="A path/subpath=value expression to distinquish items that shoud be deleted. The path should have a format like /GRAND/PARENT/!CHILD/NAME=VALUE. The '!' specifies from where the tree must be removed example: specify -p 'LISTENER_.*/DESCRIPTION_LIST/DESCRIPTION/!ADDRESS/HOST=.*-vip.*' to remove all addresses with a value HOST=*-vip*.", default="")
  parser.add_option("-r", "--replace", action="store_true", dest="replace", help="Replace output file (don't read it before parsing other input).", default=False)
  parser.add_option("--nostdin", action="store_false", dest="stdin", help="Don't read from stdin.", default=True)
  parser.add_option("--noformat", action="store_false", dest="format", help="Do not reformat the output (not recommended).", default=True)
  parser.add_option("--nobackup", action="store_false", dest="backup", help="Do not create backup before changing the file (not recommended).", default=True)

#  parser.add_option("-c", "--casesensitive", action="store_true", dest="case", help="Operate case sensitive (excludes -i).", default=True)
#  parser.add_option("-i", "--caseinsensitive", action="store_false", dest="case", help="Operate case insensitive (excludes -c).", default=False)

  group = OptionGroup(parser, "All other options", '''All other options are considered input files.
First the contents of outfile will be read (if -r is not used of course) and applied to the internal TNS structure.
Then contents from all other input files will be read and applied.
Then stdin will be read and applied.
Then -d items will be removed.

Please be aware that duplicate entries are always replaced by the last one read.
Outfile (or stdout) will never contain duplicate entries.''')
  parser.add_option_group(group)

  (options, args) = parser.parse_args()

  if options.outfile:
    if options.element:
      usage()
      stderr.write('Savety: Cannot output one element to file. Use > if you really do want to.\n')
      exit(1)
    elif options.list:
      usage()
      stderr.write('Savety: Cannot output service names to file. Use > if you really do want to.\n')
      exit(1)
    try:
      if not options.replace:
        print "opening "+options.outfile
        source=open(options.outfile,'r')
        try:
          tnsoutfile=TNSConfig(source.read())
        finally:
          source.close()
    except:
      tnsoutfile=TNSConfig('')
  else:
    tnsoutfile=TNSConfig('')

  for infile in args:
    source=open(infile,'r')
    try:
      tnsinfile=TNSConfig(source.read())
    finally:
      source.close()
    for item in tnsinfile:
      tnsoutfile.repl_element(item)

  if options.stdin and len(args)==0:
    tns_stdin = TNSConfig(stdin.read())
    for item in tns_stdin:
      tnsoutfile.repl_element(item)

  for item in options.deletelist.split(","):
    tnsoutfile.del_element(item)

  if options.delete_by_path != "":
    try:
      path, val = options.delete_by_path.split('=')
      path = path.split('/')
      tnsoutfile.del_by_path(path, val)
    except:
      pass

  if options.sort == 1:
    tnsoutfile=tnsoutfile.sort()
    options.format=1

  if options.element:
    element=TNSConfig('')
    element.append(tnsoutfile.get_element(options.element))
    if not element:
      stderr.write('Unknown element '+options.element+'\n')
      exit(1)
  else:
    element=tnsoutfile

  if options.list:
    if options.outfile:
      usage()
      stderr.write('Savety: Cannot output service names to file. Use > if you really do want to.\n')
      exit(1)
    for item in element.sub_names():
      if item:
        print item
  elif not options.outfile:
    if options.format:
      stdout.write(element.formatted()+'\n')
    else:
      stdout.write(str(element)+'\n')
  else:
    print "Outfile"
    if options.backup:
      backupfile=options.outfile+'.'+strftime('%Y%m%d%H%M%S')
      print 'Backing up to: '+backupfile
      copy(options.outfile,backupfile)
    dest = open(options.outfile,'w+')
    if options.format:
      dest.write(element.formatted()+'\n')
    else:
      dest.write(str(element)+'\n')

  if options.outfile:
    print "Succesfully written to "+options.outfile
