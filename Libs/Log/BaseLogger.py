import threading
import datetime
import cgi
import logging
import re
import traceback
#import LogFormat
import sys, pprint, cStringIO
from enum import Enum

class BaseLogger(object):
    """
    provide a unified log operation interface
    """
    def __init__(self, className, appender=None):
        """
        Args:
            className :: the class name of the class holding the BaseLogger object

        Returns:
            None

        Example:
            Get the logger instance
            Logger = BaseLogger(''ClassName')
        """
        self.className = className
        self.appender = appender

    def _log(self):
        """
        static method to get the logging of the current thread's Appender object

        Args:
            None

        Returns:
              Logger: The underlying Logger encapsulated by the current thread's Appender object.

         Examples:
               Get the logging encapsulated by the appender object of the current threa and print the log
               self._log.log(FileLogLevel.Trace, msg, msg, extra=html)
        """
        if self.appender:
            return self.appender.getLogger()
        if hasattr(threading.currentThread(), 'appender'):
            return threading.currentThread().appender.getLogger()
        else:
            return logging.getLogger()

    def _formatLogMsg(self, level, msg):
        """
        Format the log, dd timestamps and trace

        Args:
            level (int) :: Log level, enumerated type, defined in LogFormat, such as LogFormat.Error
            msg (str) :: Specific log information

        Returns:
            string after formatting

        #TODO :: Need to check LogFormat class
        """
        if level not in FileLoglevel:
            raise Exception('Invalid param')
        parameterDic = {'level': logging.getLevelName(level),
                        'timestamp': datetime.datetime.now().strftime(LogFormat.timeFormat)[0:23],
                        'className': self.className,
                        'threadID': threading.currentThread().ident}
        pattern = re.compile('<a .+>.+</a>', re.I)
        # Escape Html characters if msg does not contain a connection
        if not pattern.search(msg):
            parameterDic['msg'] = cgi.escape(msg)
        else:
            parameterDic['msg'] = msg
        traceList = []
        traceStack = traceback.extract_stack()
        # Reverse order
        traceStack.reverse()
        # Get the line number
        lineNo = traceStack[2][1]
        parameterDic['lineNo'] = lineNo
        # get the call stack information, but need to push two forwards, is the real call to the log module stack
        for trace in traceStack[2:]:
            traceDic = dict(zip(LogFormat.traceDicFormat, trace))
            traceList.append(LogFormat.traceFormat.format(**traceDic))
        trace = '\n'.join(traceList)
        parameterDic['trace'] = trace.replace('', "")
        return unicode(LogFormat.logFormatDic['general'].format(**parameterDic), 'UTF-8', errors='replace')

    def formatException(self):
        try:
            ei = sys.exc_info()
            if None not in ei:
                sio = cStringIO.StringIO()
                traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
                s = sio.getvalue()
                sio.close()
                if s[-1] == '\n':
                    s = s[:-1]
                return s
            else:
                return ""
        finally:
            del ei

    def _formatParameter(self, *args):
        exception = None
        msg = ''
        for parameter in args:
            if isinstance(parameter, Exception):
                exception = parameter
                continue
            elif isinstance(parameter, dict) or isinstance(parameter, list):
                msg += pprint.pformat(parameter)
            elif isinstance(parameter, unicode):
                msg += parameter.encode('UTF-8', errors='replace')
            else:
                msg += str(parameter)
        if exception:
            msg += self.formatException()
        return msg
