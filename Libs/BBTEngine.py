#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: BBTCase, BBT用例类.

版权信息: 华为技术有限公司，版本所有(C) 2014-2015
"""
import datetime
import time
import threading
import re
import os

from UniAutos.Util.Threads import Threads
from UniAutos.Util.Time import sleep
from UniAutos.Util.Units import Units
from UniAutos.TestEngine.Group import Group
from UniAutos.TestEngine.Configuration import Configuration
from UniAutos.TestEngine.BBTCase import BBTCase
from UniAutos.TestEngine.Base import Base
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.HookException import HookException
from UniAutos import Log
from UniAutos.Log import LogFormat
from UniAutos.TestEngine.Engine import Engine
from UniAutos.Util.TestStatus import TEST_STATUS


class BBTEngine(Engine):
"""BBT类型的测试用例基类
"""
# NOTE: self.testCases中包含的是归属于测试套的用例和Group(CCT), Group中的测试用例不在其中.

# TODO 部分代码与Engine和RatsEngine重复，后续需要统一整改.

# BBTEngine公共属性
@property
def bbtTestCases(self):
"""获取测试套中所有的测试用例, 包含Group中的用例."""
__bbtTestCases = []
for test in self.testCases:
if isinstance(test, Group):
__bbtTestCases.extend(test.testCases)
__bbtTestCases.append(test)
return __bbtTestCases

# BBTEngine公共接口

def logGroupCaseLink(self, tg, tc):
"""生成和打印est Group中的Test Case的日志链接到Group日志主界面.
Args:
tg (Group): Group对象.
tc (Base): 用例对象.
"""
Log.changeLogFile(Log.LogType.TestCase, tg.name)
fileFullName = tg.name + '/' + tc.name
fileFullName = fileFullName.replace('.', '_')
fileLink = fileFullName + '---0' + ".html"
self.logger.info(LogFormat.fileLink.format(href=fileLink, msg=tc.name))

def getEndTime(self, startTime, duration):
"""获取测试结束的时间

Args:
startTime (float): 测试开始的时间, S为单位. 由time.time()获取.
duration (str): 测试间隔时间.

Returns:
startTime + duration (str): 根据测试时长和测试开始时间计算的理论任务结束时间.
"""

convertDuration = Units.convert(duration, 'S')
duration = Units.getNumber(convertDuration)
return startTime + duration

def updateStatus(self):
"""
更新当前测试用例执行的状态，生成状态数据，用于日志中的图形显示.
"""
notRun = 0
passed = 0
failed = 0
configError = 0
running = 0
killed = 0

for testObj in self.bbtTestCases:
if isinstance(testObj, Base):
if testObj.caseStatus == TEST_STATUS.NOT_RUN:
notRun += 1
if testObj.caseStatus == TEST_STATUS.PASS:
passed += 1
if testObj.caseStatus == TEST_STATUS.FAILED:
failed += 1
if testObj.caseStatus == TEST_STATUS.RUNNING:
running += 1
if testObj.caseStatus == TEST_STATUS.KILLED:
killed += 1
if testObj.caseStatus == TEST_STATUS.CONFIG_ERROR:
configError += 1

total = notRun + passed + failed + running + killed + configError

fh = open(os.path.join(Log.LogFileDir, 'status.js'), 'w')
fh.write('var stats = [{0}, {1}, {2}, {3}, {4}, {5}, {6}]\n\n'.format(total, passed, failed, configError,
notRun, killed, running))
fh.write("var testData = [{label: 'Pass', data: %s, color: 'green'}, "
"{label: 'Fail', data: %s, color: 'red'}, "
"{label: 'ConfigError', data: %s, color: 'blue'}, "
"{label: 'Not Run', data: %s, color: 'yellow'}, "
"{label: 'Kill', data: %s, color: 'orange'}, "
"{label: 'Running', data: %s, color: '#2ECCFA'}]" % (passed, failed, configError, notRun,
killed, running))
fh.close()

# BBTEngine公共调度方法
def __parallelTest(self, tc, tcLogFile):
"""针对BBTEngine中并发执行时， 单个测试执行调度的接口

