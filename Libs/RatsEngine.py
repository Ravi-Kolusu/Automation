#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 用于测试用例控制，测试用例执行，为并发循环执行用例的控制提供接口定义.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015.

修改记录: 2015/5/25 胡伟 90006090 created

"""

import threading
import hashlib
import sys
import time
import re
import datetime
import traceback
import copy
import random
from UniAutos import Log
from UniAutos.TestEngine.Engine import Engine
from UniAutos.TestEngine.RatsCase import RatsCase
from UniAutos.TestEngine.Group import Group
from UniAutos.Exception.UnsupportedException import UnsupportedException
from UniAutos.Exception.DictKeyException import DictKeyException
from UniAutos.Exception.HookException import HookException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.Units import Units, SECOND
from UniAutos.Util.Threads import Threads
from UniAutos.TestEngine.Configuration import Configuration
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Util.TestStatus import TEST_STATUS


class RatsEngine(Engine):
"""并发循环执行用例引擎

Args:
engineParam (dict): 测试引擎参数， 包含测试套对象、测试引擎在主配置文件中的配置数据.

Attributes:
self.recordComponents (dict) : 记录的component.
self.allowNewTestFlag (bool) : 是否运行执行新用例的标记.
True: 允许.
False: 不允许.
self.rescanIoHostsReq (bool) : 重新扫描IO主机的请求.
self.hosts (list) : 保存当前设备配置的主机对象列表.
self.ioLock (dict) : key为主机IP, value为锁对象的字典, 用于主机IO的锁定.
self.duration (str) : 测试运行的时长, 单位为S.
self.runningTestCases (dict) : 正在运行的测试用例.
self.isRescanning (bool) : 是否正在扫描主机的标记.
self.durationExpired (bool) : 标识测试的时长是否已经超过定义的测试最大时间.
self.ratsTcStatus (dict) : 记录ratsCase的全局状态.
self.noKillRatsThreads (dict) : 不允许kill的用例.
self.tcNameToThread (dict) : 测试用例名字和线程的对应关系.
self.ratsSuspend (dict) : 记录用例暂停的信息.
self.timeSinceLastStatus (str) : 最后一次更新用例状态的时间, 用例延时处理.
self.controllerLogFile (str) : Engine日志文件的文件名头.

Returns:
RatsEngine (instance): RatsEngine对象.
"""

def __init__(self, engineParam):
super(RatsEngine, self).__init__(engineParam)
self.recordComponents = {}
self.recordComponentsLock = threading.Lock()
self.allowNewTestFlag = True
self.rescanIoHostsReq = False
self.hosts = []
self.ioLock = {}
self.duration = None
self.runningTestCases = {}
self.isRescanning = False
self.durationExpired = False
self.ratsTcStatus = {} # 记录ratsCase的全局状态.
self.noKillRatsThreads = {}
self.tcNameToThread = {} # 测试用例名字和线程的对应关系.
self.ratsSuspend = {}
self.timeSinceLastStatus = None
self.controllerLogFile = "Controller"
self.checkIsRatsTests()
self.ratsEngine = True

@staticmethod
def _removeDeadThread(threadList=None, th=None):
"""检查测试用例线程列表中的线程是否存活，不存活的被移除.

Args:
threadList (list): 线程列表.

"""

__threads = []
if th is None and threadList:
for key in threadList:
if not key.isAlive():
__threads.append(threadList.pop(threadList.index(key)))
if th and threadList and th in threadList:
__threads.append(threadList.pop(threadList.index(th)))
return __threads

def _cloneTestObject(self, tc):
"""复制即将运行的测试用例对象

复制即将运行的测试用例对象，并赋予不同的名称. 因为测试对象可能会运行多次，记录的日志名称也会不同.

Args:
tc (instance): 测试用例对象.

Returns:
cloneTestCase (instance): 修改测试用例名称，克隆后的测试用例对象.

Examples:
cloneTc = self._cloneTestObject(tc)
"""
# 测试用例对象执行次数加1, 设置克隆用例对象的名称.
tc.incrementRunNumber()
cloneTestName = tc.name + "-" + str(tc.runNumber)

tcParam = {"name": cloneTestName,
"location": tc.path,
# "params": newParams,
"instance_id": tc.instanceId,
"identities": tc.identities,
# "dependencies": tc.dependencies,
"order": tc.order,
"resource": tc.resource,
"description": tc.description,
"tags": tc.tags,
"engine": self,
"templateId": tc.templateId,
"base": tc,
"required_equipment": tc.requiredEquipment,
"shareable_equipment": tc.shareableEquipment,
"steps_to_perform": tc.testSteps}

# 创建克隆对象.
__import__(tc.casePackageName)
tcClone = getattr(sys.modules[tc.casePackageName], tc.__class__.__name__)(tcParam)
tcClone.parameters = copy.deepcopy(tc.parameters)
return tcClone

def _killRatsThread(self, th):
"""杀掉指定的线程
当用例执行失败需要杀死线程时，指定线程执行.
Args:
th (instance): 线程对象.
"""

# 杀死线程前获取线程对应的测试用例并设置状态为KILLED.
ratsName = self.getRatsTcNameFromTid(th.thId)
status = TEST_STATUS.KILLED \
if th.tc.caseStatus not in [TEST_STATUS.FAILED,
TEST_STATUS.CONFIG_ERROR,
TEST_STATUS.NOT_RUN] else th.tc.caseStatus
if ratsName:
self.logger.info("Killing Module %s. " % ratsName)
self.ratsTcStatus[ratsName]["status"] = status
self.ratsTcStatus[ratsName]["end_time"] = time.time()
else:
self.logger.info("Killing Thread Id %s." % th.ident)

# 杀死线程.
if th.isAlive() and th.tc:
self.killTestThread(th.tc, th)
self.releaseThreadHandle(th)

else:
self.logger.debug("Thread %s already terminated by itself, collecting status..." % th.ident)
self._checkThreadStatus(th)

# 每个用例被杀死时需要记录结果到result.html中.
Log.TestCaseStatusLogger.logTestCaseStatus(name=th.tc.name,
status=status,
start=th.tc.startTime,
# 结束时间就是当前的时间.
end=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
# 如果当前用例是被kill的不需要原因，如果被kill前就已经失败或者成功，就使用
# case原有的原因.
reason=th.tc.baseCaseObject.failureReason
if status not in [TEST_STATUS.COMPLETE,
TEST_STATUS.CONFIGURED,
TEST_STATUS.DE_CONFIGURED,
TEST_STATUS.PASS] else '',
tmss_id=th.tc.getTmssId(),
post='',
times=th.tc.baseCaseObject.runNumber)

@staticmethod
def setThreadError(errorMsg):
"""设置让前线程的错误信息
Args:
errorMsg (Exception): 用例线程执行错误的信息.
"""
if hasattr(threading.current_thread(), "errorMsg"):
threading.current_thread().errorMsg += str(errorMsg)
return

def _runRatsTest(self, ratsCase):
"""运行测试用例内容.

