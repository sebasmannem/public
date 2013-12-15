#!/usr/bin/python2
import re
fill_re = re.compile('^(.*?)([^\'"()=#])')
qt_re = re.compile("\A.+?'")
dqt_re = re.compile('\A.+?"')
remark_re = re.compile('\A.*?\n')
name_re = re.compile('\s*(\S+)\s*=')
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
          if lvl<=1:
            ret+='\n'
          ret+=str(lvl)+'_'+piece
      else:
        if len(ret) > 0 and ret[-1] == ')':
          ret+='\n'
        ret+=piece.formatted(spcs,lvl+1)
    return ret
  def __str__(self):
    ret=''
    for piece in self:
      if type(piece) == str:
        ret+=piece
      else:
        ret+=str(piece)
    return ret
  def __init__(self, content):
    if content == '':
      return
    content,rest=self.get_element(content)
    for piece in content:
      self.append(piece)
    self.append(rest[0:-1])
  def get_element(self,content):
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
        try:
          m = name_re.search(data[-1])
          name=m.group(1)
          element.append(data[-1])
          data[-1]=element
        except:
          name=None
          data.append(element)
        element.append(content[0])
        content=content[1:]
        piece,content = self.get_element(content)
        element.append(piece)
      elif content[0] == ')':
        data.append(content[0])
        content = content[1:]
        return data, content
      else:
        m=text_re.search(content)
        if not m:
          return data, content
        piece = m.group(0)[0:-1]
        content = content[len(piece):]
        data.append(piece)
    return data, content
  def name(self):
    try:
      m=name_re.search(self[0])
      return m.group(1)
    except:
      pass
  def sub_names(self):
    ret = []
    for sub in self:
      try:
        ret.append(sub.name())
      except:
        pass
    return ret

if __name__ == "__main__":
  def read_args():
#  if len(argv) < 2:
#   usage()
#   print "please specify at least 1 parameter."
#   exit(2)
    try:
      opts, args = getopt(argv[1:], "hs:d:i:", ["help", "source=", "dest=", "interval="])
      for opt, arg in opts:
        if opt in ("-h", "--help"):
          usage()
          exit()
        elif opt in ('-s', '--source'):
          global source
          source = open(arg,'r')
        elif opt in ("-d", "--dest"):
          global dest
          dest = open(arg,'w')
    except IOError:
      print "Could not open "+arg
      exit(2)
    except:
      usage()
      exit(2)

  def usage():
    print "'{0}' can be used to edit specific entries in tns formatted files, like tnsnames.ora and listener.ora:".format(argv[0])
    print "'{0}' can be used with the following options:".format(argv[0])
    print "-h, --help, no parameters      : Show this usage info."
    print "-s [source], --source=[source] : The source file that will be read."
    print "-d [dest], --dest=[dest]       : The destination file to wich will be written.\n"
    print "Without a source, input will be read from stdin."
    print "Without a destination, output will be written to stdout."

  from sys import argv, exit, stdin, stdout, stderr
  from getopt import getopt

  source=stdin
  dest=stdout
  read_args()

  tnsfile=TNSConfig(source.read())
#  dest.write(tnsfile.formatted()+'\n')
#  dest.write(tnsfile.__repr__()+'\n')
#  dest.write(str(tnsfile.sub_names())+'\n')
#  for sub in tnsfile:
#    try:
#      stderr.write(sub.name()+'\n')
#    except:
#      pass

