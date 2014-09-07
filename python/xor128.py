#!/usr/bin/python
def xor128(num,batch):
  x = 123456789
  y = 362436069
  z = 521288629
  w = 88675123
  i = j = 0
  while i<num:
    ret=[]
    while j< batch:
      i+=1
      t = (x ^ (x<<11)) & 0xffffffff
      (x,y,z) = (y,z,w)
      w = (w ^ (w >> 19) ^ (t ^ (t >> 8))) & 0xffffffff
      ret.append(w)
    yield ret

if __name__ == "__main__":
  from sys import stdout
  for i in xor128(2**20,2**10):
    x=str(i)
    stdout.write(str(i))