Args:
ratsCase (RatsCase|Group): 指定运行的测试用例对象.
"""
# ratsCase = ratsCaseDict.get("tcObject")
tid = threading.current_thread().thId
self.ratsSuspend[tid] = {"semaphore": threading.Semaphore(),
"state": TEST_STATUS.RUNNING}
# 设置测试用例日志.
tcLogFile = ratsCase.name
_uuid = Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
self.tidToTcLogs[tid] = tcLogFile + "---0" # "---0" 日志文件过大后分片的标志， 默认第一分片加上.
self.tcNameToThread[ratsCase.name] = threading.current_thread()

# 打印用例详细信息日志.
ratsCase.logCaseDetailInfo()
ratsCase.logParameter()

# 设置用例初始状态.
postReason = ''
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.RUNNING)
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.RUNNING)
ratsCase.setCaseStatus(TEST_STATUS.RUNNING)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.RUNNING

# 2015/09/28 h90006090 Add test case startTime use to tmss fillback.
_start = datetime.datetime.now()
_startTime = _start.strftime('%Y-%m-%d %H:%M:%S')
ratsCase.baseCaseObject.setStartTime(_startTime)
ratsCase.setStartTime(_startTime)
Log.TestCaseStatusLogger.logTestCaseStatus(name=ratsCase.name,
status=TEST_STATUS.RUNNING,
start=_startTime,
end=_startTime,
reason=ratsCase.failureReason
# 2017/05/25 h90006090
# fix http://10.183.61.55/oceanstor-autotest/UniAutos/issues/1541
if ratsCase.caseStatus not in [TEST_STATUS.COMPLETE,
TEST_STATUS.CONFIGURED,
TEST_STATUS.DE_CONFIGURED,
TEST_STATUS.PASS] else '',
tmss_id=ratsCase.getTmssId(),
post=postReason,
times=ratsCase.baseCaseObject.runNumber)
# 记录数据到数据库中.
# _uuid = hashlib.new('md5', Log.LogFileDir + ratsCase.name).hexdigest()
ratsCase.statusUuid = _uuid
_dbStatus = {
'_uuid': ratsCase.statusUuid,
"_stage": 'running',
"_post_status": TEST_STATUS.NOT_RUN,
"_status": TEST_STATUS.RUNNING,
"_start": _start,
"_log_file": tcLogFile,
'_duration': '0S',
"_what": 'case',
"_id": self._getIdentityOfTest(ratsCase),
"_name": ratsCase.baseCaseObject.name,
"_round": ratsCase.baseCaseObject.runNumber,
"_base_status": ratsCase.baseCaseObject.caseStatus
}
self.statusDb.save(**_dbStatus)

# 执行PreTestCase.
_preTestPassFlag = False
try:
# self.runHooks('beforePreTest')
ratsCase.preTestCase()
except Exception, preErrorMsg:
self.logger.fail(preErrorMsg)
self.setThreadError(preErrorMsg)
ratsCase.setCaseStatus(TEST_STATUS.CONFIG_ERROR)
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.CONFIG_ERROR)
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.CONFIG_ERROR)
ratsCase.baseCaseObject.setFailureReason("Failed Reason is: %s " % preErrorMsg)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.CONFIG_ERROR # 及时更新Case的状态.
self.logger.fail("%s Pre Test has Failed: \n %s \nThread Id: %s"
% (ratsCase.name, preErrorMsg, threading.current_thread().ident))
else:
_preTestPassFlag = True

# 执行procedure(), 测试主体.
if _preTestPassFlag:
try:
ratsCase.procedure()
if isinstance(ratsCase, Group) and ratsCase.groupError:
raise UniAutosException(
'Group: %s have some case executed error, please check detail in case log.' % ratsCase.name)

except Exception, errorMsg:
self.logger.fail(errorMsg)
self.setThreadError(errorMsg) # 设置当前线程的error信息.
ratsCase.setCaseStatus(TEST_STATUS.FAILED) # 设置当前clone的用例对象的状态.
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.FAILED) # 设置clone的用例对象的源对象的状态.
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.FAILED)
ratsCase.baseCaseObject.setFailureReason("Failed Reason is: %s " % errorMsg)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.FAILED # 及时更新Case的状态.
self.logger.fail("%s Procedure Test has Failed:\n %s\nThread Id: %s"
% (ratsCase.name, errorMsg, threading.current_thread().ident))

else:
ratsCase.logger.passInfo("%s Main Test has Passed" % ratsCase.name)
ratsCase.setCaseStatus(TEST_STATUS.PASS)
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.PASS)
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.PASS)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.PASS # 及时更新Case的状态.

# 执行PostTestCase.
try:
self.logger.info("Running PostTestCase (if Exists)")
# h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
ratsCase.setPostStatus(TEST_STATUS.RUNNING)
ratsCase.postTestCase()
self.runHooks("afterPostTest", tc=ratsCase)
except Exception, postErrorMsg:
postReason = postErrorMsg.message
self.logger.fail("RatsCase PostTestCase() Failed:\n %s\nThread Id: %s"
% (postErrorMsg, threading.current_thread().ident))
# h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
ratsCase.setPostStatus(TEST_STATUS.FAILED)
self.setThreadError(postErrorMsg)
self.decRunningRatsCase(ratsCase)
self.recordRatsCaseCompleteWithComponent(ratsCase)
# 2015/09/30 h90006090 增加测试单次结束时间
ratsCase.baseCaseObject.setEndTime(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
if not isinstance(postErrorMsg, HookException):
self.runHooks("afterPostTest", tc=ratsCase)
_postUpdateStatus = {
'_post_status': TEST_STATUS.FAILED,
}
else:
self.logger.info("%s Post Test has Passed" % ratsCase.name)
self.logger.info("%s Test has Complete." % ratsCase.name)
self.decRunningRatsCase(ratsCase)
self.recordRatsCaseCompleteWithComponent(ratsCase)
_postUpdateStatus = {
'_post_status': TEST_STATUS.PASS,
}
_datetimeEnd = datetime.datetime.now()
_timeEnd = time.time()
_postUpdateStatus.update({
'_stage': 'done',
'_duration': str(_timeEnd - self.ratsTcStatus[ratsCase.name]['start_time']) + 'S',
'_end': _datetimeEnd,
'_base_status': ratsCase.baseCaseObject.caseStatus,
'_status': ratsCase.caseStatus
})
self.statusDb.update(ratsCase.statusUuid, **_postUpdateStatus)
ratsCase.logger.tcEnd()
self.ratsTcStatus[ratsCase.name]["end_time"] = _timeEnd

# 2015/09/30 h90006090 增加测试单次结束时间
ratsCase.setEndTime(_datetimeEnd.strftime('%Y-%m-%d %H:%M:%S'))
ratsCase.baseCaseObject.setEndTime(_datetimeEnd.strftime('%Y-%m-%d %H:%M:%S'))
Log.TestCaseStatusLogger.logTestCaseStatus(name=ratsCase.name,
status=ratsCase.caseStatus,
start=ratsCase.baseCaseObject.startTime,
end=ratsCase.baseCaseObject.endTime,
reason=ratsCase.baseCaseObject.failureReason
# 2017/05/25 h90006090
# fix http://10.183.61.55/oceanstor-autotest/UniAutos/issues/1541
if ratsCase.caseStatus not in [TEST_STATUS.COMPLETE,
TEST_STATUS.CONFIGURED,
TEST_STATUS.DE_CONFIGURED,
TEST_STATUS.PASS] else '',
tmss_id=ratsCase.getTmssId(),
post=postReason,
times=ratsCase.baseCaseObject.runNumber)

Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)
# 测试用例执行完成后才增加执行次数，没有对测试最大次数进行限制时也进行增加，但是不生效.
ratsCase.baseCaseObject.numberOfExecuted += 1
# 释放克隆的用例对象内存, 释放打开的日志文件句柄.
ratsCase.baseCaseObject.canRunExecFlag = True
del ratsCase

def _checkThreadStatus(self, th, errorMsgs=None):
"""检查线程的状态
Args:
th (thread handle): 线程句柄.
errorMsgs (str): 由上层接口传入的线程的错误信息, 默认为空.
"""
if not errorMsgs:
errorMsgs = []
if isinstance(errorMsgs, str):
errorMsgs = [errorMsgs]
ratsName = self.getRatsTcNameFromTid(th.thId)

# 无判断是否可以join的接口，使用isAlive()接口判断线程是否消亡，
# 并在处理后从currentRunningTestThreads移除已经消亡的线程，避免多次处理.
if not th.isAlive():
if th.errorMsg:
self.logger.error("RatsCase %s Failed and reported an error:\n%s\nThread Id:%s"
% (ratsName, th.errorMsg, th.ident))
errorMsgs.append(th.errorMsg)
if ratsName:
self.ratsTcStatus[ratsName]["status"] = TEST_STATUS.FAILED
self.ratsTcStatus[ratsName]["message"] = th.errorMsg
self.ratsTcStatus[ratsName]["end_time"] = time.time()
else:
if ratsName:
self.logger.info("RatsCase %s finished running and passed" % ratsName)
self.ratsTcStatus[ratsName]["status"] = TEST_STATUS.PASS
self.ratsTcStatus[ratsName]["message"] = None
self.ratsTcStatus[ratsName]["end_time"] = time.time()
self._removeDeadThread(self.currentRunningTestThreads, th)
pass

def createNewTestThread(self, tmpRatsCases):
"""遍历测试用例对象检查对象的状态，检查结果为真，对该测试用例对象再次启动线程，运行测试用例.
Args:
tmpRatsCases (list): 测试套中的用例对象列表.
"""
spawnedAtLeastOne = False
parameters = self.testSet.getParameter()
if parameters.get('random', False):
random.shuffle(tmpRatsCases)
for tc in tmpRatsCases:
self.checkRatsCasesStatus()
# 如果当前用例执行的次数达到最大次数， 将不再执行.
if tc.totalNumberOfExec is not None and tc.numberOfExecuted >= tc.totalNumberOfExec:

if tc.debugSwitch:
self.testSet.reachedMaximumTcNumber += 1
# 日志只打印一次, 并记录测试套达到最大次数的用例个数。
self.logger.info("Can not Run Test Case[%s], Because Reached the maximum number[%s] "
"of executions." % (tc.name, tc.numberOfExecuted))
tc.debugSwitch = False
continue
if self.rescanIoHostsReq:
self.rescanHosts()

if (time.time() - self.timeSinceLastStatus) > 300:
self.reportStatus()
self.timeSinceLastStatus = time.time()

cloneTestCase = self._cloneTestObject(tc)
# 设置clone对象的测试套.
cloneTestCase.setTestSet(tc.testSet)
canRun = False
if self.allowNewTestFlag:
self.logger.info("Ready to running canRun() for %s" % tc.name)
try:
if not self.isRunning(tc):
tc.canRunExecFlag = False
self.logger.info("Running canRun() for %s" % tc.name)
canRun = cloneTestCase.canRun()
if not canRun:
tc.canRunExecFlag = True
self.logger.info("canRun() for %s complete." % tc.name)
else:
self.logger.info("Can not Running canRun() for %s, Test Case is Running now." % tc.name)
except Exception, errorMsg:
self.logger.error("RatsCase %s canRun() method threw an exception:\n%s, %s"
% (cloneTestCase.name, errorMsg, traceback.format_exc()))
self.checkRatsCasesStatus(str(errorMsg))
tc.canRunExecFlag = True

# 2017-4-18 h90006090 decrementRunNumber if can not be run.
if not canRun:
self.logger.debug("Test case: %s can not be run, delete clone test case and decrement "
"run number of test case." % tc.name)
tc.decrementRunNumber()

# if canRun and not self.isRunning(tc):
if canRun:
self.checkRatsCasesStatus()
self.incRunningRatsCase(tc)
time.sleep(1)

# 复制对象用于记录测试的名字
baseName = tc.name[:]
# cloneTestCase = self._cloneTestObject(tc)
self.ratsTcStatus[cloneTestCase.name] = {'status': TEST_STATUS.NOT_RUN,
"start_time": time.time(),
"end_time": time.time(),
"base": baseName,
"tid": None,
"max_runtime": cloneTestCase.maxRunTime,
'message': None} # 赋初始值.

# 新起一个线程执行用例对象
th = Threads(self._runRatsTest, cloneTestCase.name, ratsCase=cloneTestCase)
th.start()
self.incrementTestCounter()
self.currentRunningTestThreads.append(th)
self.logger.info("Wait test case create log file, if hung on, please call automation support staff.")
while th.thId not in self.tidToTcLogs:
time.sleep(1)
link = "%s" \
% (self.tidToTcLogs[th.thId], self.tidToTcLogs[th.thId])

self.logger.info("Starting RatsCase:%s \nUnique ID:%s \nThread ID: %s \n %s"
% (baseName, cloneTestCase.baseCaseObject.runNumber, th.ident, link))

self.ratsTcStatus[cloneTestCase.name]["tid"] = th.thId
spawnedAtLeastOne = True

if not spawnedAtLeastOne:
sleepUtil = time.time() + 120
self.logger.info("Waiting 120s For New Thread is CanRun. ")
tmpCount = 120
while time.time() < sleepUtil:
time.sleep(10)
tmpCount -= 10
self.logger.debug("Please wait a moment. Waiting %ss For New Thread is CanRun. " % tmpCount)
self.checkRatsCasesStatus()
if self.rescanIoHostsReq:
self.rescanHosts()

if (time.time() - self.timeSinceLastStatus) > 300:
self.reportStatus()
self.timeSinceLastStatus = time.time()

def setIsRescanIo(self, flag):
"""设置是否正在扫描的标记
Args:
flag (bool): 是否在进行扫描的标记:
True: 是.
False: 否.
"""
self.isRescanning = flag

def checkIsRatsTests(self):
"""检查测试用例对象是否都为RatsCase， 否则抛出异常
"""
from UniAutos.TestEngine.Group import Group
for tc in self.testCases:
if isinstance(tc, Group):
continue
if not isinstance(tc, RatsCase) and not isinstance(tc, Configuration):
raise UnsupportedException("Every Test in this Test Set must be RatsCase or Configuration script.\n"
"Test Case: %s is not RatsCase Object or a Configuration script." % tc)
pass

def incRunningRatsCase(self, ratsCase):
"""记录指定templateId的用例， 当前有多少克隆副本正在执行.
Args:
ratsCase (instance): 用例对象.
"""
self.runningTestCases[ratsCase.templateId] += 1
pass

def decRunningRatsCase(self, ratsCase):
"""克隆的用例副本执行完成后， 计数减1.
Args:
ratsCase (instance): 用例对象.
"""
self.runningTestCases[ratsCase.templateId] -= 1
pass

def getRunningRatsCaseCount(self, ratsCase):
"""获取当前用例执行的副本个数
Args:
ratsCase (instance): 用例对象.

