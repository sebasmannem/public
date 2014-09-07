def __call__(self):
    t = self.x ^ (self.x<<11) & 0xffffffff                   # <-- keep 32 bits
    self.x = self.y
    self.y = self.z
    self.z = self.w
    w = self.w
    self.w = (w ^ (w >> 19) ^(t ^ (t >> 8))) & 0xffffffff    # <-- keep 32 bits
    return self.w

def xor128():
  x = 123456789
  y = 362436069
  z = 521288629
  w = 88675123
  while True:
    t = (x ^ (x<<11)) & 0xffffffff
    (x,y,z) = (y,z,w)
    w = (w ^ (w >> 19) ^ (t ^ (t >> 8))) & 0xffffffff
    yield w

import random

#http://stackoverflow.com/questions/2709818/fastest-way-to-generate-1-000-000-random-numbers-in-python
import numpy
