import codecs
import threading
import os
import json

class SimpleLogger(object):
    def __init__(self, filename):
        self.lock = threading.RLock()
        self.logfileName = filename
        self.isFirst = True

    def logTestCaseStatus(self, **kwargs):
        self.lock.acquire()
        try:
            json.dumps(kwargs)
        except TypeError:
            if kwargs.get('reason'):
                kwargs['reason'] = 'fail reason is too large, please check case detail'
            if kwargs.get('post'):
                kwargs['post'] = 'fail reason is too large, please check case detail'
        try:
           stream = self._open()
           try:
               if self.isFirst:
                   stream.write('var TCStatus = [')
                   stream.write(json.dumps(kwargs))
                   stream.write(']')
                   self.isFirst = False
               else:
                   stream.seek(-1, os.SEEK_END)
                   stream.truncate()
                   stream.write(',')
                   stream.write(json.dumps(kwargs))
                   stream.write(']')
           finally:
               self._flush(stream)
        finally:
               self.lock.release()

    def _open(self):
        stream = codecs.open(self.logfileName, mode='a', encoding='UTF-8')
        return stream

    def _flush(self, stream):
        stream.flush()
        stream.close()