Returns:
count (int): 正在运行的副本个数.
"""
if ratsCase.templateId in self.runningTestCases and self.runningTestCases[ratsCase.templateId]:
return self.runningTestCases[ratsCase.templateId]
else:
return 0

@validateParam(testCase=RatsCase, killFlag=bool)
def setKillAble(self, testCase, killFlag):
"""测试用例可以通过ratsEngine设置自己是否可以被kill

当部分模块、用例(如：监视、报告等)这些模块和用例正在做一些重要的事情如：日志收集、系统状态监控.
部分的kill操作尝试需要等待设置kill flag为True.
Args:
testCase (instance): 用例对象.
killFlag (bool): 是否杀掉线程的标记.
"""
if killFlag and testCase.name in self.noKillRatsThreads:
self.noKillRatsThreads.pop(testCase.name)
else:
self.noKillRatsThreads[testCase.name] = True

def stopTestThread(self, th):
"""暂停测试用例的线程
Args:
th (thread handle): 用例对象线程句柄.
"""
tid = th.thId
self.ratsSuspend[tid]["state"] = "SUSPENDED"
self.ratsSuspend[tid]["semaphore"].acquire()
self.ratsSuspend[tid]["state"] = TEST_STATUS.RUNNING
self.ratsSuspend[tid]["semaphore"].release()

def suspendRatsCase(self, tcNameList):
"""暂停测试套的中的用例测试
Args:
tcNameList (list): 测试用例对象列表.
"""
for tcName in tcNameList:
th = self.tcNameToThread[tcName]
tid = th.thId
if th.isAlive():
self.logger.info("Suspending TestCase: %s" % tcName)
else:
continue

Log.changeLogFile(Log.LogType.TestCase, self.tidToTcLogs[tid])
self.logger.info("Controller Suspended me. ")
Log.changeLogFile(Log.LogType.Main, self.controllerLogFile)
self.ratsSuspend[tid]["semaphore"].acquire()
self.stopTestThread(th)

for tcName in tcNameList:
th = self.tcNameToThread[tcName]
tid = th.thId
while self.ratsSuspend[tid]["state"] == "SUSPENDED":
self.logger.info("Waiting for thread %s To Suspend..." % th.ident)
if not th.isAlive():
self.logger.info("Actually, Thread %s looks to have finished. No need for suspend. " % th.ident)
break
time.sleep(1)

def resumeRatsCase(self, tcNameList):
"""继续暂停的测试
Args:
tcNameList (list): 测试用例对象列表.
"""
for tcName in tcNameList:
th = self.tcNameToThread[tcName]
tid = th.thId
self.logger.info("Resuming TestCase: %s " % tcName)
self.ratsSuspend[tid]["semaphore"].release()
Log.changeLogFile(Log.LogType.TestCase, self.tidToTcLogs[tid])
self.logger.info("Controller Resumed me. ")
Log.changeLogFile(Log.LogType.Main, self.controllerLogFile)

def isRatsCaseHung(self, testCase):
"""检查用例是否挂起

