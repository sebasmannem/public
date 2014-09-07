#!/usr/bin/python
from Crypto import Random
from Crypto.Cipher import AES
import base64
import hashlib

BS = 32
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
unpad = lambda s : s[0:-ord(s[-1])]

class AESCipher:
    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv )
        return base64.b64encode( iv + cipher.encrypt( raw ) ) 

    def decrypt( self, enc ):
        enc = base64.b64decode(enc)
        iv = enc[:BS]
        cipher = AES.new(self.key, AES.MODE_CBC, iv )
        return unpad(cipher.decrypt( enc[BS:] ))

def doit():
  m = hashlib.md5()
  m.update('blaat'.encode('utf-8'))
  cphr=AESCipher(m.digest())
  for i in range(1):
    cphr.encrypt(" "*2**30)

if __name__ == "__main__":
  doit()
