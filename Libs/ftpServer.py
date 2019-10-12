from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from Libs.Threads import Threads
import logging

class ftpServer:
    """
    Create a FTP server

    Args:
        ip         (str) :: ftp server's ip address
        user       (str) :: ftp server's username
        password   (str) :: user's password
        homeDir    (str) :: user's home dir
        permission (str) :: Optional, perm argument is a string referencing the user's,
                            default is 'elradfmw'.These are explained below
                            Read permissions :-
                            - 'e' == change directory (CWD command)
                            - 'l' == list files (LIST, NLST, STAT, MLSD, MLST, SIZE, MDTM commands)
                            - 'r' == retrieve file from the server
                            - 'a' == append data to an existing file
                            - 'd' == delete file or directory (DELE, RMD commands)
                            - 'f' == rename file or directory (RNFR, RNTO commands)
                            - 'm' == create directory (MKDIR command)
                            - 'w' == change file mode (CHMOD)
        port       (int) :: Optional, ftp server's port, default is 21

    Returns:
        returns a FTP server instance

    Example:
        ftp = ftpServer()
        ftp.start()
        ftp.stop()
    """
    def __init__(self, ip, user, password, homeDir, permission='elradfmw', port=21):
        authorizer = DummyAuthorizer()
        authorizer.add_user(user, password, homeDir, permission)
        handler = FTPHandler
        handler.authorizer = authorizer
        self.server = FTPServer((ip, port), handler)
        self.ftpServerTh = None
        self.logger = logging.getLogger(__name__)

    def start(self):
        # Start ftp server
        def __start():
            try:
                self.server.serve_forever()
            except Exception:
                self.logger.warn('Start ftp server %s failed'%(str(self.server.address)))
        self.ftpServerTh = Threads(__start, 'ftp_server')
        self.ftpServerTh.setDaemon(True)
        self.ftpServerTh.start()

    def stop(self):
        # Stop ftp server
        try:
            self.server.close_all()
            self.ftpServerTh.kill()
        except Exception:
            self.logger.error('stop ftp server %s failed'%(str(self.server.address)))

if __name__ == '__main__':
    pass