Checks to see if the module has declared a max runtime and if that time
has been exceeded. If so, the module is killed.

Args:
testCase (instance): 测试用例对象.
"""
th = None
if testCase.name in self.tcNameToThread:
th = self.tcNameToThread[testCase.name]
tid = th.thId
if th and "max_runtime" in self.ratsTcStatus \
and self.ratsTcStatus[testCase.name]["max_runtime"] != 0:
if time.time() > (self.ratsTcStatus[testCase.name]["start_time"] +
self.ratsTcStatus[testCase.name]["max_runtime"]):
if th.isAlive():
self.logger.info("Killing TestCase: %s, because it has timed out." % testCase.name)
self.ratsTcStatus[testCase.name]["status"] = TEST_STATUS.KILLED
self.ratsTcStatus[testCase.name]["end_time"] = time.time()
self.killTestThread(testCase, th)
return True
return False

def isRunning(self, testCase):
"""判断指定的用例当前的状态

Args:
testCase (instance): 指定用例.

Returns:
True or False, True为正在运行，False反之.
"""
if testCase.processStatus == TEST_STATUS.RUNNING or not testCase.canRunExecFlag:
self.logger.info("The RatsCase:%s Can not start new thread. Status: %s, baseRunExecFlag: %s" %
(testCase.name, testCase.processStatus, testCase.canRunExecFlag))
return True
else:
self.logger.debug("The RatsCase:%s, Last Status: %s, baseRunExecFlag: %s, Can start new thread." %
(testCase.name, testCase.processStatus, testCase.canRunExecFlag))
return False

def isCanRun(self, testCase):
"""检查测试用例对象是否能并发执行.

