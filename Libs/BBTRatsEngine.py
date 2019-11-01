
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: BBTCase, BBT用例类.

版权信息: 华为技术有限公司，版本所有(C) 2014-2015
"""
import time
import sys
import copy
import hashlib
import datetime
import re
import threading
from time import sleep

from UniAutos.TestEngine.Group import Group
from UniAutos.TestEngine.Configuration import Configuration
from UniAutos.TestEngine.RatsCase import RatsCase
from UniAutos.Exception.HookException import HookException
from UniAutos.Util.TestStatus import TEST_STATUS
from UniAutos.Util.Units import Units
from UniAutos import Log
from UniAutos.TestEngine.RatsEngine import RatsEngine
from UniAutos.Exception.UniAutosException import UniAutosException


class BBTRatsEngine(RatsEngine):
@property
def bbtTestCases(self):
"""获取测试套中所有的测试用例, 包含Group中的用例."""
__bbtTestCases = []
for test in self.testCases:
if isinstance(test, Group):
__bbtTestCases.extend(test.testCases)
__bbtTestCases.append(test)
return __bbtTestCases

def __runBBTRatsCase(self, ratsCase):
"""运行测试用例内容.
Args:
ratsCase (RatsCase|Group): 指定运行的测试用例对象.
"""
tid = threading.current_thread().thId
self.ratsSuspend[tid] = {"semaphore": threading.Semaphore(),
"state": TEST_STATUS.RUNNING}
# 设置测试用例日志.
tcLogFile = ratsCase.name
tcUuid = Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
self.tidToTcLogs[tid] = tcLogFile + "---0" # "---0" 日志文件过大后分片的标志， 默认第一分片加上.
self.tcNameToThread[ratsCase.name] = threading.current_thread()
ratsCase.logCaseDetailInfo()
ratsCase.logParameter()
postReason = ''
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.RUNNING)
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.RUNNING)
ratsCase.setCaseStatus(TEST_STATUS.RUNNING)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.RUNNING
# 2015/09/28 h90006090 Add test case startTime use to tmss fillback.
_start = datetime.datetime.now()
_formatStart = _start.strftime('%Y-%m-%d %H:%M:%S')
ratsCase.baseCaseObject.setStartTime(_formatStart)
ratsCase.setStartTime(_formatStart)
Log.TestCaseStatusLogger.logTestCaseStatus(name=ratsCase.name,
status=TEST_STATUS.RUNNING,
start=_formatStart,
end=_formatStart,
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
# 3. 如果配置了Delay Start, 先进行Delay执行.
if hasattr(ratsCase, 'delay_start') and ratsCase.delay_start is not None:
delay_start = ratsCase.delay_start
ratsCase.logger.info("###BBT###: %s Delay Start On %s Later, Please Wait........."
% (ratsCase.name, delay_start))
sleep(Units.getNumber(delay_start))
# 记录数据到数据库中.
# _uuid = hashlib.new('md5', Log.LogFileDir + ratsCase.name).hexdigest()
ratsCase.statusUuid = tcUuid
_dbStatus = {
'_uuid': ratsCase.statusUuid,
"_stage": 'running',
"_end": _start,
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
# test case procedure(), duration
duration = ratsCase.duration if hasattr(ratsCase, 'duration') else None
iterations = ratsCase.iterations if hasattr(ratsCase, 'iterations') else None
wait_between_iterations = ratsCase.wait_between_iterations if \
hasattr(ratsCase, 'wait_between_iterations') else None

self.logger.debug("###BBT###: Running %s Procedure(), Duration: %s, Iterations: %s. "
% (ratsCase.name, duration, iterations))
# 执行procedure(), 测试主体.
try:
startRunTime = time.time()
endRunTime = startRunTime
if duration:
convertDuration = Units.convert(duration, 'S')
duration = Units.getNumber(convertDuration)
endRunTime = startRunTime + duration

if duration and iterations:
count = 1
while time.time() < endRunTime and iterations:
ratsCase.procedure()
ratsCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (ratsCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
iterations -= 1
count += 1
elif duration:
count = 1
while time.time() < endRunTime:
ratsCase.procedure()
ratsCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (ratsCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
count += 1
elif iterations:
count = 1
while iterations:
ratsCase.procedure()
ratsCase.logger.debug('###BBT###: Running %s Procedure() Finished No.%s, Wait %s To Re-execute '
'Procedure() Again.' % (ratsCase.name, count, wait_between_iterations))
sleep(Units.getNumber(wait_between_iterations))
iterations -= 1
count += 1
else:
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
if isinstance(ratsCase, Group) and ratsCase.caseStatus == TEST_STATUS.INCOMPLETE:
ratsCase.setCaseStatus(TEST_STATUS.INCOMPLETE)
ratsCase.baseCaseObject.setCaseStatus(TEST_STATUS.INCOMPLETE)
ratsCase.baseCaseObject.setRatsCaseProcessStatus(TEST_STATUS.INCOMPLETE)
self.ratsTcStatus[ratsCase.name]["status"] = TEST_STATUS.INCOMPLETE # 及时更新Case的状态.

else:
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
'_status': ratsCase.caseStatus,
"_base_status": ratsCase.baseCaseObject.caseStatus
})
self.statusDb.update(ratsCase.statusUuid, **_postUpdateStatus)

ratsCase.logger.tcEnd()
self.ratsTcStatus[ratsCase.name]["end_time"] = time.time()

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

def _runRatsTest(self, ratsCase):
"""并发串行时，执行单个用例.
Args:
ratsCase (instance): 测试用例对象.
"""

# 获取Dependency参数
tid = threading.current_thread().thId
self.ratsSuspend[tid] = {"semaphore": threading.Semaphore(),
"state": TEST_STATUS.RUNNING}
# 设置测试用例日志.
tcLogFile = ratsCase.name
Log.changeLogFile(Log.LogType.TestCase, tcLogFile)
self.tidToTcLogs[tid] = tcLogFile + "---0" # "---0" 日志文件过大后分片的标志， 默认第一分片加上.
dependency = ratsCase.dependency if hasattr(ratsCase, 'dependency') else None
self.logger.info("Start to check test case dependency.")

# 如果当前用例不存在dependency直接执行.
if not dependency:
self.__runBBTRatsCase(ratsCase)
return None

else:
dependencyCases = {}
# 查找依赖的用例.
for _dependency in dependency:
for case in self.testCases:
if re.match(_dependency.get('test_name'), case.name):
dependencyCases.update({case: _dependency.get('status')})
break

# 如果查找到的dependency少于配置，则直接报错
# Note：参数配置错误时可能出现该情况.
if len(dependencyCases) < len(dependency):
__error = '###BBT###: %s not run, because dependency on: \n %s, But The condition is not satisfied, ' \
'dependency case only have: %s.' % (ratsCase.name, dependency, dependencyCases)
self.logger.error(__error)
self._handleException(ratsCase, __error, "pre")
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

# 如果有一个不满足条件直接报错退出.
if _flag is None:
__error = '###BBT###: %s not run, because dependency on: \n %s, But The condition is not satisfied.' \
% (ratsCase.name, dependency)
self.logger.error(__error)
self._handleException(ratsCase, __error, 'pre')
raise UniAutosException(__error)

# 满足执行当前用例.
if _flag:
self.__runBBTRatsCase(ratsCase)
return None
self.logger.debug('###BBT###: %s not run, because dependency on: \n %s, '
'Please wait 60s to check dependency status and try again.'
% (ratsCase.name, dependency))
sleep(60)

def runTests(self):
"""并发循环测试用例执行

Examples:
self.runTests()

"""
self.timeLineLogInitial()
# 获取参数
execParams = self.getParameter()
self.stopOnError = execParams.get("stop_on_error")

# 将configuration和testCase分开.
tmpConfigurationTests = []
tmpRatsCases = []

for tmpTc in self.testSet.testCases:
if isinstance(tmpTc, Configuration):
tmpConfigurationTests.append(tmpTc)
if isinstance(tmpTc, RatsCase) or isinstance(tmpTc, Group):
tmpRatsCases.append(tmpTc)

# 将DeConfig和Config分开，并执行Config
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
if isinstance(tc, RatsCase):
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
elif isinstance(tc, Group):
__group = {'parallel': tc.parallel,
'testCases': tc.testCases,
'templateId': tc.templateId,
'order': tc.order,
'name': cloneTestName,
'base': tc,
'engine': tc.engine}
return Group(__group)