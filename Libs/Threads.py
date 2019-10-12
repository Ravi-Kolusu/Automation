import threading
import ctypes
import random
import multiprocessing
import traceback
import logging
from Libs.BaseLogger import BaseLogger

class Threads(threading.Thread):
    """
    Custom thread for multi-threaded concurrent execution use cases

    Args:
        threadName (str) :: The name of the thread. The name of the use case is generally passed when the use case is
                            executed
        kwargs           :: The parameters of the callback function, key and value are the names of the callback function
                            paramteres, and the values of callback function parameters
        callback   (fun) :: The function executed in the thread. When the use case is executed, the use case is generally
                            passed to the call interface

    Arguments:
        self.callback (instance) :: Same as the parameter callback
        self.tc       (instance) :: Same as the parameter testcase
        self.errorMsg (str)      :: Used to save the thrown exception information when the use case fails
        thIdList      (list)     :: The thread uniquely identifies the id list
        self.thId     (int)      :: Custom thread unique id identifier, the original thread's own ident will be repeated
                                    by ident, causing log confusion
        self.kwargs   (dict)     :: The parameters of the callback function, key and value are the names of callback
                                    function parameters
        self.ret      (list)     :: When the callback is stored in the ret by the return value, the ret value is None
                                    when there is no return value, and ret is a list when multiple return values

    Returns:
        Thread (instance)  :: Thread object instance

    Example:
        Th = Threads(runTest, tcName, tcObject=tcObj)

    Note:
        1. Support linux, Windows (32 and 64 bit)
    """
    # ID list, used to save the assigned ID, avoiding duplicate thread ID's, resulting in log link confusion
    thIdList = []

    logger = logging.getLogger(__name__)

    def __init__(self, callback, threadName, **kwargs):
        threading.Thread.__init__(self, name=threadName)
        self.thId = random.randrange(1E6)
        while self.thId in Threads.thIdList:
            self.thId = random.randrange(1E6)
        Threads.thIdList.append(self.thId)
        self.callback = callback
        self.kwargs = kwargs
        self.tc = self.kwargs.get('testCase') if self.kwargs.get('testCase') else self.kwargs.get('ratsCase')
        self.errorMsg = ''
        self.released = False
        self.ret = None
        self.dataLocks = []

    def setReleaseFlag(self, flag):
        """
        Set whether the status of release

        Args:
            flag (bool) :: The parameter passed to True when set to release else false
        """
        self.released = flag

    def run(self):
        """
        Thread run function for executing use cases

        Examples:
            Th = Threads(runTest, tcName, tcObject)
            Th.start()
        """
        try:
            self.ret = self.callback(**self.kwargs)
        except Exception:
            self.errorMsg = traceback.format_exc()

    def _raiseExc(self, excObj):
        """
        Terminate the thread

        Args:
            excObj (object type) :: System object type, the default value is SystemExit

        Examples:
            self._raiseExc(SystemExit)
        """
        if not self.isAlive():
            raise Exception('Thread must be started')
        _asyncRaise(self.ident, excObj)

    def kill(self):
        """
        Use SystemExit to exit the thread

        You must throw a SystemExit type object type instead of an instance of SystemExit() after initialization

        Examples:
            Th = Threads(runTest, tcName, tcObject)
            Th.start()
            Th.kill()
        """
        self.logger.info("++++++thread start kill lock")
        for lock in self.dataLocks:
            if lock.locked():
                lock.release()
        self._raiseExc(SystemExit)

    @classmethod
    def waitThreadsComplete(cls, thList):
        """
        Wait for all of the incoming thread object list to end now

        Args:
            thList (List)  :: List of Threads instance objects
        """
        if not isinstance(thList, list):
            raise Exception('Params thList must be list, now thList type is [%s]'%type(thList))
        for th in thList:
            if isinstance(th, Threads):
                if th.isAlive():
                    th.join()
            else:
                cls.logger.warn('The input parameter:[%s], type:[%s], is not Threads'%(th, type(th)))

def _asyncRaise(tid, excObj):
    """
    Use ctypes to call the system exception class and exit the thread

    Args:
        tid    (long)        :: thread ID
        excObj (object type) :: System object type, the default value is SystemExit

    Examples:
        self._asyncRaise(self.ident, excObj)

    Note:
        In a 32-bit system, the thread id is int32. In a 64-bit system, the thread id id long, and the long type is used
        uniformly
    """
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(excObj))
    if res == 0:
        raise Exception('Not existent thread id')
    elif res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)

def MultiOperation(func, iterable, processes=None, chunksize=None):
    """
    Calling func concurrently in the thread pool to process data in the iterator iterable

    Args:
        func      (func)     :: The callback function processed by map
        iterable  (iterable) :: Ietrator, which can be a list
        processes (int)      :: The number of threads that need to be created
        chunksize (int)      :: The iterator's step
    """
    pass

logger = BaseLogger('Threads')

def waitAllThreadComplete(threads):
    """
    Waiting for all threads to complete

    Args:
        threadList (list) :: list of threads
    """
    logger.info('Now just waiting for any object operation thread exit or finished')
    for th in threads:
        if th.release:
            continue
        if th.isAlive():
            th.join()
        __releaseThreadHandle(th)
    errorMsgs = []
    for th in threads:
        if th.errorMsg:
            error = "Thread Id: %s, Thread name: %s\n"%(th.ident, th.name)
            errorMsgs.append(error+th.errorMsg)
    if errorMsgs:
        logger.info('the threads seem got some error when processing...')
        raise Exception('%s'%(errorMsgs))

def __releaseThreadHandle(th):
    """
    Release the handle in the thread

    The handle in python multithreading will only be released when the main thread exits. In the operation, if there is
    no need for message communication after the thread finishes executing

    Args:
        th (threaf handle) :: thread handle
    """
    th._Thread__started._Event__cond = None
    th._Thread__started = None
    th._Thread__stderr = None
    th._Thread__lock = None
    th.additionalInfo = None
    th.setReleaseFlag(True)

if __name__ == '__main__':
    pass