Args:
testCase (instance): 指定用例.

Returns:
canRun (bool): True为可以运行，False为不能运行。
"""
canRun = False
self.logger.debug("Running canRun() for Test: %s" % testCase.name)

# 如果canRun如下执行会返回True, 否则会捕获异常记录日志，并返回canRun默认值False.
try:
canRun = testCase.canRun()
except Exception, errorMsg:
self.logger.error("Test: %s canRun() method raise an exception: %s" % errorMsg)

return canRun

def checkRatsCasesStatus(self, errorMsgs=None):
"""检查线程的用例、线程的状态，根据配置杀掉线程或者记录日志

Args:
errorMsgs (str): 线程和用例的错误信息.
"""
controllerFailed = False
if errorMsgs is not None and errorMsgs != '':
controllerFailed = True
if isinstance(errorMsgs, str):
errorMsgs = [errorMsgs]
else:
errorMsgs = []

# 倒序遍历列表， 因为_checkThreadStatus函数中由修改列表操作.
for index in xrange(len(self.currentRunningTestThreads) - 1, -1, -1):
th = self.currentRunningTestThreads[index]
ratsName = self.getRatsTcNameFromTid(th.thId)
if th.errorMsg:
errorMsgs.append(th.errorMsg)
if ratsName:
self._checkThreadStatus(th, errorMsgs)
if self.isRatsCaseHung(th.tc):
errorMsgs.append("Module %s was hung and killed. " % ratsName)

# 如果用例执行失败, 且配置了遇到错误停止.
if errorMsgs and self.stopOnError:
self.logger.info("Engine: Stop On Error was set so killing all RatsCases Now!")
self.logger.info(
"Engine: Current Running Test Thread: %s" % [_th.name for _th in self.currentRunningTestThreads])
self.allowNewTestFlag = False

unKilledThreads = []

# 倒序遍历列表， 因为_killRatsThread函数中由修改列表操作.
for index in xrange(len(self.currentRunningTestThreads) - 1, -1, -1):
th = self.currentRunningTestThreads[index]
ratsName = self.getRatsTcNameFromTid(th.thId)
if ratsName and ratsName in self.noKillRatsThreads:
unKilledThreads.append(th)
continue
self._killRatsThread(th)
time.sleep(1)

# Now we need to wait for any threads that were on the no kill list to become
# killable, and then kill them too
while unKilledThreads:
waitingOnThreads = []
for th in unKilledThreads:
waitingOnThreads.append(th.thId)
self.logger.debug("The following threads are marked as unkillable and the Engine "
"is waiting for them to finish up: %s"
% "\n".join(str(tid) for tid in waitingOnThreads))
stillUnKilled = []
for th in unKilledThreads:
ratsName = self.getRatsTcNameFromTid(th.thId)
if ratsName and ratsName in self.noKillRatsThreads and self.noKillRatsThreads[ratsName]:
stillUnKilled.append(th)
unKilledThreads.pop(unKilledThreads.index(th))
continue
self._killRatsThread(th)
unKilledThreads.pop(unKilledThreads.index(th))
time.sleep(1)
unKilledThreads = stillUnKilled
if len(unKilledThreads):
time.sleep(30)

# Give each thread a few moments to get the signal and exit gracefully
stillWaiting = 1
maxWait = time.time() + 60 # Give 60 seconds to cleanly end
while stillWaiting and time.time() < maxWait:
stillWaiting = 0
self.waitAllTestComplete(self.currentRunningTestThreads)
for th in self.currentRunningTestThreads:
if th.released:
continue
if not th.isAlive():
self.logger.debug("Finished joining thread %s" % th.ident)
else:
stillWaiting = 1
if stillWaiting:
for th in self.currentRunningTestThreads:
if th.released:
continue
if th.isAlive():
self.killTestThread(th.tc, th)

self.reportStatus(controllerFailed)
self.logger.error("A ratsCase failed and Stop on Error was set. "
"Running any postTestSet hooks and exiting.")

# self.postTestSet()
raise UniAutosException("A ratsCase failed and Stop On Error was set. Exiting.")

def getEndTime(self, startTime):
"""获取测试结束的时间

