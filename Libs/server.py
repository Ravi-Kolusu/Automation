import re
import time
import socket
import paramiko


class server(object):
    def __init__(self, hostip, hostname, password, port):
        self.hostip = hostip
        self.hostname = hostname
        self.password = password
        self.port = port

    def socket_connect(self):
        pass

    def para_connect(self):
        p = paramiko.SSHClient()


