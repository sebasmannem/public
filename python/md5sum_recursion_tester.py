#!/bin/python

if __name__ == "__main__":
  from sys import argv, exit, stdin, stdout, stderr
  from hashlib import md5
  if len(argv) < 2:
    print('Sorry, maar ik heb een seed nodig')
    exit(1)
  tested=set()
  tested_big=set()
  m=md5()
  seed = argv[1]
  i=1
  while seed not in tested and seed not in tested_big:
    print('{0}: {1}'.format(i,seed))
    tested.add(seed)
    if len(tested) > 100000:
      tested_big.add(seed)
      tested.clear()
    m.update(seed.encode('utf-8'))
    seed = m.hexdigest()
    i+=1
  print('Found recursion after {0} times.'.format(i))
  print('{0}: {1}'.format(i,seed))