Args:
startTime (float): 测试开始的时间, S为单位. 由time.time()获取.

Returns:
startTime + duration (str): 根据测试时长和测试开始时间计算的理论任务结束时间.
"""

if self.duration is None:
raise DictKeyException("TestSet Duration time have not define. ")

durationUnit = Units.getUnit(self.duration)
convertDuration = Units.convert(self.duration, SECOND)

duration = Units.getNumber(convertDuration)

return startTime + duration

def ioLockRequire(self):
"""申请主机IO锁
"""
for hostIp in self.ioLock:
self.logger.info("Allowing new IO to start on host: %s" % hostIp)
self.ioLock[hostIp].acquire()

def ioLockRelease(self):
"""释放主机IO锁
"""
for hostIp in self.ioLock:
self.logger.info("Preventing any new IO from starting on host: %s" % hostIp)
self.ioLock[hostIp].release()

def reportStatus(self, controllerFailed=False):
"""测试用例状态记录
Args:
controllerFailed (bool): 测试是否失败的标记，本接口透传到makeTimeLog接口.
"""
msg = "RatsCase Status Report\n"
for ratsCaseName in self.ratsTcStatus:
if "tid" not in self.ratsTcStatus[ratsCaseName] and self.ratsTcStatus[ratsCaseName]["tid"] \
and self.ratsTcStatus[ratsCaseName]["tid"] not in self.tidToTcLogs \
and self.tidToTcLogs[self.ratsTcStatus[ratsCaseName]["tid"]]:
continue
log = self.tidToTcLogs[self.ratsTcStatus[ratsCaseName]["tid"]]
status = self.ratsTcStatus[ratsCaseName]["status"]

color = "blue"
if status == TEST_STATUS.PASS:
color = "green"
elif status == TEST_STATUS.FAILED:
color = "red"

link = "%s" % (log, color, status)
msg += "RatsCase %s: %s\n" % (ratsCaseName, link)
self.logger.info(msg)
self.logger.info("Make TimeLine Log , Wait a few second.")
self.makeTimeLog(controllerFailed)
self.logger.info("Make TimeLine Log success.")

def initialTestEnv(self):
"""初始化环境
"""
# 初始化主机
blockDevices = []
unifiedDevices = []

tmpDevices = self.testCases[0].resource.getDevice("unified")

for deviceId in tmpDevices:
unifiedDevices.append(tmpDevices[deviceId])

uniBlkIoDevices = blockDevices + unifiedDevices

for uniBlkIoDevice in uniBlkIoDevices:
tmpHosts = None
tmpHosts = uniBlkIoDevice.getAttachedHost()
for host in tmpHosts:
# if not isinstance(host, Hypervisor)
self.hosts.append(host)
uniBlkIo = host.createUniBlkIoSession()
uniBlkIo.init()
ip = host.localIP
self.ioLock[ip] = threading.Semaphore()

pass

def initRunningRatsCase(self, tmpRatsCases):
"""初始化用例副本运行个数

