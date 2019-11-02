#!/usr/bin/env python
# -*-coding: utf-*

import threading
from Libs import Log
from Libs.Threads import Threads
from Libs.Exception.CustomExceptions import InvalidParamException
from Libs.Exception.UniAutosException import UniAutosException
from time import time
logger = Log.getLogger('Time')

def _sleep(seconds):
    """Thread sleep operation interface

    This interface is used to replace the sleep function that comes with the thread. After the system comes with
    the sleep function, you cannot call the kill function to kill the thread

    Args:
         seconds (float) :: sleep time, s is the unit

    Examples:
          From Libs.Time import sleep
          sleep(10)
    """
    # simulate sleep using event's timeout mechanism
    if isinstance(seconds, int) or isinstance(seconds, float):
        sleepTimer = threading.Event()
        sleepTimer.wait(timeout=seconds)
        sleepTimer = None
    else:
        raise InvalidParamException("Timeout value [%s], type is %s , it must be int or float."%(seconds, type(seconds)))

def sleep(seconds, segment=60):
    """Segmented sleep is used to monitor the sleep process, avoiding no printing during long sleep, and unable to
    judge whether the operation is normal or not

    Args:
        seconds (float) : total sleep time
        segment (int) : the time of the segment, that is how long to sleep to print log

    Notes:
          if the total sleep time is not an integer divided by the time of the segmentation, it needs to be rounded up
    """
    #  if total sleep time <= 60, will not print log
    if seconds <= 60:
        _sleep(seconds)
        return

    ceilCount = int(seconds/segment)
    lastTime = seconds % segment
    totalCount = ceilCount

    if lastTime > 0:
        totalCount += 1
    count = 0
    while count < ceilCount:
        logger.debug("(%s/%s)%sS, %sS, %sS"%(count+1,
                                             int(totalCount),
                                             seconds,
                                             segment,
                                             ((ceilCount-count)*segment+lastTime)))
        count += 1
    if lastTime > 0:
        logger.debug("(%s/%s)%sS, %sS, %sS"%(count+1,
                                             int(totalCount),
                                             seconds,
                                             segment,
                                             ((ceilCount-count)*segment+lastTime)))
        _sleep(lastTime)

class Timeout(Exception):
    pass

def timeout(seconds):
    """Timeout decorator, specified timeout if the decorated methad does not return within the specified time, throw
    a timeout exception
    """
    def timeout_decorator(func):
        """
        Timeout decorator
        """
        def _new_func(oldFunc, result, oldFuncArgs, oldFuncKwargs):
            result.append(oldFunc(*oldFuncArgs, **oldFuncKwargs))

        def _(*args, **kwargs):
            result = []
            # create new args for _new_func, because we want to get the func return val to return list
            newKwargs = {'oldFunc':func,
                         'result':result,
                         'oldFuncArgs':args,
                         'oldFuncKwargs':kwargs}
            thd = Threads(_new_func, 'timeout', **newKwargs)
            thd.start()
            thd.join(seconds)

            if thd.errorMsg != '':
                raise UniAutosException(thd.errorMsg)
            if thd.isAlive():
                thd.kill()
            if len(result) <= 0:
                raise Timeout('Function [%s] run too long time, timeout %d seconds.'%(func.__name__, seconds))
            else:
                return result[0]
        _.__name__ = func.__name__
        _.__doc__ = func.__doc__
        return _
    return timeout_decorator

def repeat_timeout(logMesg='function repeat running', raiseException=True):
    """
    :param logMesg: (str) the log message you need
    :param raiseException: (bool) if True is to raise the exception, False is not
    :return:
    """
    def decorated(func):
        """
        running the func every interval util the time is bigger than timeout
        the func must return a list, and the first element must be a bool to judge the func is up to expectations
        func (function) :: the function
        """
        def _wrapper(*args, **kwargs):
            """
            :param args:
            :param kwargs: must have timeout and interval parameters
            :return:
            """
            startTime = time()
            _timeout = kwargs.get('timeout', 120)
            _interval = kwargs.get('interval', 10)
            _continue_times = kwargs.get('continue_times', 1)
            cur_times = 0
            while True:
                result = func(*args, **kwargs)
                endTime = time()
                timeSlot = int(endTime-startTime)
                repeatResult = result[0]
                if not isinstance(repeatResult, bool):
                    raise ValueError('###TIMEOUT###The function[%s]return[%s] must be bool'%(func.__name__, result))
                if repeatResult is True:
                    cur_times += 1
                    logger.info('###TIMEOUT###[%sS/%sS][%s]%s is up to expectations, times %s, target times %s'%(timeSlot,
                                                                                                                 _timeout,
                                                                                                                 func.__name__,
                                                                                                                 logMesg,
                                                                                                                 cur_times,
                                                                                                                 _continue_times))
                    if cur_times < _continue_times:
                        sleep(1)
                        continue
                    else:
                        return result
                else:
                    if timeSlot > _timeout:
                        if raiseException:
                            raise ValueError('###TIMEOUT###%s timeout %sS'%(logMesg, _timeout))
                        else:
                            logger.info('###TIMEOUT### %s is finish'%(logMesg))
                            return result
                    else:
                        cur_times = 0
                        logger.info('###TIMEOUT###[%sS/%sS][%s]%s is not upto expectations, wait %sS and run later'%(timeSlot,
                                                                                                                     _timeout,
                                                                                                                     func.__name__,
                                                                                                                     logMesg,
                                                                                                                     _interval))
                        sleep(_interval)
            return _wrapper
        return decorated




