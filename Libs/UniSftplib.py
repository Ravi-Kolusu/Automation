import os
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, OPEN_SUCCEEDED

class StubServer(ServerInterface):

    def check_auth_password(self, username, password):
        """
        Authorization authentication, allowing any username and password.
        over write ServerInterface

        Args:
            username (str) :: sftp server username
            password (str) :: sftp server user password

        Returns:
              AUTH_SUCCESSFUL, the identification was successful.
        """
        return AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        """
        After the authentication is successful, the return channel request is successful
        over write ServerInterface
        """
        return OPEN_SUCCEEDED

class StubSFTPHandle(SFTPHandle):
    # over write SFTPHandle
    def __init__(self, flag):
        super(StubSFTPHandle, self).__init__(flag)
        self.readfile = None
        self.filename = None

    def stat(self):
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)

    def chattr(self, attr):
        # python doesn't have equivalents to fchown or fchmod, so we have to use the stored filename
        try:
            SFTPServer.set_file_attr(self.filename, attr)
            return SFTP_OK
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)

class StubSFTPServer(SFTPServerInterface):
    """
    Rewrite SFTPServerInterface, mainly for the root path set by the incoming user
    """
    def __init__(self, server, rootPath):
        """
        Rewrite SFTPServerInterface to get the incoming root path.

        Args:
            rootPath (str) : Set the sftp server root path
        """
        super(StubSFTPServer, self).__init__(server)
        self.rootPath = rootPath

    def _realpath(self, path):
        # over write SFTPServerInterface
        return self.rootPath + self.canonicalize(path)

    def list_folder(self, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            out = []
            fList = os.listdir(path)
            for fName in fList:
                attr = SFTPAttributes.from_stat(os.stat(os.path.join(path, fName)))
                attr.filename = fName
                out.append(attr)
            return out
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            return SFTPAttributes.from_stat(os.stat(path))
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)

    def lstat(self, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            return SFTPAttributes.from_stat(os.lstat(path))
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)

    def open(self, path, flags, attr):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            binary_flag = getattr(os, 'O_BINARY', 0)
            flags |= binary_flag
            mode = getattr(attr, 'st_mode', None)
            if mode is not None:
                fd = os.open(path, flags, mode)
            else:
                # os.open() defaults to 0777 which is an odd default mode for files
                fd = os.open(path, flags, 0666)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        if (flags & os.O_CREAT) and (attr is not None):
            attr._flags &= ~attr.FLAG_PERMISSIONS
            SFTPServer.set_file_attr(path, attr)
        if flags & os.O_WRONLY:
            if flags & os.O_APPEND:
                fstr = 'ab'
            else:
                fstr = 'wb'
        elif flags & os.O_RDWR:
            if flags & os.O_APPEND:
                fstr = 'a+b'
            else:
                fstr = 'r+b'
        else:
            fstr = 'rb'
        try:
            f = os.fdopen(fd, fstr)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        fobj = StubSFTPHandle(flags)
        fobj.filename = path
        fobj.readfile = f
        fobj.writefile = f
        return fobj

    def remove(self, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            os.remove(path)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def rename(self, oldpath, newpath):
        # over write SFTPServerInterface
        oldpath = self._realpath(oldpath)
        newpath = self._realpath(newpath)
        try:
            os.rename(oldpath, newpath)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def mkdir(self, path, attr):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            os.mkdir(path)
            if attr is not None:
                SFTPServer.set_file_attr(path, attr)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def rmdir(self, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            os.rmdir(path)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def chattr(self, path, attr):
        # over write SFTPServerInterface
        path = self._realpath(path)
        try:
            SFTPServer.set_file_attr(path, attr)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def symlink(self, target_path, path):
        # over write SFTPServerInterface
        path = self._realpath(path)
        if(len(target_path)>0) and (target_path[0]=='/'):
            # absolute symlink
            target_path = os.path.join(self.rootPath, target_path[1:])
            if target_path[:2] == '//':
                # bug in os.path.join
                target_path = target_path[1:]
        else:
            # compute relative to path
            abspath = os.path.join(os.path.dirname(path), target_path)
            if abspath[:len(self.rootPath)] != self.rootPath:
                # this symlink isn't going to work anyway -- just break immediately
                target_path = '<error>'
        try:
            os.symlink(target_path, path)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def readlink(self, path):
        ## over write SFTPServerInterface
        path = self._realpath(path)
        try:
            symlink = os.readlink(path)
        except OSError, e:
            return SFTPServer.convert_errno(e.errno)
        # if its absolute, remove the root
        if os.path.isabs(symlink):
            if symlink[:len(self.rootPath)] == self.rootPath:
                symlink = symlink[len(self.rootPath):]
                if (len(symlink)==0) or (symlink[0] != '/'):
                    symlink = '/' + symlink
            else:
                symlink = '<error>'
        return symlink