#!/bin/python2
#psql -h localhost -p 9876
import SocketServer
import struct
import threading
import time

def char_to_hex(char):
    retval = hex(ord(char))
    if len(retval) == 4:
        return retval[-2:]
    else:
        assert len(retval) == 3
        return "0" + retval[-1]

def str_to_hex(inputstr):
    return " ".join(char_to_hex(char) for char in inputstr)

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        print "handle()"
        self.read_SSLRequest()
        self.send_to_socket("N")

        self.read_StartupMessage()
#        self.send_AuthenticationClearText()
#        self.read_PasswordMessage()
        self.send_AuthenticationOK()
        self.send_ParameterStatus('server_version','9.4')
        self.send_ReadyForQuery()
        Continue, Query = self.read_Query()
        while Continue:
          self.send_queryresult()
          Continue, Query = self.read_Query()
        raise(SystemExit)

    def send_queryresult(self):
        fieldnames = ['Hi', 'Polla']
        HEADERFORMAT = "!cih"
        fields = ''.join(self.fieldname_msg(name) for name in fieldnames)
        rdheader = struct.pack(HEADERFORMAT, 'T', struct.calcsize(HEADERFORMAT) - 1 + len(fields), len(fieldnames))
        self.send_to_socket(rdheader + fields)

        rows = [['You', 'are'], ['an', 'idjit...']]
        DRHEADER = "!cih"
        for row in rows:
            dr_data=''
            for c in row:
                c = str(c)
                frmt='!i{0}s'.format(len(c))
                dr_data += struct.pack(frmt, len(c), c)
            dr_header = struct.pack(DRHEADER, 'D', struct.calcsize(DRHEADER) - 1 + len(dr_data), len(row))
            self.send_to_socket(dr_header + dr_data)

        self.send_CommandComplete()
        self.send_ReadyForQuery()

    def send_CommandComplete(self):
        HFMT = "!ci"
        msg = "SELECT 2\x00"
        self.send_to_socket(struct.pack(HFMT, "C", struct.calcsize(HFMT) - 1 + len(msg)) + msg)

    def fieldname_msg(self, name):
        tableid = 0
        columnid = 0
        datatypeid = 23
        datatypesize = 4
        typemodifier = -1
        format_code = 0 # 0=text 1=binary
        return name + "\x00" + struct.pack("!ihihih", tableid, columnid, datatypeid, datatypesize, typemodifier, format_code)

    def read_socket(self):
        print "Trying recv..."
        data = self.request.recv(1024)
        print "Received {} bytes: {}".format(len(data), repr(data))
        print "Hex: {}".format(str_to_hex(data))
        return data

    def send_to_socket(self, data):
        print "Sending {} bytes: {}".format(len(data), repr(data))
        print "Hex: {}".format(str_to_hex(data))
        return self.request.sendall(data)

    def read_Query(self):
        data = self.read_socket()
        msgident, msglen = struct.unpack("!ci", data[0:5])
        if msgident == "Q":
          print "Query: "+data[5:]
          return True, data[5:]
        elif msgident == "X":
          print "Terminate"
          return False, ''
        else:
          print "Unexpected command."
          return False, ''

    def send_ParameterStatus(self, Name, Value):
        frmt="!ci{0}s{1}s".format(len(Name)+1,len(Value)+1)
        self.send_to_socket(struct.pack(frmt, 'S', len(Name+Value)+6, Name, Value))

    def send_ReadyForQuery(self):
        self.send_to_socket(struct.pack("!cic", 'Z', 5, 'I'))

    def read_PasswordMessage(self):
        data = self.read_socket()
        b, msglen = struct.unpack("!ci", data[0:5])
        assert b == "p"
        print "Password: {}".format(data[5:])


    def read_SSLRequest(self):
        data = self.read_socket()
        msglen, sslcode = struct.unpack("!ii", data)
        assert msglen == 8
        assert sslcode == 80877103

    def read_StartupMessage(self):
        data = self.read_socket()
        msglen, protoversion = struct.unpack("!ii", data[0:8])
        print "msglen: {}, protoversion: {}".format(msglen, protoversion)
        assert msglen == len(data)
        parameters_string = data[8:]
        print parameters_string.split('\x00')

    def send_AuthenticationOK(self):
        self.send_to_socket(struct.pack("!cii", 'R', 8, 0))

    def send_AuthenticationClearText(self):
        self.send_to_socket(struct.pack("!cii", 'R', 8, 3))

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    SocketServer.ThreadingMixIn.daemon_threads = True
    HOST, PORT = "localhost", 9876
    #server = SocketServer.TCPServer((HOST, PORT), ThreadedTCPRequestHandler) #Single threaded...
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    try:
        #Wait until main thread has stopped, or an exception occurs...
        while True:
            time.sleep(10)
        #server.serve_forever() #Single threaded
    except:
        pass
        #server.shutdown()