Args:
tmpRatsCases (list): 测试用例对象列表.
"""
for tc in tmpRatsCases:
self.runningTestCases[tc.templateId] = 0

def __initConfigurationDbStatus(self, configurations):
"""初始化db中configuration的数据库数据."""
for _config in configurations:
_uuid = hashlib.new('md5', Log.LogFileDir + _config.name).hexdigest()
_config.statusUuid = _uuid
_dbStatus = {
"_uuid": _uuid,
"_status": TEST_STATUS.NOT_RUN,
"_what": 'configuration',
"_id": self._getIdentityOfTest(_config),
"_name": _config.name,
"_stage": 'init_case',
"_duration": '0S'
}
self.statusDb.save(**_dbStatus)


def runTests(self):
"""并发循环测试用例执行
"""
self.timeLineLogInitial()

# 获取参数
execParams = self.getParameter()
self.stopOnError = execParams.get("stop_on_error")
# self.logger.info("The stop on error value is : %s" % self.stopOnError)

# 将configuration和testCase分开.
tmpConfigurationTests = []
tmpRatsCases = []

# 如果是普通的RatsEngine，Group对象的用例不能执行.
for index in range(len(self.testCases) - 1, -1, -1):
if isinstance(self.testCases[index], Group):
self.logger.info("Test Case: %s is a Group/CCT, it can not be run in rats engine,"
"We will pop it from this test task." % self.testCases[index].name)
self.testCases.pop(index)

for tmpTc in self.testSet.testCases:
if isinstance(tmpTc, Configuration):
tmpConfigurationTests.append(tmpTc)
if isinstance(tmpTc, RatsCase):
tmpRatsCases.append(tmpTc)

# 将DeConfig和Config分开，并执行Config
# self.__initConfigurationDbStatus(tmpConfigurationTests)
deConfigurationTests = []
self.logger.info("Run Configuration First, if have configuration Test.")
perTestIsSave = False
for conf in tmpConfigurationTests:
tmpModeName = conf.getParameter().get("Mode", None)
if "Config" == tmpModeName:
perTestUuid = Log.changeLogFile(Log.LogType.PreTestSet, 'Pre_TestSet')
if not perTestIsSave:
perTestIsSave = True
self._initSpecStatusDb('Pre_TestSet',perTestUuid)
configLink = " %s" % \
(self.createTestCaseLogFile(conf.name), conf.name)
self.logger.info('Run Configuration: %s' % configLink)
self.runConfiguration(conf)

elif "DeConfig" == tmpModeName:
deConfigurationTests.append(conf)

# 创建Engine日志.
self.createEngineHtmlLog()

# 创建TimeLine日志.
self.initRunningRatsCase(tmpRatsCases)
if "duration" in self.testSet.parameters:
self.duration = self.testSet.parameters.get("duration", None).getValue()

self.logger.info("Running RATS Modules for %s. " % self.duration)
self.startRunTime = time.time()
self.endRunTime = self.getEndTime(self.startRunTime)
self.timeSinceLastStatus = time.time()

# Main Loop
while time.time() < self.endRunTime or len(self.currentRunningTestThreads) > 0:

# 移除的线程可能存在错误, 取出错误信息进行check.
__deadThreads = self._removeDeadThread(self.currentRunningTestThreads)
__errorMsg = ''
for th in __deadThreads:
__errorMsg += th.errorMsg

self.checkRatsCasesStatus(__errorMsg)
# 循环过程中如果测试套中的已经达到最大执行次数的用例个数和测试套的总用例数相同则直接退出循环.
if self.testSet.reachedMaximumTcNumber >= len(tmpRatsCases):
self.logger.info("RATS Controller All RatsCases have reached the maximum number of executions. ")
break
if time.time() >= self.endRunTime:
self.logger.info("Engine Duration Has Expired, wait all test case finished "
"or some case error will be killed.")
if time.time() - self.timeSinceLastStatus > 100:
# 注释暂时保留，以备查验.
# self.waitAllTestComplete(self.currentRunningTestThreads)
self.reportStatus()
self.timeSinceLastStatus = time.time()
self.durationExpired = True
# 2017-04-18 h90006090 从30S改为10S
time.sleep(10)
continue
# 创建新的线程
self.createNewTestThread(tmpRatsCases)

self.logger.info("RATS Controller has finished running RatsCases. "
"Now running any De-configuration steps and postTestSet hooks and exiting.")

self.reportStatus()

postTestIsSave = False
for deConf in deConfigurationTests:
postTestUuid = Log.changeLogFile(Log.LogType.PostTestSet, 'Post_TestSet')
if not postTestIsSave:
postTestIsSave = True
self._initSpecStatusDb('Post_TestSet', postTestUuid)
configLink = "%s" % \
(self.createTestCaseLogFile(deConf.name), deConf.name)
self.logger.info('Run Configuration: %s' % configLink)
self.runConfiguration(deConf, mode='DeConfig')

def recordComponentForRatsCase(self, ratsCase, component, destructive, action, tid):
"""
Marks an UniAuto Component as being used by a module. This is not a LOCK
of a component. Multiple modules may use the same component if their actions
don't conflict. This is just a mechanism to record that this module is using a
Component and declaring its actions (which may be evaluated by other modules
to determine if they can run on this component)

Args:
ratsCase (instance): 用例对象.
component (instance): 测试用例的component对象.
destructive (bool): will this module be destructive to this Component.
action (str): they type of action. This should be a simple description
that other modules can check as well to determine if they can run.
eg: 'MIGRATION_DESTINATION', or "SNAPSHOT_SOURCE"
tid (int): 线程ID.

Examples:
self.recordComponentForRatsCase(tc, component, True, "SNAPSHOT_SOURCE", 100)

