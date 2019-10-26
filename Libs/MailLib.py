"""
This package contains methods related to receive email and send email
"""
import smtplib
import poplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formatdate
from email import encoders
from email.mime.text import MIMEText
import ssl
from Lib import Log

class Mail(object):
    """
    Used to receive and send mail

    Args:
        None

    Attributes:
          self.logger             (instance)   :: The log object
          self.smtpServer         (str)        :: smtp server address
          self.pop3Server         (str)        :: pop3 server address
          self.loginUsername      (str)        :: The account that logs in to the pmail_osauto account, which is also the sending
                                                  address of the mail
          self.loginPassword      (str)        :: Login to the password of pmail_osauto account
          self.sender             (str)        :: Sender email address
          self.sendEmailServer    (instance)   :: Send an instance of mail server
          self.receiveEmailServer (instance)   :: Receive an instance of mail server

    Returns:
          Mail (instance) :: The mail object instance
    """
    def __init__(self):
        super(Mail, self).__init__()
        self.logger = Log.getLogger(str(self.__module__))
        self.smtpServer = "<smtp address>"
        self.pop3Server = "<pop3 address>"
        self.loginUsername = "username"
        self.loginPassWord = "password"
        self.sender = "xxxx@xxx.com"

    def connectSendServer(self, server, port):
        """
        Connect to the server that send the mail

        Args:
            server (instance) :: smtp server address
            port   (int)      :: smtp server port

        Returns:
              None
        """
        self.logger.info("start to connect server:%s,port:%s"%(server, port))
        try:
            self.sendEmailServer = smtplib.SMTP()
            self.sendEmailServer.connect(server, port)
            self.logger.info("Connect server:%s,port:%s successfully"%(server, port))
        except Exception, connectError:
            self.logger.error("Failed to connect server:%s,port:%s"%(server, port))
            raise connectError

    def loginSendServer(self, userName, password):
        """
        Log in to the server that send the mail

        Args:
            userName (str) :: smtp server login account
            password (str) :: password for smtp server login

        Returns:
              None
        """
        self.logger.info("Start to login")
        try:
            self.sendEmailServer.login(userName, password)
            self.logger.info("Login successfully")
        except Exception, loginError:
            self.logger.error("Failed to login")
            raise loginError

    def sendEmail(self, receiver, sub, content, smtpServer=None, sender=None, file_paths=None, userName=None, password=None, port=25, type='plain'):
        """
        Log into the server that sent the mail

        Args:
            receiver   (list) :: the recipient's account number, ex [xxx@gmail.com]
            sub        (str)  :: the title of the sent message
            content    (str)  :: the content of the sent message
            smtpServer (str)  :: (optional) smtp server address
            sender     (str)  :: (optional) sender email address
            userName   (str)  :: (optional) sender email account
            password   (str)  :: (optional) sender email password
            port       (int)  :: (optional) smtp server port
            type       (str)  :: (optional) content type, optional 'plain', 'html' two formats

        Returns:
              None
        """
        file_paths = [] if file_paths is None else file_paths
        self.server = smtplib.SMTP()
        self.logger.info("Start to send Email")
        if smtpServer is None:
            self.connectSendServer(self.smtpServer, port)
        else:
            self.connectSendServer(smtpServer, port)

        if userName is not None:
            self.loginSendServer(userName, password)
            emailFrom = "<" + sender + ">"
        else:
            self.loginSendServer(self.loginUsername, self.loginPassWord)
            emailFrom = "<" + self.sender + ">"
        self.looger.info("start to send email")
        msg = MIMEMultipart()
        msg['From'] = emailFrom
        msg['To'] = ";".join(receiver)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = sub
        msg.attach(MIMEText(content, _subtype=type))
        for f in file_paths:
            tmp = f.split(os.sep)
            filename = tmp.pop()
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(f, 'rb').read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename=%s'%filename)
            msg.attach(part)
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv3)
        failed = 0
        for everyone in receiver:
            try:
                self.sendEmailServer.sendmail(emailFrom, everyone, msg.as_string())
            except Exception, sendFailed:
                self.logger.error("Send to %s failed, Exception:%s"%(everyone, sendFailed))
                failed += 1
        self.logger.info("The total number of send email is %s ,failed:%s"%(len(receiver), failed))

    def receiveEmail(self):
        pass



