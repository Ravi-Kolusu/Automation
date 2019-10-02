import paramiko
from paramiko import Transport
from paramiko.ssh_exception import SSHException, AuthenticationException
import time
import threading
import re
import socket
import traceback
import logging
import os

class ssh_connect(object):
    """

    """
    logger = logging.getLogger(__name__)
    def __init__(self, hostname, username, password=None, privateKey=None, port=22):
        self.linesep = '\n'
        self.status = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.privateKey = privateKey
        self.port = port
        self.waitstrDict = None
        self.transport = None
        self.channel = None
        # Thread local varialbes, different threads, independent variables
        self.localParam = threading.local()

    def __del__(self):
        """
        cleanup resources when garbage collection

        Return::
            An sftp object
        """
        self.close()

    def close(self):
        """
        Disconnect the current connection
        """
        if self.transport:
            self.transport.close()
            self.transport = None
            self.channel = None

    def createSFTPClient(self):
        """
        create an SFT channel
        """
        t = self.createClient()
        self.authentication(t)
        sftp = paramiko.SFTPClient.from_transport(t)
        return sftp

    def createClient(self):
        """
        create an SSH connection

        Return::
            Transport: Transfer object
        """
        t = None
        count = 0
        event = threading.Event()
        while count < 3:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.hostname, self.port))
                t = Transport(sock)
                t.start_client(event)
                event.wait(10)
                if not event.is_set():
                    self.logger.warn("start client timeout")
                if not t.is_active():
                    raise Exception("start client error")
                break
            except(socket.error, EOFError, paramiko.SSHException) as e:
                self.logger.warn(e, 'host: %s:%s connection failed'%(self.hostname, self.port))
                count += 1
                sock.close()
                time.sleep(3)
        else:
            raise Exception("Create connect to %s failed"%self.hostname)
        return t

    def authentication(self, transport):
        """
        Authentication

        Args:
            Transport object
        """
        if not transport.is_authenticated():
            if self.privateKey:
                self.auth_public_key(transport)
            elif self.password is not None:
                try:
                    self.auth_password(transport)
                except paramiko.BadAuthenticationType as error:
                    if 'keyboard-interactive' not in error.allowed_types:
                        raise self.auth_interactive(transport)
        self.logger.debug("login success")

    def auth_interactive(self, transport):
        """
        try keyboard interactive authentication type
        """
        self.logger.debug('try keyboard interactive authentication type')
        password = self.password
        def handler(title, instructions, fields):
            if len(fields) > 1:
                raise SSHException('Fallback authentication failed')
            if len(fields) == 0:
                return []
            return [password]
        my_event = threading.Event()
        transport.auth_handler = paramiko.AuthHandler(transport)
        transport.auth_handler.auth_interactive(self.username, handler, my_event, "")
        my_event.wait(120)
        if not my_event.is_set():
            self.logger.warn('Authenticate timeout')
        if not transport.is_authenticated():
            error = transport.get_exception()
            if error is None:
                error = AuthenticationException('Authentication failed')
            raise error

    def auth_password(self, transport):
        self.logger.debug('try keyboard interactive authentication type')
        my_event = threading.Event()

        self.logger.debug('login IP:%s username:%s password:%s'%(self.hostname, self.username, self.password))
        transport.auth_password(self.username, self.password, my_event)
        my_event.wait(120)
        if not my_event.is_set():
            self.logger.warn('authentication timeout, ip:%s, user:%s, password:%s'%(self.hostname, self.username, self.password))
        if not transport.is_authenticated():
            error = transport.get_exception()
            if error in None:
                error = AuthenticationException('Authentication failed')
            raise error

    def auth_public_key(self, transport):
        self.logger.debug('try keyboard interactive authentication type')
        my_event = threading.Event()
        try:
            key = paramiko.RSAKey.from_private_key_file(self.privateKey)
        except SSHException:
            key = paramiko.DSSKey.from_private_key_file(self.privateKey)
        self.logger.debug('login IP:%s username:%s privateKey:%s'%(self.hostname, self.username, self.privateKey))
        transport.auth_publickey(self.username, key, my_event)
        my_event.wait(120)
        if not my_event.is_set():
            self.logger.warn('authentication timeout, ip:%s user:%s privateKey:%s'%(self.hostname, self.username, self.privateKey))
        if not transport.is_authenticated():
            error = transport.get_exception()
            if error is None:
                error = AuthenticationException('Authentication failed, privateKey: %s'%self.privateKey)
            raise error

    def send(self, cmd, timeout=120):
        """
        Issue the actual commands that need to be executed on the device

        Args:
            cmd (str) :: the command to be executed
            timeout (int) :: The time to wait for the connection state to execute the command

        Return:
            True/False: command successfully sent return True
                        command delivery fails return False
        """
        nowTime = time.time()
        endTime = nowTime + timeout
        channel = self.channel
        while nowTime < endTime:
            try:
                channel.send(cmd + self.linesep)
                self.logger.debug('host:%s, send cmd:%s'%(self.hostname, cmd))
                return True
            except socket.timeout as e:
                self.logger.warn(e, 'execute cmd: %s timeout'%cmd,)
            nowTime = time.time()
        return False

    def recv(self, waitstr="[>#]", nbytes=None, timeout=120, lastSendData=None):
        """
        Receive the command output after the command is sent

        Args:
            waitstr (str) :: echo information end character
            nbytes (int) :: the maximum amount of echo information reveiced each time
            timeout (int) :: the longest time to wait for the echo to be received

        Return:
              Result :: Returns the echo information after the command is executed. If the command fails to be sent
                        or the echo information is not returned, the user returns again
                        - You need to call the connect method to reestabilish the connection before issuing the command
              isMatch :: whether to match the echo end symbol
              matchStr :: matching echo end character
        """
        if not self.isActive():
            raise Exception('connection has been closed')
        isMatch = False
        matchStr = None
        recv = ""
        nowTime = time.time()
        endTime = nowTime + timeout
        channel = self.channel
        warnmsg = ""
        while nowTime < endTime:
            strGet = ""
            match = None
            try:
                strGet = channel.recv(nbytes)
            except socket.timeout:
                if not warnmsg:
                    warnmsg = 'echo is not received'
                    self.logger.warn(warnmsg)
            if strGet is not "":
                recv += strGet
                match = re.search(waitstr, recv)
            if match:
                isMatch = True
                matchStr = match.group()
                break
            nowTime = time.time()
        self.logger.debug("DEVICE INFO:\n%s"%recv)
        p = re.compile(r'\x1b\[(?:\d{1,2};)?\d{0,2}m')
        recv = p.sub("", recv)
        if recv == "":
            recv = None
        return recv, isMatch, matchStr

    def isActive(self):
        """
        Determine if the current connection is disconnected
        """
        if self.channel:
            return not self.channel.closed
        return False

    def login(self):
        """
        Landing device
        """
        if self.transport is None or not self.transport.is_active():
            t = self.createClient()
            self.transport = t
        self.authentication(self.transport)
        channel = self.transport.open_session()
        channel.get_pty(width=200, height=200)
        channel.invoke_shell()
        channel.settimeout(10)
        self.channel = channel
        result, isMatch, matchStr = self.recv(timeout=5)
        if not isMatch:
            self.logger.warn('Has not got the command prompt yet as this connection')
        defaultWaitStr = '@#>'
        self.execCommand('<cmd>', waitstr='root'+ defaultWaitStr, timeout=5)
        self.waitstrDict = {'normal':defaultWaitStr}
        self.status = 'normal'

    def execCommand(self, cmd, waitstr="[>#]", timeout=120, nbytes=32768):
        """
        Send commands to the array and get the echo information

        Args:
            cmd (str) :: command to get executed
            waitstr(str) :: end character when the command is executed after the echo is executed
            timeout (int) :: command execution timeout

        Return:
              Result :: Returns the echo information after the command is executed. If the command fails to be sent
                        or the echo information is not returned, the user returns again
                        - You need to call the connect method to reestabilish the connection before issuing the command
              isMatch :: whether to match the echo end symbol
              matchStr :: matching echo end character
        """
        if not self.send(cmd, timeout):
            return None
        result, isMatch, matchStr = self.recv(waitstr, nbytes, timeout, lastSendData=cmd)
        return result, isMatch, matchStr

    def cmd(self, cmdSpec):
        defaultwaitstr = self.waitstrDict.get('normal', '[#|>]')
        result = {'rc':None, 'stderr':None, 'stdout':''}
        if "directory" in cmdSpec:
            tmpresult, isMatch, matchStr = self.execCommand('cd'+cmdSpec['directory'], defaultwaitstr)
            if tmpresult is None:
                result['stdout'] = None
                return result
            result['stdout'] += tmpresult
        timeout = cmdSpec.get('timeout', 600)
        waitstr = cmdSpec.get('waitstr', defaultwaitstr)

        cmdstr = " ".join(cmdSpec['command'])
        cmdstr = re.sub('^sh -c', "", cmdstr)
        cmdList = []
        cmdList.append([cmdstr, waitstr])
        if cmdSpec.get('input'):
            inputLen = len(cmdSpec['input'])
            for i in range(0, inputLen, 2):
                wStr = cmdSpec['input'][i+1] if (i+1)!= inputLen else defaultwaitstr
                cmdList.append([cmdSpec['input'][i], wStr])
        stdout = ""
        for cmd in cmdList:
            tmpresult, isMatch, matchStr = self.execCommand(cmd[0], cmd[1]+'|'+defaultwaitstr, timeout)
            if tmpresult:
                stdout += tmpresult
        stdlist = stdout.split('\r\n')
        if stdlist[0] == cmdstr:
            stdlist.pop(0)
        if stdlist[-1] == defaultwaitstr:
            stdlist.pop(-1)
        result['rc'] = self.__lastCmdStatus()
        if result['rc'] == 0:
            result['stdout'] = '\r\n'.join(stdlist)
            result['stderr'] = None
        else:
            result['stderr'] = '\r\n'.join(stdlist)
            result['stdout'] = None
        return result

    def __lastCmdStatus(self):
        defaultwaitstr = self.waitstrDict.get('normal', '[#|>]')
        result = self.execCommand('echo $?', defaultwaitstr, timeout=3)[0]
        if result:
            l = result.split('\r\n')
            if 'echo $?' in l:
                ind = l.index('echo $?')
                if l[ind+1].isdigit():
                    return int(l[ind+1])
        return None

    def reconnect(self):
        """
        Reconnection
        """
        self.close()
        self.login()

    def getFile(self, src, dst):
        """
        download file

        Args:
            src(str) :: remote file path
            dst(str) :: local file path

        Return:
              True/False

        Example:
              ssh = ssh_connect("10.18.18.102", 'root', 'ravi@123')
              ssh.getFile("/home/file.sh", "D:/ftp/get/file.sh")
        """
        sftp = self.createSFTPClient()
        self.localParam.rate = 0
        try:
            sftp.get(src, dst, self.callback)
        except Exception:
            self.logger.warn('file transfer failed')
            return False
        finally:
            sftp.close()
        return True

    def downloadFile(self, remote, local):
        """
        Download all files in a file or folder

        Args:
            remote(str) :: remote file path
            local(str) :: local file path

        Return:
              True/False

        Example:
              ssh = ssh_connect("10.18.18.102", 'root', 'ravi@123')
              ssh.downloadFile("/home/file.sh", "D:/ftp/get/file.sh")
        """
        sftp = self.createSFTPClient()
        try:
            if os.path.isdir(local):
                file_list = sftp.listdir(remote)
                if len(file_list) != 0:
                    for file in sftp.listdir(remote):
                        self.localParam.rate=0
                        sftp.get(os.path.join(remote+file), os.path.join(local+file), self.callback())
                else:
                    self.localParam.rate = 0
                    sftp.get(remote, local, self.callback())
        except Exception as e:
            self.logger.error('Download file exception : %s'% e)
            return False
        finally:
            sftp.close()
        return True

    def callback(self, sended, total):
        """
        File transfer callback function, which allows users to visually see the progress of file transfer

        Return:
            sended (int) :: No of bytes the file has been transferred
            total (int) :: total file size in bytes
        """
        i = (round(sended)/round(total))*100
        if i-self.localParam.rate < 1:
            return
        self.localParam.rate = i

        self.logger.info("file size: %dB, send: %dB, rate:%d"%(total, sended, i))
        if sended == total:
            self.logger.info('File transfer success')