"""
shareDict = {"destructive": destructive,
"action": action,
"tid": tid}
cStr = str(component)
self.recordComponentsLock.acquire()
if cStr not in self.recordComponents or not self.recordComponents[cStr]:
self.recordComponents[cStr] = {}
self.recordComponents[cStr][ratsCase.name] = shareDict
self.recordComponentsLock.release()
pass

def recordRatsCaseCompleteWithComponent(self, ratsCase, component=None):
"""Records that a module is done with a component
Args:
ratsCase (instance): 用例对象.
component (instance): 用例关联的Component.
"""
tcName = ratsCase.name
self.recordComponentsLock.acquire()
if component is not None:
self.recordComponents[str(component)].pop(tcName)
for componentStr in self.recordComponents:
# self.recordComponents 为字典, self.recordComponents[componentStr]为字典，
# 故self.recordComponents[componentStr].pop()不依赖index，依赖key，可以采用深度拷贝复制对象后，
# 判断深度复制的对象，如果对象满足名称上的一致，则删除深度复制前的对象元素.
tmp = copy.deepcopy(self.recordComponents[componentStr])
for tmpName in tmp:
if tmpName == tcName:
self.recordComponents[componentStr].pop(tmpName)
self.recordComponentsLock.release()
# 代码暂时保留作为修改对照.
# for tmpName in self.recordComponents[componentStr]:
# if tmpName == tcName:
# self.recordComponents[componentStr].pop(tmpName)
return

def getCurrentComponentActions(self, component):
"""获取当前正在使用指定的component的用例和用例的操作

Args:
component (instance): 指定需要查询的UniAutos.Component对象

Returns:
actionDict (dict): 包含用例和他们的操作的字典. 格式如下:
moduleName: {action: 'Action',
destructive: 'boolean',
tid: tid of modules thread}

moduleName: {...}: 可能多个用例使用该Component.
Examples:
self.getCurrentComponentActions(component)

"""
actionDict = None
cStr = str(component)
self.recordComponentsLock.acquire()
if cStr in self.recordComponents:
actionDict = self.recordComponents[cStr]
self.recordComponentsLock.release()
return actionDict

def getRatsTcNameFromTid(self, tid):
"""通过线程id获取TestCase的名称.

Args:
tid (int): 线程id.

Returns:
tcName (str): 指定线程关联的用例名称.

Examples:
self.getRatsTcNAmeFromTid(100)

Changes:
2015-05-26 h90006090 修改:RuntimeError: dictionary changed size during iteration问题.
采用dict.keys()拷贝key变量进行遍历.
"""
# tcNameToThread在子线程中会有增加操作，且有多处需要进行遍历操作. 使用dict.keys()拷贝key变量进行操作.
for tcName in self.tcNameToThread.keys():
if self.tcNameToThread[tcName].thId == tid:
return tcName
return None

def rescanHosts(self):
pass

def makeTimeLog(self, controllerFail=False):
"""生成timeline日志文件

Args:
controllerFail (bool): 该参数用于说明当前执行中是否存在错误发生.
True: 存在.
False: 不存在.
"""

color = "green"
status = ""

if controllerFail:
color = "red"
status = "---FAILED"

controllerLink = "" \
"View Controller Log %s" % (color, status)
monitorLink = "View Monitor Log"

baseDict = {} # 用于重组ratsTcStatus.
earliest = None
latest = None
concurrentDict = {} # 保存当前正在执行的用例信息.

for tcName in self.ratsTcStatus:
if TEST_STATUS.RUNNING == self.ratsTcStatus[tcName]["status"]:
self.ratsTcStatus[tcName]["end_time"] = time.time()

# 向baseDict中添加元素.
if self.ratsTcStatus[tcName]["base"] in baseDict:
baseDict[self.ratsTcStatus[tcName]["base"]][tcName] = self.ratsTcStatus[tcName]
else:
baseDict[self.ratsTcStatus[tcName]["base"]] = {}
baseDict[self.ratsTcStatus[tcName]["base"]][tcName] = self.ratsTcStatus[tcName]

if earliest is None or self.ratsTcStatus[tcName]["start_time"] < earliest:
earliest = self.ratsTcStatus[tcName]["start_time"]

if latest is None or self.ratsTcStatus[tcName]["end_time"] > latest:
latest = self.ratsTcStatus[tcName]["end_time"]

if not (latest and earliest):
self.logger.debug("There is not enough runtime to generate the timeline log yet."
"\n startTime:%s \n latestTime: %s" % (str(earliest), str(latest)))
return

# Check to make sure every module in the test set has at least some data (even if empty)

for tc in self.testCases:
if tc.name not in baseDict:
baseDict[tc.name] = {}

# Each module has a time range. Figure out how many modules of each time have run at the same
# time and how many during that time.

for baseName in baseDict:
maxConcurrent = 0
for entry in baseDict[baseName]:
maxEntryConcurrent = 0
startTime = baseDict[baseName][entry]["start_time"]
endTime = baseDict[baseName][entry]["end_time"]
for searchEntry in baseDict[baseName]:
# Ranges look like this
# S-------E This startTime and endTime
# S---E Scenario 1 MATCH
# S-------E Scenario 2 MATCH
# S------E Scenario 3 MATCH
# S--E S--E Exclude these
if (startTime = baseDict[baseName][searchEntry]["end_time"]) \
or (startTime startTime):
maxEntryConcurrent += 1
if maxEntryConcurrent > maxConcurrent:
maxConcurrent = maxEntryConcurrent
concurrentDict[baseName] = maxConcurrent

# 设置用例执行时间
duration = latest - earliest

days = int(duration / (24 * 60 * 60))
hours = int((duration / (60 * 60)) % 24)
minutes = int((duration / 60) % 60)
seconds = int(duration % 60)
durationStr = "{Days},{HH}:{MM}:{SS}".format(Days=days,
HH=hours,
MM=minutes,
SS=seconds)
# 计算每个表格的元素长度.
cellDuration = None
numberOfCells = None

def cDurationExc():

for cDuration in range(1, 1200):
if cDuration * cells >= duration:
tmp = earliest
while tmp = start and tcDict[tmpTc][entry]["end_time"] 1:
return False
return True