获取dependency，判断当前用例或者Group的依赖情况, 并根据依赖对象的结果分别进行不同的执行调度.
Args:
tc (Base): 测试用例对象, 用例对象可归属于测试套或Group.
tcLogFile (str): 测试用例的日志文件，透传给__runTest()方法.

"""
# 获取Dependency参数
dependency = tc.dependency if hasattr(tc, 'dependency') else None
self.logger.info("Start to check test case dependency.")

# 如果当前用例不存在dependency直接执行.
if not dependency:
self._runTest(tc, tcLogFile)
return

dependencyCases = {}
# 查找依赖的用例.
inner_count = 0
for _dependency in dependency:
if _dependency.get('inner'):
inner_count += 1
for case in self.testCases:
if _dependency.get('test_name'):
if re.match(_dependency.get('test_name'), case.name):
dependencyCases.update({case: _dependency.get('status')})
break
elif _dependency.get('test_alias') and _dependency.get('status'): # 专门应对BBT用例中间状态依赖的情况，中间状态依赖交给脚本来处理
if hasattr(case,"alias") and case.alias:
if re.match(_dependency.get('test_alias'), case.alias):
dependencyCases.update({case: _dependency.get('status')})
break

# 如果查找到的dependency少于配置，则直接报错
# Note：参数配置错误时可能出现该情况.
if len(dependencyCases) < len(dependency) - inner_count:
__error = '###BBT###: %s not run, because dependency on: \n %s, But The condition is not satisfied, ' \
'dependency case only have: %s.' % (tc.name, dependency, dependencyCases)
self.logger.error(__error)
self._handleException(tc, __error, "pre")
# raise UniAutosException(__error)

self.logger.info("###BBT###: dependency cases: %s" % ([_tmp.caseStatus for _tmp in dependencyCases]))

# 判断用例的状态执行当前用例.
while True:
_flag = True

for dependencyCase in dependencyCases:

# 判断依赖的状态是否满足不满足时，继续等待.
if dependencyCase.caseStatus.lower() != dependencyCases[dependencyCase].lower():
_flag = False

# 如果不满足条件，但是依赖对象的状态为已经执行完成的几个状态时，证明当前依赖执行结果不满足条件.
# TODO POST处理
if dependencyCase.caseStatus.lower() in [TEST_STATUS.PASS.lower(),
TEST_STATUS.KILLED.lower(),
TEST_STATUS.CONFIG_ERROR.lower(),
TEST_STATUS.FAILED.lower(),
TEST_STATUS.CONFIGURED.lower(),
TEST_STATUS.COMPLETE.lower(),
TEST_STATUS.DE_CONFIGURED.lower()]:
_flag = None
break
# elif dependencyCase.caseStatus.lower() != dependencyCases[dependencyCase].lower() \
# and dependencyCase.caseStatus.lower() in [TEST_STATUS.PASS.lower(),
# TEST_STATUS.KILLED.lower(),
# TEST_STATUS.CONFIG_ERROR.lower(),
# TEST_STATUS.FAILED.lower(),
# TEST_STATUS.CONFIGURED.lower(),
# TEST_STATUS.COMPLETE.lower(),
# TEST_STATUS.DE_CONFIGURED.lower()]:
# _flag = None

self.logger.info('###BBT###: Current dependency case[%s], status: [%s]' %
(dependencyCase.name,
dependencyCase.caseStatus))

# 如果有一个依赖用例不满足条件直接报错退出.
if _flag is None:
__error = '###BBT###: %s not run, because dependency on: \n %s, But The condition is not satisfied.'\
% (tc.name, dependency)
self.logger.error(__error)
self._handleException(tc, __error, 'pre')
raise UniAutosException(__error)

# 满足执行当前用例.
if _flag:
self._runTest(tc, tcLogFile)
return
wait_time = tc.testSet.getParameter().get('wait_between_cases', 60)
self.logger.debug('###BBT###: %s not run, because dependency on: \n %s, '
'Please wait %ss to check dependency status and try again.'
% (tc.name, dependency, wait_time))
sleep(wait_time)

def runTests(self):
"""使用BBTEngine, 顺序执行测试套中配置的所有测试用例, 包含Group类型.
"""
runTestCases = []
self.logger.info("TestEngine (runTests) - Running all Tests. ")

# 更新status.js文件用于绘制测试用例状态饼图.
self.updateStatus()

# 遍历测试用例对象进行测试执行.
# self._initStatusLogFile()
for testCase in self.testCases:

self.testSet.setRunHistory(runTestCases)
self.setCurrentlyRunningTest(testCase)
self.testSet.setCurrentlyRunningTest()
self.startTime = time.time()
self.incrementTestCounter()

# 改变日志记录的文件.
tcLogFile = testCase.name
tcUuid = Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
self._initTcStatusDb(testCase,tcUuid)

# 用例全局状态初始值设定.
self.globalTestStatus[testCase.name] = {'status': TEST_STATUS.NOT_RUN,
'start_time': time.time(),
'end_time': time.time(),
'tid': None}
if isinstance(testCase, Configuration):
self._runConfiguration(testCase, tcLogFile)

else:
self._runTest(testCase, tcLogFile)
self.updateStatus()
self.setCurrentlyRunningTest(None)

def _runTest(self, testCase, tcLogFile):
"""运行单个测试用例
该函数主要用于执行用例中preTestCase、procedure、postTestCase中的测试步骤.
Args:
testCase (BBTCase|Group): 测试用例对象.
"""

# 1. 打印测试用例开始日志，开始执行测试用例.
testCase.logCaseDetailInfo()
testCase.logParameter()
self.logger.tcStart()
postReason = ''
# 2015/09/28 h90006090 Add test case startTime use to tmss fillback.
_start = datetime.datetime.now()
testCase.setStartTime(_start.strftime('%Y-%m-%d %H:%M:%S'))
testCase.setCaseStatus(TEST_STATUS.RUNNING)

# 如果运行的时group外层测试用例包括Group，且为并发.
if self.runTestsInParallelFlag:
self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus

_uuid = testCase.statusUuid
_dbStatus = {
"_stage": 'running',
"_post_status": TEST_STATUS.NOT_RUN,
"_status": TEST_STATUS.RUNNING,
"_start": _start,
"_end": _start,
"_log_file": tcLogFile}

self.statusDb.update(_uuid, **_dbStatus)
self.serialLogResult(testCase, postReason)

# 3. 如果配置了Delay Start, 先进行Delay执行.
if hasattr(testCase, 'delay_start') and testCase.delay_start is not None:
delay_start = testCase.delay_start
testCase.logger.info("###BBT###: %s Delay Start On %s Later, Please Wait........."
% (testCase.name, delay_start))
sleep(Units.getNumber(delay_start))

testCase.logger.info("###PRE-TEST-CASE: %s ###" % testCase.name)

# 4. 执行preTestCase, 如果执行失败TestCase执行失败.
preTestCasePassFlag = False
try:
self.runHooks('beforePreTest')
testCase.preTestCase()
if isinstance(testCase, Group) and testCase.groupError:
Log.MainLogger.fail("%s Pre Test Failed. " % testCase.name)
self.runHooks("afterPreTest")
except HookException, errorMsg:
Log.MainLogger.fail("%s Run Hook Failed. detail: %s" % (testCase.name, errorMsg))
self._handleException(testCase, errorMsg, 'pre')
return
except Exception, errorMsg:
self._handleException(testCase, errorMsg, "pre")
Log.MainLogger.fail("%s Pre Test Failed. " % testCase.name)
self.runHooks("afterPreTest", tc=testCase)
else:
preTestCasePassFlag = True
testCase.logger.passInfo("%s Pre TestCase Passed. " % testCase.name)


# 5. 执行测试用例procedure, 如果preTestCase执行失败则直接跳过，同时mainTestCasePassFlag为False.
if preTestCasePassFlag:
testCase.logger.info("###MAIN###")

# test case procedure(), duration
duration = testCase.duration if hasattr(testCase, 'duration') else None
iterations = testCase.iterations if hasattr(testCase, 'iterations') else None
wait_between_iterations = testCase.wait_between_iterations if \
hasattr(testCase, 'wait_between_iterations') else None

self.logger.debug("###BBT###: Running %s Procedure(), Duration: %s, Iterations: %s. "
% (testCase.name, duration, iterations))
# Main Loop
try:
# 5.2 如果存在duration，按照duration进行执行, duration优先级最高.
self.runHooks('beforeProcedure', tc=testCase)
startRunTime = time.time()
endRunTime = startRunTime
if duration:
convertDuration = Units.convert(duration, 'S')
duration = Units.getNumber(convertDuration)
endRunTime = startRunTime + duration

if duration and iterations:
count = 1
while time.time() < endRunTime and iterations:
testCase.procedure()
testCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (testCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
iterations -= 1
count += 1
elif duration:
count = 1
while time.time() < endRunTime:
testCase.procedure()
testCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (testCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
count += 1
elif iterations:
count = 1
while iterations:
testCase.procedure()
testCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (testCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
iterations -= 1
count += 1

# 5.3 都不存在按照标准执行.
else:
testCase.procedure()
if isinstance(testCase, Group) and testCase.groupError:
Log.MainLogger.fail("%s Main Test Failed. " % testCase.name)
self.runHooks("afterProcedure")
except HookException, errorMsg:
Log.MainLogger.fail("%s Run Hook Failed. detail: %s" % (testCase.name, errorMsg))
self._handleException(testCase, errorMsg, 'main')
return
except Exception, errorMsg:
Log.MainLogger.fail("%s Main Test Failed. " % testCase.name)
self._handleException(testCase, errorMsg, "main")
self.runHooks("afterProcedure", tc=testCase)
else:
testCase.logger.passInfo("%s Main Test has Passed" % testCase.name)
if not self.runTestsInParallelFlag:
Log.MainLogger.passInfo("%s Main Test Passed. " % testCase.name)

if isinstance(testCase, Group) and testCase.caseStatus == TEST_STATUS.INCOMPLETE:
testCase.setCaseStatus(TEST_STATUS.INCOMPLETE)
else:
testCase.setCaseStatus(TEST_STATUS.PASS)

# 6. 不管preTestCase和procedure是否执行成功，都要执行postTestCase.
self.logger.info("###POST-TEST-CASE###")
try:
# h90006090 2018/03/01 Add: Post运行情况记录，方便Hook或其他接口进行其他操作
testCase.setPostStatus(TEST_STATUS.RUNNING)
testCase.postTestCase()
if isinstance(testCase, Group) and testCase.groupError:
Log.MainLogger.fail("%s Post Test Failed. " % testCase.name)
self.runHooks("afterPostTest", tc=testCase)
except HookException, errorMsg:
Log.MainLogger.fail("%s Run Hook Failed. detail: %s" % (testCase.name, errorMsg))
self._handleException(testCase, errorMsg, 'post')
return
except Exception, errorMsg:
self._handleException(testCase, errorMsg, "post")
Log.MainLogger.fail("%s Post Test Failed. " % testCase.name)
postReason = errorMsg.message
self.runHooks("afterPostTest", tc=testCase)
else:
testCase.logger.passInfo("%s Post TestCase Passed" % testCase.name)
if self.runTestsInParallelFlag:
self.globalTestStatus[testCase.name]["status"] = testCase.caseStatus

if self.runTestsInParallelFlag:
duration = str(time.time() - self.globalTestStatus[testCase.name]["start_time"]) + "S"
else:
duration = str(time.time() - self.startTime) + "S"

_dbStatus = {
'_post_status': TEST_STATUS.PASS,
"_duration": duration,
}
self.statusDb.update(_uuid, **_dbStatus)

_end = datetime.datetime.now()
_dbStatus = {
"_stage": 'done',
"_end": str(_end),
"_status": testCase.caseStatus
}
self.statusDb.update(_uuid, **_dbStatus)

if self.runTestsInParallelFlag:
self.globalTestStatus[testCase.name]["end_time"] = time.time()
testCase.logger.tcEnd()
# 2015/09/28 h90006090 Add test case endtime use to tmss fillback.
testCase.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
self.serialLogResult(testCase, postReason)
Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

# 测试套调度并发接口
def runTestsInParallel(self):
"""单次并发执行用例
当判断测试套中设置Parallel为True时调用此接口进行单次并发执行测试.
"""
self.logger.info("BBTEngine.py (runTestsInParallel) - Running all Tests in bbt parallel.")
self.updateStatus()
self.createEngineHtmlLog()
self.timeLineLogInitial()

# 将configuration和testCase分开.
configurationTests = []
deConfigurationTests = []
tmpTestCases = []

for tmpTc in self.testCases:
if isinstance(tmpTc, Configuration):
if tmpTc.getParameter('Mode')['Mode'] == 'Config':
configurationTests.append(tmpTc)
elif tmpTc.getParameter('Mode')['Mode'] == 'DeConfig':
deConfigurationTests.append(tmpTc)
if isinstance(tmpTc, BBTCase) or isinstance(tmpTc, Group):
tmpTestCases.append(tmpTc)

perTestIsSave = False
for conf in configurationTests:
perTestUuid = Log.changeLogFile(Log.LogType.PreTestSet, 'Pre_TestSet')
if not perTestIsSave:
perTestIsSave = True
self._initSpecStatusDb('Pre_TestSet', perTestUuid)
configLink = "%s" % \
(self.createTestCaseLogFile(conf.name), conf.name)
self.logger.info('Run Configuration: %s' % configLink)
self.runConfiguration(conf)

timeSinceLastStatus = time.time()

# 将TestCase加入线程.
for tcObject in tmpTestCases:

# 将名字重新赋值，预防同一个用例参数不同的情况.
tcObjectTmpName = tcObject.name
time.sleep(0.1)
tcObject.setName(tcObjectTmpName)

# 用例全局状态初始值设定.
self.globalTestStatus[tcObject.name] = {'status': TEST_STATUS.NOT_RUN,
'start_time': time.time(),
'end_time': time.time()}

# 启动线程并发执行.
tcThread = Threads(self._runTestParallel, tcObject.name, testCase=tcObject)
tcThread.start()
self.currentRunningTestThreads.append(tcThread)

self.logger.info("Wait test case create log file, if hung on, please call automation support staff.")
while tcThread.ident not in self.tidToTcLogs or not self.tidToTcLogs[tcThread.ident]:
time.sleep(1)

# 创建日志连接
logLink = "%s" \
% (self.tidToTcLogs[tcThread.ident], self.tidToTcLogs[tcThread.ident])
self.logger.info("Test Case %s Start, Dependency on %s.\n"
"Thread ID: %s \n %s" % (tcObject.name, tcObject.dependency, tcThread.ident, logLink))
self.tidToTcName[tcThread.ident] = tcObject.name
self.globalTestStatus[tcObject.name]["tid"] = tcThread.ident

# 用例状态轮询检查
self._checkTestCaseThreadStatus(timeSinceLastStatus)

# 创建TimeLine日志
self.makeTimeLog()

# run deConfig
postTestIsSave = False
for conf in deConfigurationTests:
postTestUuid = Log.changeLogFile(Log.LogType.PostTestSet, 'Post_TestSet')
if not postTestIsSave:
postTestIsSave = True
self._initSpecStatusDb('Post_TestSet', postTestUuid)
configLink = " %s" % \
(self.createTestCaseLogFile(conf.name), conf.name)
self.logger.info('Run Configuration: %s' % configLink)
self.runConfiguration(conf, mode='DeConfig')
self.updateStatus()

def _runTestParallel(self, testCase):
"""并发串行时，执行单个用例.
Args:
testCase (instance): 测试用例对象.
"""

# 设置开始时间.
self.globalTestStatus[testCase.name]["start_time"] = time.time()

# 线程id与日志文件关联.
tcLogFile = testCase.name
self.tidToTcLogs[threading.current_thread().ident] = tcLogFile + "---0"
tcUuid = Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
self._initTcStatusDb(testCase, tcUuid)
self.tidToTcObject[threading.current_thread().ident] = testCase

# 运行单个测试
self.__parallelTest(testCase, tcLogFile)