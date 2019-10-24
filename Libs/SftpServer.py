import socket
import time
import os
from Threads import Threads
import paramiko
from UniSftplib import StubServer, StubSFTPServer

BACKLOG = 10
KEY_FILE = "server_rsa_key"

class SftpServer(object):
    """
    SFTP server, used to create an SFTP server, upload logs and so on

    Args:
        host     (str) :: server ip address
        port     (str) :: server port
        rootPath (str) :: server root path
        keyFile  (str) :: the default is "server_rsa_key" already provided, you can generate rsa key and pass it.
        level    (str) :: server log level

    Returns:
          Return a sftpserver instance

    Examples:
          sftp = SftpServer('10.18.18.102', 22, "c:\\")
          sftp.start()
          sftp.stop()
    """
    def __init__(self, host, port, rootPath, keyFile=KEY_FILE, level='INFO'):
        self.host = host
        self.port = port
        if keyFile == KEY_FILE:
            self.keyFile = os.path.join(os.path.split(os.path.realpath(__file__))[0], keyFile)
        else:
            self.keyFile = keyFile
        self.level = level
        paramikoLevel = getattr(paramiko.common, self.level)
        paramiko.common.logging.basicConfig(level=paramikoLevel)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self.serverSocket.bind((self.host, self.port))
        self.serverSocket.listen(BACKLOG)
        self.transport = None
        self.th = None
        self.rootPath = rootPath

    def _start(self):
        """
        Real-time monitoring waits for login and user operations
        """
        while True:
            conn, addr = self.serverSocket.accept()
            host_key = paramiko.RSAKey.from_private_key_file(self.keyFile)
            self.transport = paramiko.Transport(conn)
            self.transport.add_server_key(host_key)
            self.transport.set_subsystem_handler('sftp', paramiko.SFTPServer, StubSFTPServer, rootPath=self.rootPath)
            server = StubServer()
            self.transport.start_server(server=server)
            channel = self.transport.accept()
            while self.transport.is_active():
                time.sleep(1)

    def start(self):
        """
        The thread starts the server and runs in the background
        """
        self.th = Threads(self._start, 'sftp')
        self.th.setDaemon(True)
        self.th.start()

    def stop(self):
        """
        stop the server
        """
        if self.transport:
            self.transport.close()
        self.th.kill()

if __name__ == '__main__':
    pass