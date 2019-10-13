import ftplib
import re

import logging

class ftpClient:
    """
    Connect Ftp server

    Args:
        ip     (str) :: ftp server ip
        user   (str) :: ftp server username
        passwd (str) :: ftp server password

    Return:
        Ftp client instance

    Example:
        from Lib.ftpClient import ftpClient
        ftp = ftpClient(ip='10.18.18.102', user='root', passwd='password@123')
    """
    def __init__(self, ip, user, passwd):
        self.ftp = ftplib.FTP(ip, user, passwd)
        self.logger = logging.getLogger(__name__)
        #self.logDir = Log.LogFileDir

    def getPackageToLocal(self, ftpPath=None, localPath=None, keyWord=None):
        """
        Get package from remote ftp server to local

        Args:
            ftpPath   (str) :: the relative path of homedir, default homedir
            localPath (str) :: download path of local, default log storage path
            keyWord   (str) :: get the packet matching the remote end and the keyword. If there are multiple,
                               take the first one, and get the first compressed package by default
        Returns:
            localFile (str) :: absolute path of download file

        Example:
            ftp = ftpClient(ip='10.18.18.102', user='root', passwd='password@123')
            ftp.getPackageToLocal(localPath='c:\\testFtp')
            ftp.quit()
        """
        if ftpPath is not None:
            self.ftp.cwd(ftpPath)
        fileList = self.ftp.nlst()
        self.logger.info("There are packages :: %s"%(fileList))
        fileName = None
        if fileList is None:
            raise Exception('There is no package')
        if keyWord is not None:
            for file in fileList:
                if re.search(keyWord, file):
                    fileName = file
                    self.logger.info('To get the package :: %s'%(fileName))
                    break
        else:
            for file in fileList:
                if file.endswith('tgz') or file.endswith('gz') or file.endswith('tar') or file.endswith('zip') or file.endswith('7z'):
                    fileName = file
                    self.logger.info('To get the package :: %s'%(fileName))
                    break
        if fileName is None:
            raise Exception('dont find the package what you want')
        if localPath is not None:
            import os
            localPath = localPath.strip()
            if not os.path.exists(localPath):
                os.makedirs(localPath)
            if localPath.endswith("\\") or localPath.endswith('/'):
                localFile = localPath + fileName
            else:
                localFile = localPath + "\\" + fileName
        else:
            #localFile = self.logDir + "\\" + fileName
            pass
        self.ftp.retrbinary("RETR" + fileName,open(localFile,'wb').write)
        self.logger.info('Get the package to %s successfully'%(localFile))

    def quit(self):
        self.ftp.quit()