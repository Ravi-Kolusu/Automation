#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Group类，用以实例化测试套中配置的类型为test_group和cct的类型.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

"""

import time
import re
import datetime
import traceback
import threading
import os
import random
import hashlib
from random import choice

from UniAutos import Log
from UniAutos.Log import LogFormat
from UniAutos.Util.Time import sleep
from UniAutos.Util.Units import Units
from UniAutos.Util.TestStatus import TEST_STATUS, STATUS_UNITS
from UniAutos.TestEngine.RatsCase import RatsCase
from UniAutos.TestEngine.Case import Case
from UniAutos.Util.Threads import Threads
from UniAutos.TestEngine.Parameter import Parameter
from UniAutos.Exception.ValueException import ValueException
from UniAutos.Exception.HookException import HookException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.TypeException import TypeException
from UniAutos.TestEngine.Configuration import Configuration


class Group(object):
def __init__(self, parameters):
self.statusUuid = None
self.__testCases = parameters.get('testCases')
self.__parallel = parameters.get('parallel', False)
self.__order = parameters.get('order')
self.name = parameters.get('name', 'TestGroup')
self.testSet = None
self.identities = parameters.get('identities')
self.caseStatus = 'NotRun'
self.__startTime = '1990-01-01 01:01:01'
self.__endTime = '1990-01-01 01:01:01'
self.durationStartTime = time.time()
self.__logger = Log.getLogger(self.__class__.__name__)
self.__testEngine = parameters.pop("engine", None)
self.__logCollectFlag = False
self.parameters = {}

self.tidToTcName = {} # 线程ID和TestCase名称的映射.
self.tidToTcObject = {} # 线程ID和TestCase对象的映射.
self.globalTestStatus = {} # TestCase对象全局状态.
self.tidToTcLogs = {} # 线程ID和TestCase日志文件名称的映射.
self.currentRunningTestThreads = []
self.__groupError = False
self.failureReason = ''
# 错误计数多线程共享
self.errorCount = 0
self.warnCount = 0
self.errorCountSemaphore = threading.Semaphore()
self.warnCountSemaphore = threading.Semaphore()

# 克隆之前的用例唯一ID
self.templateId = parameters.pop("templateId", random.randrange(1000000))

# 定义一个克隆之前的用例对象，用来保存该用例对象的全局状态用来判断当前的用例是否可以执行.
self.baseCaseObject = parameters.pop("base", None)
self.maxRunTime = 0
self.runNumber = 0
self.canRunExecFlag = True
self.debugSwitch = True
self.numberOfExecuted = 0
self.__id = parameters.get('id')
self.__detail = parameters.get('detail')
times = parameters.get("times")
self.totalNumberOfExec = int(times) if times is not None and Units.isNumber(times) else None
self.processStatus = TEST_STATUS.NOT_RUN
self.__postStatus = TEST_STATUS.NOT_RUN

self.customParam = parameters.get("params")
self.resource = parameters.get("resource")
# 测试执行前需要做的比如添加参数.
self.createMetaData()

# 设置testSet中传入的case parameter到case用.
self.setParameter(self.customParam)

@property
def postStatus(self):
return self.__postStatus

def setPostStatus(self, status):
self.__postStatus = status

@property
def detail(self):
return self.__detail

@property
def id(self):
return self.__id

@property
def startTime(self):
return self.__startTime

@property
def endTime(self):
return self.__endTime

def setStartTime(self, t):
"""设置用例开始时间
Args:
t (str): 时间字符串, 如: '1990-01-01 01:01:01'
"""
self.__startTime = t

def setEndTime(self, t):
"""设置用例结束时间
Args:
t (str): 时间字符串, 如: '1990-01-01 01:01:01'
"""
self.__endTime = t

def _initStatusLogFile(self):
"""遍历所有的测试用例, 初始化写入初始的用例状态.
"""
for tc in self.testCases:
if isinstance(tc, Configuration):
what = "configuration"
elif isinstance(tc, Case):
what = "case"
else:
what = None

_uuid = hashlib.new('md5', Log.LogFileDir + tc.name).hexdigest()
tc.statusUuid = _uuid
_dbStatus = {
"_uuid": _uuid,
"_status": TEST_STATUS.NOT_RUN,
"_what": what,
"_id": tc.getTmssId(),
"_name": tc.name,
"_stage": 'init_case',
"_duration": '0S'
}
self.engine.statusDb.save(**_dbStatus)

def _initTcStatusDb(self, tc, _uuid):
if isinstance(tc, Configuration):
what = "configuration"
elif isinstance(tc, Case):
what = "case"
else:
what = None

tc.statusUuid = _uuid
_dbStatus = {
"_uuid": _uuid,
"_status": TEST_STATUS.NOT_RUN,
"_what": what,
"_id": tc.getTmssId(),
"_name": tc.name,
"_stage": 'init_case',
"_duration": '0S'
}
self.engine.statusDb.save(**_dbStatus)

@property
def logCollectFlag(self):
"""是否进行过日志收集"""
return self.__logCollectFlag

def setLogCollectFlag(self, flag):
"""Set logCollectFlag to flag.
Args:
flag True|False
"""
self.__logCollectFlag = flag

@property
def groupError(self):
"""Group是否存在用例执行是被的标记，用于Group的执行情况检查，从而使stop_on_error可以生效.
"""
return self.__groupError

def setCaseEndTime(self, endTime):
"""设置用例的结束时间.
Args:
endTime (str): case的结束时间.
"""
self.__endTime = endTime

def setParameter(self, customParamList=None):
"""传入从xml中获取的parameter value，设置到parameter中.

Args:
ParamList (list): xml配置的参数list, 默认为None. 如:
[{"name": "lun_type", "value": "thin"},
{"name" :"size", "value": ["10GB", "20GB", ]}, ]

Raises:
ValueException: XML配置的Value不合法.
TypeException: XML返回的parameter类型错误.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setParameter(setParam)

Changes:
2015-05-18 h90006090 优化设置Parameter值设置双重循环

"""
if not customParamList:
return

if not isinstance(customParamList, list):
raise TypeException("Input parameter: '%s' type error, should be list type. " % customParamList)

hasInvalidValue = False

for param in customParamList:
if param["name"] in self.parameters:
parameterObj = self.parameters[param["name"]]
try:
if "values" in param:
if isinstance(param["values"], dict):
parameterObj.setValue([param["values"]["value"]])
if isinstance(param["values"], list):
tmpValue = []
for key in param["values"]:
if isinstance(key["value"], dict):
key['value'] = [key['value']]
tmpValue.append(key["value"])
parameterObj.setValue(tmpValue)
else:
parameterObj.setValue(param["value"])
except (ValueException, TypeException):
logMessage = "Test Set Parameter: {name} has been set to " \
"an invalid value. ".format(name=param["name"])
self.logger.error(logMessage)
hasInvalidValue = True

# 再判断设置的值是否为空.如果getValue出来的值是False，会导致进入if，修改为用None判断
if parameterObj.getValue() is None and parameterObj.isOptional():
logMessage = "A value for: {name} must be specified for. ".format(name=param["name"])
self.logError(logMessage)
hasInvalidValue = True

if hasInvalidValue:
raise ValueException("One or more parameters are "
"invalid, please check log for more information. ")

def addIdentity(self, identity):
"""Case中添加identity

Args:
identity (dict): Case的身份标识.如：
identity = {"name": "YMC", "id": "TC-001"}

Raises:
ValueException: 需要添加的identity已经存在.

"""
if self.hasIdentity({"name": identity["name"]}):
raise ValueException("The identity: '%s' already exists on this test. " % identity["name"])

self.identities["identity"].append(identity)

def getIdentity(self, reqIdentity=None):
"""获取指定名字的identity.

Args:
identityName (dict or None): 需要获取值的identity名称, 默认为None.如：
identityName = {"name": "QW"}.

Returns:
identities (list): 需要获取的指定name的identity.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.getIdentity()

"""
if reqIdentity is None:
return self.identities["identity"]

identities = []
if not self.hasIdentity(reqIdentity):
self.logger.warn("The identity: '%s' has not been provided for the test: '%s'. "
% (reqIdentity, self.name))
return None

for identity in self.identities["identity"]:
if reqIdentity["name"] == identity["name"]:
identities.append(identity)

return identities

def getTmssId(self):
"""get case tmss id.
Returns:
tmssId (str): case tmss id.
"""
if self.hasIdentity({'name': 'tmss_id'}):
for identity in self.identities["identity"]:
if identity["name"] == 'tmss_id':
return identity['id']
else:
return None

def getTmssUri(self):
"""get case tmss Uri.
Returns:
tmssUri (str): case tmss Uri.
"""
if self.hasIdentity({'name': 'uri'}):
for identity in self.identities["identity"]:
if identity["name"] == 'uri':
return identity['id']
else:
return None

def setGroupError(self, flag):
"""设置Group的执行状态标记
Args:
flag (bool): 是否存在错误, True|False.
"""
self.__groupError = flag

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

def setRatsCaseProcessStatus(self, status):
"""设置RatsCase的过程状态，因为caseStatus需要保存执行结果，故而新创建该属性。

用于设置case的状态.

Args:
status (str): case的状态.

Notes:
1、定义的Case的状态为：ConfigError|Running|Pass|Fail|Configured|Kill|NotRun

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setRatsCaseProcessStatus("pass")

"""
status_Units = "|".join(STATUS_UNITS)
statusRegex = "^(" + status_Units + ")$"

if not re.match(r'' + str(statusRegex) + '', status, re.IGNORECASE):
raise ValueException("Case Status: '%s' is undefined. " % status)

self.processStatus = status

def incrementRunNumber(self):
"""设置用例对象执行次数，每次计数加一
"""
self.runNumber += 1

def decrementRunNumber(self):
"""设置用例对象执行次数，每次计数减一， 如果CanRun执行结果为False."""
self.runNumber -= 1

def setFailureReason(self, reason):
"""设置Case执行失败的原因
由controller调用设置.

Args:
reason (str): case执行失败的原因.
"""
self.failureReason = reason

def preTestCase(self):
"""适配引擎运行Group而定义的与Case相同的接口

因为不存在具体执行内容，该步骤一定成功，且在该步骤中不应该存在Group Error.
"""
self.setGroupError(False)

def procedure(self):
"""Group执行的主调度接口, 适配引擎运行Group而定义的与Case相同的接口.
"""
# 如果测试套为并发时，需要记录Group的信息到全局变量中.
self.logger.info("###BBT###: Test Group: %s is a Group or CCT." % self.name)
# self._initStatusLogFile()
if self.parallel:
self.__runGroupInParallel() # Group并发执行.
else:
self.__runGroupInSequential() # Group串行执行.

def logError(self, errorMessage='None', exceptionMsg='None'):
"""记录case的error信息
Args：
errorMessage (str): 记录的error信息.
"""
self.logger.error(errorMessage, exceptionMsg)

def postTestCase(self):
self.setGroupError(False)

def canRun(self):
return True

def setCaseStatus(self, status):
"""设置当前Group的执行结果
Args:
status (str): 测试执行结果.
"""
status_Units = "|".join(STATUS_UNITS)
statusRegex = "^(" + status_Units + ")$"

if not re.match(r'' + str(statusRegex) + '', status, re.IGNORECASE):
raise ValueException("Case Status: '%s' is undefined. " % status)

# 在并发循环时，克隆的用例会回填基础用例状态，当一次执行失败则基础用例的状态应该为失败.
if self.caseStatus == TEST_STATUS.FAILED or self.caseStatus == TEST_STATUS.CONFIG_ERROR:
return
self.caseStatus = status

def killGroupTestThread(self, testCase, th):
"""杀死指定用例的线程
Args:
testCase (instance): 测试用例对象.
th (thread Handle): 线程句柄.

Examples:
self.killTestThread(tc, th)

"""
if th.ident in self.tidToTcLogs:
# print re.sub(r'---0$', "", self.tidToTcLogs[th.ident])
Log.changeGroupCaseLogFile(self.name, Log.LogType.TestCase,
re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
self.logger.debug("Controller Told me Stop! \nThread ID: %s" % th.ident)
Log.releaseFileHandler(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]), self)
Log.changeLogFile(Log.LogType.TestCase, self.name)
testCase.setCaseStatus(TEST_STATUS.KILLED)
th.kill()

def killAllAliveTestCases(self):
"""杀死当前Group中包含的所有用例线程，仅适用与Group并发.
"""
try:
if not self.parallel:
for case in self.testCases:
if case.caseStatus == TEST_STATUS.RUNNING:
case.setCaseStatus(TEST_STATUS.KILLED)

for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = \
TEST_STATUS.KILLED
self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
self.killGroupTestThread(self.tidToTcObject[thChild.ident], thChild)

finally:
__groupTimeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
self.__endTime = __groupTimeNow
self.setCaseStatus(TEST_STATUS.FAILED)
if self.engine.runTestsInParallelFlag:
self.engine.globalTestStatus[self.name]['end_time'] = time.time()

def generateGroupStatus(self):
"""根据当前Group中所有用例的结果，生成当前Group的结果.
"""
__casesStatus = [test.caseStatus for test in self.testCases]

# 如果Group中存在用例失败，Kill， Incomplete时，Group结果为Failed.
for status in [TEST_STATUS.CONFIG_ERROR,
TEST_STATUS.FAILED,
TEST_STATUS.KILLED,
TEST_STATUS.INCOMPLETE]:
if status in __casesStatus:
return TEST_STATUS.FAILED

# 如果Case存在Not_run时， Group为Incomplete.
if TEST_STATUS.NOT_RUN in __casesStatus:
return TEST_STATUS.INCOMPLETE

# 如果Case存在Running时， Group为Incomplete.
if TEST_STATUS.RUNNING in __casesStatus:
return TEST_STATUS.INCOMPLETE

return TEST_STATUS.PASS

def logCaseDetailInfo(self):
"""用例中在class的doc中写入测试用例的详细信息，如测试用例ID，测试用例步骤等，通过该方法记录用例的原始详细信息到日志中
"""
self.logger.info("###BBT###: This Is A Group Test, Parallel is: %s." % self.parallel)

def logParameter(self):
"""记录Case的Parameter.
"""
self.logger.info("Parameter: \n" + str(self.getParameter()))

def getParameter(self, *args):
"""获取指定名字的parameter 的value，未指定名字时返回全部.

Args:
args (list or None): 1个或多个需要获取value的parameter的name，或者不指定返回全部.

Return:
paramValue (dict): key为指定的name， value为parameter value的字典。

Raises:
ValueException: 需要获取的parameter不存在.

Examples:
1、返回全部的parameter：
getParameter();

2、返回指定名称的parameter:
getParameter("name1", "name2")

"""
paramValue = {}

# 如果未指定需要返回value的parameter name
if not args:
for key in self.parameters:
paramValue[key] = self.parameters[key].getValue()
return paramValue

for reqName in args:
if reqName not in self.parameters:
raise ValueException("parameter name: '%s' does not exist. " % reqName)

paramValue[reqName] = self.parameters[reqName].getValue()

return paramValue

def addParameter(self, **kwargs):
"""用例中添加参数, 子类继承重写preTestCase()接口中调用.

Args:
kwargs : 测试用例参数. 为关键字参数，键值对说明如下：
name (str): parameter的名称, 必选参数.
display_name (str): parameter的显示名称, 可选参数.
description (str): parameter的描述信息，可选参数.
default_value (parameterType): parameter的默认值，可选参数，优先级最低, optional为默认和
-False时default_value和assigned_value必须指定一个.
type (str): parameter的值类型，由ParameterType定义，必选参数取值范围为:
-Boolean、Ip_Address、List、Number、Select、Size、Text、
-Time、Multiple_(Boolean、Ip_Address、List、Number、
-Select、Size、Text、Time).
identity (str): parameter的标识, 可选参数.
assigned_value (parameterType): parameter设置值，优先级高于default_value，可选参数.
optional (bool): parameter的值是否时可选的，可选参数，不传入值时默认为False.
validation (dict): parameter对象的validation(校验)值，默认为None.

Returns：
None

Raises:
ValueException: 需要添加的parameter已存在，或没有给定具体的Value.

Notes:
1、传入参数的格式必须为如下格式，参考Examples和参数键值说明：
name='fs_type', # 必要参数.
display_name='filesystem type',
description='ext3 or ext2 or mixed',
default_value='ext3',
validation={'valid_values': ['ext3, ext2']},
type='select', # 必要参数.
identity='id1',
assigned_value='ext2',
optional=True # 必须是布尔型，不给定时默认为True.

Examples:
addParameter(name='fs_type',
display_name='filesystem type',
description='ext3 or ext2 or mixed',
default_value='ext3',
validation={'valid_values': ['ext3', 'ext2']},
type='select',
identity='id1',
assigned_value='ext2',
optional=True)

"""
paramObj = Parameter(kwargs)

if paramObj.name in self.parameters:
raise ValueException("%s: add parameter Fail, "
"parameter: '%s' already exists. " % (self.name, paramObj.name))

if not paramObj.isOptional() and paramObj.getValue() is None:
raise ValueException("%s: add parameter Fail, parameter: '%s' "
"is optional parameter, must be set a value. " % (self.name, paramObj.name))

self.parameters[paramObj.name] = paramObj

def createMetaData(self):

# Parameter Duration for test case procedure()
self.addParameter(name='duration',
display_name='procedure_duration',
description='The test case procedure running duration time.',
type='multiple_time',
identity='bbt_duration',
optional=True)

# Parameter Iterations for test case procedure()
self.addParameter(name='iterations',
display_name='procedure_iterations',
description='The test case procedure running iterations times.',
type='multiple_number',
identity='bbt_iterations',
optional=True)

# Parameter delay_start for test case.
self.addParameter(name='delay_start',
display_name='case_delay_start',
description='The test case delay start time.',
type='multiple_time',
identity='bbt_delay_start',
optional=True)

# Parameter wait_between_iterations for test case procedure().
self.addParameter(name='wait_between_iterations',
display_name='procedure_wait_between_iterations',
description='The test case procedure wait between iterations time.',
type='multiple_time',
identity='bbt_wait_between_iterations',
optional=True)

# Parameter dependency for test case.
self.addParameter(name='dependency',
display_name='case_dependency',
description='The test case dependency case.',
type='multiple_list',
identity='case_dependency',
optional=True)

def __calculationBbtTimeParameter(self, parameter_name):
"""计算BBTCase中需要随机计算时间的参数的随机数."""
parameters = self.getParameter()
parameter = parameters.get(parameter_name)

# 如果参数中不存在parameter_name, 直接返回None.
if not parameter:
return None

# 如果parameter_name中只设置一个值，直接返回该值.
if 1 == len(parameter):
return parameter[0]

# 如果设置了多个值，根据要求，只应该取两个，即index为0，1的值.
elif 2 latest):
latest = group.globalTestStatus[tcName]["end_time"]
if not (earliest and latest):
self.logger.debug("There is not enough runtime to generate the timeline log yet. "
"\n startTime:%s \n latestTime: %s" % (str(earliest), str(latest)))
return

# 创建timeLine日志文件.
timeLineFh = self.setupGroupTimeLog(group)

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
cellDuration = None # 单个单元格的宽度.
numberOfCells = None # 单元格的个数.

def hasMultipleDuration(startTime, endTime, tcDict):
for tc in tcDict:
durationCnt = 0
if tcDict[tc]["start_time"] >= startTime and tcDict[tc]["end_time"] 1:
return False
return True

def cDurationExc():

for cDuration in range(1, 1200):
if cDuration * cells >= duration:
tmp = earliest
while tmp 0:

for index in range(len(self.currentRunningTestThreads) - 1, -1, -1):
th = self.currentRunningTestThreads[index]
# 线程消亡才执行状态检查.
if not th.isAlive():
# 如果当前用例已经消亡，即从正在运行的Case中移除.
self.currentRunningTestThreads.pop(index)
# 线程消亡后，线程数量递减.
runningTestCount -= 1

# 如果线程消亡，但是测试用例的状态为Not_Run证明，在运行前且在等待Dependency时发生错误.
if re.match(r'' + str(TEST_STATUS.NOT_RUN) + '', self.tidToTcObject[th.ident].caseStatus) \
and th.errorMsg != '':
self.logger.error("Test case %s: [Thread ID: %s] threw an error, "
"Maybe check case dependency error.\n, %s"
% (self.tidToTcName[th.ident], th.ident, th.errorMsg))

# 线程消亡. 用例状态只有PASS和失败，只要非PASS则证明用例失败.
if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '',
self.tidToTcObject[th.ident].caseStatus):
self.logger.error("Test case %s: [Thread ID: %s] threw an error, please click "
"the related link to see detail. \n" % (self.tidToTcName[th.ident], th.ident))

# 如果用例失败, 且配置了StopOnError, 且存在其他线程依然存活，则杀掉存活的线程，并设置用例状态.
if self.engine.stopOnError:
self.logger.info("StopOnError is set so Controller is going to "
"kill all the remaining tests")

# TODO 处理stop on error, FOR BBT
for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = \
TEST_STATUS.KILLED
self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
self.killGroupTestThread(self.tidToTcObject[thChild.ident], thChild)

# 如果已经执行杀线程， 再次进行检测， 线程是否全部消亡.

for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
thChild.join() # 如果没有消亡则等待消亡.
self.logger.debug('Finished Or Exit thread %s' % thChild.ident)

runningTestCount = 0 # 正在运行的线程直接赋值为0， 退出循环.
if self.engine.__class__.__name__ != 'BBTRatsEngine':
self.engine.updateStatus()
break

# 如果线程存活，则每隔5分钟记录以及Timeline.
if (time.time() - 300) >= timeSinceLastStatus:
# Group测试结束后更新Group状态.
__groupStatus = self.generateGroupStatus()
__groupTimeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
self.__endTime = __groupTimeNow
self.setCaseStatus(__groupStatus)
if self.engine.runTestsInParallelFlag:
self.engine.globalTestStatus[self.name].update({"end_time": time.time(),
"status": __groupStatus})
self.makeGroupTimeLog(self)
timeSinceLastStatus = time.time()

time.sleep(1)

# 等待线程全部执行完成.
self.engine.waitAllTestComplete(self.currentRunningTestThreads)
# 退出后打印最后的用例状态.
for th in self.currentRunningTestThreads:
logLink = "Log Link" \
"" % (self.name, self.tidToTcLogs[th.ident])

self.logger.info("Test case %s : %s. \n Thread Id: %s.\n %s"
% (self.tidToTcName[th.ident], self.globalTestStatus[self.tidToTcName[th.ident]]["status"],
th.ident, logLink))

def groupTimeLineLogInitial(self):
"""创建时间图片目录，并拷贝时间日志图标到对应的日志目录
"""
timeImgDstPath = os.path.join(Log.LogFileDir, "Images")

# 创建TimeLine.html文件路径变量.
timeLineFileName = os.path.join(Log.LogFileDir, 'TestCases', self.name, "TimeLine.html")

controllerLink = "" \
"View Group Log ----NotRun" % (self.name)

# 创建Images文件夹，并拷贝文件到文件夹.

imagesList = ('5x15StartPass.gif',
'5x15StartFail.gif',
'5x15EndPass.gif',
'5x15EndFail.gif',
'5x15EndKilled.gif',
'5x15ContainedPass.gif',
'5x15ContainedFail.gif',
'5x15Empty.gif',
'15x15RunPass.gif',
'15x15RunFail.gif',
'15x15Empty.gif',
'Legend.jpg')
import shutil

# 拷贝图片到当前执行的日志目录中.
if not os.path.exists(timeImgDstPath):
os.makedirs(timeImgDstPath)
for imgName in imagesList:
path = os.path.split(os.path.realpath(__file__))[0]
shutil.copy(os.path.join(path, "RatsImgs", imgName), os.path.join(timeImgDstPath, imgName))
fh = open(timeLineFileName, "w")
self.engine.writeCssStyleToTimeLog("0", controllerLink, 240, fh)
fh.close()

@staticmethod
def createGroupImageLinks():
"""创建group time line文件中图片的链接
Returns:
imageLink (dict): 图片链接的字典集合.
"""

startPass = ''
startFail = ''
endPass = ''
endFail = ''
endKilled = ''
containedPass = ''
containedFail = ''
empty = ''
runningPass = ''
runningFail = ''
bigEmpty = ''

return {"startPass": startPass, "startFail": startFail, "endPass": endPass,
"endFail": endFail, "endKilled": endKilled, "containedPass": containedPass,
"containFail": containedFail, "empty": empty, "runningPass": runningPass,
"runningFail": runningFail, "bigEmpty": bigEmpty}

# BBTEngine Configuration调度程序.
def runGroupConfiguration(self, configuration, mode='Config'):
"""运行Configuration对象, 适用与并发执行的测试套.

Args:
configuration (Configuration): 测试配置对象.
mode (str) : Configuration的模式, 默认为Config, 取值范围为: "Config", "DeConfig".

"""
if mode not in ['Config', "DeConfig"]:
self.logger.error("RunConfiguration mode is: %s, must be 'Config' or 'DeConfig', "
"Configuration can not be run.")

# 如果参数为Config执行Config
if configuration.getParameter('Mode')['Mode'] == 'Config' and 'Config' == mode:
self.__groupConfiguration(configuration, mode)

# 如果参数为DeConfig执行DeConfig
elif configuration.getParameter('Mode')['Mode'] == 'DeConfig' and 'DeConfig' == mode:
self.__groupConfiguration(configuration, mode)

def __runGroupConfiguration(self, configuration, tcLogFile):
"""运行Configuration对象, 适用与串行执行的测试套.

Args:
configuration (Configuration): 测试配置对象.
tcLogFile (str): 用例对象日志文件名称。
"""
_datetimeStart = datetime.datetime.now()
configuration.setStartTime(_datetimeStart.strftime('%Y-%m-%d %H:%M:%S'))
testName = configuration.name
_start = time.time()
self.logger.tcStart('TestConfig %s starts' % testName)
self.engine.runHooks('beforeConfig')

_dbStatusUpdate = {
'_stage': 'running',
'_status': TEST_STATUS.RUNNING,
'_start': _datetimeStart,
'_end': _datetimeStart
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
# 如果参数为Config执行Config
if configuration.getParameter('Mode')['Mode'] == 'Config':
self.logger.info('####CONFIGURATION MODE####')
try:
configuration.runConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
else:
configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
self.logger.tcEnd('%s has been successfully configured' % testName)

# 如果参数为DeConfig执行DeConfig
elif configuration.getParameter('Mode')['Mode'] == 'DeConfig':
self.logger.info('####DE-CONFIGURATION MODE####')

try:
configuration.deConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
else:
configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)
self.logger.tcEnd('%s has been successfully de-configured' % testName)

_end = datetime.datetime.now()
_dbStatusUpdate = {
'_duration': str(time.time() - _start) + "S",
'_status': TEST_STATUS.PASS,
'_stage': 'done',
'_end': _end,
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
self.engine.runHooks('afterConfig')
Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

def __groupConfiguration(self, configuration, mode='Config'):
"""run configuration.
Args:
configuration (Configuration): 测试配置对象.
mode (str) : Configuration的模式, 默认为Config, 取值范围为: "Config", "DeConfig".

"""
configLogFile = self.engine.createTestCaseLogFile(configuration.name)
tcUuid = Log.changeGroupCaseLogFile(self.name, Log.LogType.TestCase, configLogFile)
self._initTcStatusDb(configuration, tcUuid)
self.logger.tcStart("TestConfig %s starts." % configuration.name)

_datetimeStart = datetime.datetime.now()
_start = time.time()
configuration.setStartTime(_datetimeStart.strftime('%Y-%m-%d %H:%M:%S'))
testName = configuration.name

_dbStatusUpdate = {
'_stage': 'running',
'_status': TEST_STATUS.RUNNING,
'_start': _datetimeStart,
'_end': _datetimeStart
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
self.logger.info('####CONFIGURATION %s MODE####' % mode)

try:
configuration.setCaseStatus(TEST_STATUS.RUNNING)
if 'Config' == mode:
configuration.runConfiguration()
elif 'DeConfig' == mode:
configuration.deConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
self.logger.debug('Configuration: %s, Status: %s' % (configuration.name, configuration.caseStatus))

else:
if mode == 'Config':
configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
elif mode == 'DeConfig':
configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)

self.logger.tcEnd('%s has been successfully %s, Status: %s' % (testName, mode, configuration.caseStatus))

_end = datetime.datetime.now()
_dbStatusUpdate = {
'_end': _end,
'_duration': str(time.time() - _start) + "S",
'_status': TEST_STATUS.PASS,
'_stage': 'done',
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
self.engine.runHooks('afterConfig')
Log.releaseFileHandler(Log.LogType.TestCase, configLogFile)
configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))

def contains_inner_dependency(self, dependency):
"""
用例的依赖是否包含内部状态的依赖
:param dependency:
:return:
"""
for dep in dependency:
if "inner" in dep:
return True
return False

==============================================================================================


#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Group类，用以实例化测试套中配置的类型为test_group和cct的类型.

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

"""

import time
import re
import datetime
import traceback
import threading
import os
import random
import hashlib
from random import choice

from UniAutos import Log
from UniAutos.Log import LogFormat
from UniAutos.Util.Time import sleep
from UniAutos.Util.Units import Units
from UniAutos.Util.TestStatus import TEST_STATUS, STATUS_UNITS
from UniAutos.TestEngine.RatsCase import RatsCase
from UniAutos.TestEngine.Case import Case
from UniAutos.Util.Threads import Threads
from UniAutos.TestEngine.Parameter import Parameter
from UniAutos.Exception.ValueException import ValueException
from UniAutos.Exception.HookException import HookException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.TypeException import TypeException
from UniAutos.TestEngine.Configuration import Configuration


class Group(object):
def __init__(self, parameters):
self.statusUuid = None
self.__testCases = parameters.get('testCases')
self.__parallel = parameters.get('parallel', False)
self.__order = parameters.get('order')
self.name = parameters.get('name', 'TestGroup')
self.testSet = None
self.identities = parameters.get('identities')
self.caseStatus = 'NotRun'
self.__startTime = '1990-01-01 01:01:01'
self.__endTime = '1990-01-01 01:01:01'
self.durationStartTime = time.time()
self.__logger = Log.getLogger(self.__class__.__name__)
self.__testEngine = parameters.pop("engine", None)
self.__logCollectFlag = False
self.parameters = {}

self.tidToTcName = {} # 线程ID和TestCase名称的映射.
self.tidToTcObject = {} # 线程ID和TestCase对象的映射.
self.globalTestStatus = {} # TestCase对象全局状态.
self.tidToTcLogs = {} # 线程ID和TestCase日志文件名称的映射.
self.currentRunningTestThreads = []
self.__groupError = False
self.failureReason = ''
# 错误计数多线程共享
self.errorCount = 0
self.warnCount = 0
self.errorCountSemaphore = threading.Semaphore()
self.warnCountSemaphore = threading.Semaphore()

# 克隆之前的用例唯一ID
self.templateId = parameters.pop("templateId", random.randrange(1000000))

# 定义一个克隆之前的用例对象，用来保存该用例对象的全局状态用来判断当前的用例是否可以执行.
self.baseCaseObject = parameters.pop("base", None)
self.maxRunTime = 0
self.runNumber = 0
self.canRunExecFlag = True
self.debugSwitch = True
self.numberOfExecuted = 0
self.__id = parameters.get('id')
self.__detail = parameters.get('detail')
times = parameters.get("times")
self.totalNumberOfExec = int(times) if times is not None and Units.isNumber(times) else None
self.processStatus = TEST_STATUS.NOT_RUN
self.__postStatus = TEST_STATUS.NOT_RUN

self.customParam = parameters.get("params")
self.resource = parameters.get("resource")
# 测试执行前需要做的比如添加参数.
self.createMetaData()

# 设置testSet中传入的case parameter到case用.
self.setParameter(self.customParam)

@property
def postStatus(self):
return self.__postStatus

def setPostStatus(self, status):
self.__postStatus = status

@property
def detail(self):
return self.__detail

@property
def id(self):
return self.__id

@property
def startTime(self):
return self.__startTime

@property
def endTime(self):
return self.__endTime

def setStartTime(self, t):
"""设置用例开始时间
Args:
t (str): 时间字符串, 如: '1990-01-01 01:01:01'
"""
self.__startTime = t

def setEndTime(self, t):
"""设置用例结束时间
Args:
t (str): 时间字符串, 如: '1990-01-01 01:01:01'
"""
self.__endTime = t

def _initStatusLogFile(self):
"""遍历所有的测试用例, 初始化写入初始的用例状态.
"""
for tc in self.testCases:
if isinstance(tc, Configuration):
what = "configuration"
elif isinstance(tc, Case):
what = "case"
else:
what = None

_uuid = hashlib.new('md5', Log.LogFileDir + tc.name).hexdigest()
tc.statusUuid = _uuid
_dbStatus = {
"_uuid": _uuid,
"_status": TEST_STATUS.NOT_RUN,
"_what": what,
"_id": tc.getTmssId(),
"_name": tc.name,
"_stage": 'init_case',
"_duration": '0S'
}
self.engine.statusDb.save(**_dbStatus)

def _initTcStatusDb(self, tc, _uuid):
if isinstance(tc, Configuration):
what = "configuration"
elif isinstance(tc, Case):
what = "case"
else:
what = None

tc.statusUuid = _uuid
_dbStatus = {
"_uuid": _uuid,
"_status": TEST_STATUS.NOT_RUN,
"_what": what,
"_id": tc.getTmssId(),
"_name": tc.name,
"_stage": 'init_case',
"_duration": '0S'
}
self.engine.statusDb.save(**_dbStatus)

@property
def logCollectFlag(self):
"""是否进行过日志收集"""
return self.__logCollectFlag

def setLogCollectFlag(self, flag):
"""Set logCollectFlag to flag.
Args:
flag True|False
"""
self.__logCollectFlag = flag

@property
def groupError(self):
"""Group是否存在用例执行是被的标记，用于Group的执行情况检查，从而使stop_on_error可以生效.
"""
return self.__groupError

def setCaseEndTime(self, endTime):
"""设置用例的结束时间.
Args:
endTime (str): case的结束时间.
"""
self.__endTime = endTime

def setParameter(self, customParamList=None):
"""传入从xml中获取的parameter value，设置到parameter中.

Args:
ParamList (list): xml配置的参数list, 默认为None. 如:
[{"name": "lun_type", "value": "thin"},
{"name" :"size", "value": ["10GB", "20GB", ]}, ]

Raises:
ValueException: XML配置的Value不合法.
TypeException: XML返回的parameter类型错误.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setParameter(setParam)

Changes:
2015-05-18 h90006090 优化设置Parameter值设置双重循环

"""
if not customParamList:
return

if not isinstance(customParamList, list):
raise TypeException("Input parameter: '%s' type error, should be list type. " % customParamList)

hasInvalidValue = False

for param in customParamList:
if param["name"] in self.parameters:
parameterObj = self.parameters[param["name"]]
try:
if "values" in param:
if isinstance(param["values"], dict):
parameterObj.setValue([param["values"]["value"]])
if isinstance(param["values"], list):
tmpValue = []
for key in param["values"]:
if isinstance(key["value"], dict):
key['value'] = [key['value']]
tmpValue.append(key["value"])
parameterObj.setValue(tmpValue)
else:
parameterObj.setValue(param["value"])
except (ValueException, TypeException):
logMessage = "Test Set Parameter: {name} has been set to " \
"an invalid value. ".format(name=param["name"])
self.logger.error(logMessage)
hasInvalidValue = True

# 再判断设置的值是否为空.如果getValue出来的值是False，会导致进入if，修改为用None判断
if parameterObj.getValue() is None and parameterObj.isOptional():
logMessage = "A value for: {name} must be specified for. ".format(name=param["name"])
self.logError(logMessage)
hasInvalidValue = True

if hasInvalidValue:
raise ValueException("One or more parameters are "
"invalid, please check log for more information. ")

def addIdentity(self, identity):
"""Case中添加identity

Args:
identity (dict): Case的身份标识.如：
identity = {"name": "YMC", "id": "TC-001"}

Raises:
ValueException: 需要添加的identity已经存在.

"""
if self.hasIdentity({"name": identity["name"]}):
raise ValueException("The identity: '%s' already exists on this test. " % identity["name"])

self.identities["identity"].append(identity)

def getIdentity(self, reqIdentity=None):
"""获取指定名字的identity.

Args:
identityName (dict or None): 需要获取值的identity名称, 默认为None.如：
identityName = {"name": "QW"}.

Returns:
identities (list): 需要获取的指定name的identity.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.getIdentity()

"""
if reqIdentity is None:
return self.identities["identity"]

identities = []
if not self.hasIdentity(reqIdentity):
self.logger.warn("The identity: '%s' has not been provided for the test: '%s'. "
% (reqIdentity, self.name))
return None

for identity in self.identities["identity"]:
if reqIdentity["name"] == identity["name"]:
identities.append(identity)

return identities

def getTmssId(self):
"""get case tmss id.
Returns:
tmssId (str): case tmss id.
"""
if self.hasIdentity({'name': 'tmss_id'}):
for identity in self.identities["identity"]:
if identity["name"] == 'tmss_id':
return identity['id']
else:
return None

def getTmssUri(self):
"""get case tmss Uri.
Returns:
tmssUri (str): case tmss Uri.
"""
if self.hasIdentity({'name': 'uri'}):
for identity in self.identities["identity"]:
if identity["name"] == 'uri':
return identity['id']
else:
return None

def setGroupError(self, flag):
"""设置Group的执行状态标记
Args:
flag (bool): 是否存在错误, True|False.
"""
self.__groupError = flag

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

def setRatsCaseProcessStatus(self, status):
"""设置RatsCase的过程状态，因为caseStatus需要保存执行结果，故而新创建该属性。

用于设置case的状态.

Args:
status (str): case的状态.

Notes:
1、定义的Case的状态为：ConfigError|Running|Pass|Fail|Configured|Kill|NotRun

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setRatsCaseProcessStatus("pass")

"""
status_Units = "|".join(STATUS_UNITS)
statusRegex = "^(" + status_Units + ")$"

if not re.match(r'' + str(statusRegex) + '', status, re.IGNORECASE):
raise ValueException("Case Status: '%s' is undefined. " % status)

self.processStatus = status

def incrementRunNumber(self):
"""设置用例对象执行次数，每次计数加一
"""
self.runNumber += 1

def decrementRunNumber(self):
"""设置用例对象执行次数，每次计数减一， 如果CanRun执行结果为False."""
self.runNumber -= 1

def setFailureReason(self, reason):
"""设置Case执行失败的原因
由controller调用设置.

Args:
reason (str): case执行失败的原因.
"""
self.failureReason = reason

def preTestCase(self):
"""适配引擎运行Group而定义的与Case相同的接口

因为不存在具体执行内容，该步骤一定成功，且在该步骤中不应该存在Group Error.
"""
self.setGroupError(False)

def procedure(self):
"""Group执行的主调度接口, 适配引擎运行Group而定义的与Case相同的接口.
"""
# 如果测试套为并发时，需要记录Group的信息到全局变量中.
self.logger.info("###BBT###: Test Group: %s is a Group or CCT." % self.name)
# self._initStatusLogFile()
if self.parallel:
self.__runGroupInParallel() # Group并发执行.
else:
self.__runGroupInSequential() # Group串行执行.

def logError(self, errorMessage='None', exceptionMsg='None'):
"""记录case的error信息
Args：
errorMessage (str): 记录的error信息.
"""
self.logger.error(errorMessage, exceptionMsg)

def postTestCase(self):
self.setGroupError(False)

def canRun(self):
return True

def setCaseStatus(self, status):
"""设置当前Group的执行结果
Args:
status (str): 测试执行结果.
"""
status_Units = "|".join(STATUS_UNITS)
statusRegex = "^(" + status_Units + ")$"

if not re.match(r'' + str(statusRegex) + '', status, re.IGNORECASE):
raise ValueException("Case Status: '%s' is undefined. " % status)

# 在并发循环时，克隆的用例会回填基础用例状态，当一次执行失败则基础用例的状态应该为失败.
if self.caseStatus == TEST_STATUS.FAILED or self.caseStatus == TEST_STATUS.CONFIG_ERROR:
return
self.caseStatus = status

def killGroupTestThread(self, testCase, th):
"""杀死指定用例的线程
Args:
testCase (instance): 测试用例对象.
th (thread Handle): 线程句柄.

Examples:
self.killTestThread(tc, th)

"""
if th.ident in self.tidToTcLogs:
# print re.sub(r'---0$', "", self.tidToTcLogs[th.ident])
Log.changeGroupCaseLogFile(self.name, Log.LogType.TestCase,
re.sub(r'---0$', "", self.tidToTcLogs[th.ident]))
self.logger.debug("Controller Told me Stop! \nThread ID: %s" % th.ident)
Log.releaseFileHandler(Log.LogType.TestCase, re.sub(r'---0$', "", self.tidToTcLogs[th.ident]), self)
Log.changeLogFile(Log.LogType.TestCase, self.name)
testCase.setCaseStatus(TEST_STATUS.KILLED)
th.kill()

def killAllAliveTestCases(self):
"""杀死当前Group中包含的所有用例线程，仅适用与Group并发.
"""
try:
if not self.parallel:
for case in self.testCases:
if case.caseStatus == TEST_STATUS.RUNNING:
case.setCaseStatus(TEST_STATUS.KILLED)

for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = \
TEST_STATUS.KILLED
self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
self.killGroupTestThread(self.tidToTcObject[thChild.ident], thChild)

finally:
__groupTimeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
self.__endTime = __groupTimeNow
self.setCaseStatus(TEST_STATUS.FAILED)
if self.engine.runTestsInParallelFlag:
self.engine.globalTestStatus[self.name]['end_time'] = time.time()

def generateGroupStatus(self):
"""根据当前Group中所有用例的结果，生成当前Group的结果.
"""
__casesStatus = [test.caseStatus for test in self.testCases]

# 如果Group中存在用例失败，Kill， Incomplete时，Group结果为Failed.
for status in [TEST_STATUS.CONFIG_ERROR,
TEST_STATUS.FAILED,
TEST_STATUS.KILLED,
TEST_STATUS.INCOMPLETE]:
if status in __casesStatus:
return TEST_STATUS.FAILED

# 如果Case存在Not_run时， Group为Incomplete.
if TEST_STATUS.NOT_RUN in __casesStatus:
return TEST_STATUS.INCOMPLETE

# 如果Case存在Running时， Group为Incomplete.
if TEST_STATUS.RUNNING in __casesStatus:
return TEST_STATUS.INCOMPLETE

return TEST_STATUS.PASS

def logCaseDetailInfo(self):
"""用例中在class的doc中写入测试用例的详细信息，如测试用例ID，测试用例步骤等，通过该方法记录用例的原始详细信息到日志中
"""
self.logger.info("###BBT###: This Is A Group Test, Parallel is: %s." % self.parallel)

def logParameter(self):
"""记录Case的Parameter.
"""
self.logger.info("Parameter: \n" + str(self.getParameter()))

def getParameter(self, *args):
"""获取指定名字的parameter 的value，未指定名字时返回全部.

Args:
args (list or None): 1个或多个需要获取value的parameter的name，或者不指定返回全部.

Return:
paramValue (dict): key为指定的name， value为parameter value的字典。

Raises:
ValueException: 需要获取的parameter不存在.

Examples:
1、返回全部的parameter：
getParameter();

2、返回指定名称的parameter:
getParameter("name1", "name2")

"""
paramValue = {}

# 如果未指定需要返回value的parameter name
if not args:
for key in self.parameters:
paramValue[key] = self.parameters[key].getValue()
return paramValue

for reqName in args:
if reqName not in self.parameters:
raise ValueException("parameter name: '%s' does not exist. " % reqName)

paramValue[reqName] = self.parameters[reqName].getValue()

return paramValue

def addParameter(self, **kwargs):
"""用例中添加参数, 子类继承重写preTestCase()接口中调用.

Args:
kwargs : 测试用例参数. 为关键字参数，键值对说明如下：
name (str): parameter的名称, 必选参数.
display_name (str): parameter的显示名称, 可选参数.
description (str): parameter的描述信息，可选参数.
default_value (parameterType): parameter的默认值，可选参数，优先级最低, optional为默认和
-False时default_value和assigned_value必须指定一个.
type (str): parameter的值类型，由ParameterType定义，必选参数取值范围为:
-Boolean、Ip_Address、List、Number、Select、Size、Text、
-Time、Multiple_(Boolean、Ip_Address、List、Number、
-Select、Size、Text、Time).
identity (str): parameter的标识, 可选参数.
assigned_value (parameterType): parameter设置值，优先级高于default_value，可选参数.
optional (bool): parameter的值是否时可选的，可选参数，不传入值时默认为False.
validation (dict): parameter对象的validation(校验)值，默认为None.

Returns：
None

Raises:
ValueException: 需要添加的parameter已存在，或没有给定具体的Value.

Notes:
1、传入参数的格式必须为如下格式，参考Examples和参数键值说明：
name='fs_type', # 必要参数.
display_name='filesystem type',
description='ext3 or ext2 or mixed',
default_value='ext3',
validation={'valid_values': ['ext3, ext2']},
type='select', # 必要参数.
identity='id1',
assigned_value='ext2',
optional=True # 必须是布尔型，不给定时默认为True.

Examples:
addParameter(name='fs_type',
display_name='filesystem type',
description='ext3 or ext2 or mixed',
default_value='ext3',
validation={'valid_values': ['ext3', 'ext2']},
type='select',
identity='id1',
assigned_value='ext2',
optional=True)

"""
paramObj = Parameter(kwargs)

if paramObj.name in self.parameters:
raise ValueException("%s: add parameter Fail, "
"parameter: '%s' already exists. " % (self.name, paramObj.name))

if not paramObj.isOptional() and paramObj.getValue() is None:
raise ValueException("%s: add parameter Fail, parameter: '%s' "
"is optional parameter, must be set a value. " % (self.name, paramObj.name))

self.parameters[paramObj.name] = paramObj

def createMetaData(self):

# Parameter Duration for test case procedure()
self.addParameter(name='duration',
display_name='procedure_duration',
description='The test case procedure running duration time.',
type='multiple_time',
identity='bbt_duration',
optional=True)

# Parameter Iterations for test case procedure()
self.addParameter(name='iterations',
display_name='procedure_iterations',
description='The test case procedure running iterations times.',
type='multiple_number',
identity='bbt_iterations',
optional=True)

# Parameter delay_start for test case.
self.addParameter(name='delay_start',
display_name='case_delay_start',
description='The test case delay start time.',
type='multiple_time',
identity='bbt_delay_start',
optional=True)

# Parameter wait_between_iterations for test case procedure().
self.addParameter(name='wait_between_iterations',
display_name='procedure_wait_between_iterations',
description='The test case procedure wait between iterations time.',
type='multiple_time',
identity='bbt_wait_between_iterations',
optional=True)

# Parameter dependency for test case.
self.addParameter(name='dependency',
display_name='case_dependency',
description='The test case dependency case.',
type='multiple_list',
identity='case_dependency',
optional=True)

def __calculationBbtTimeParameter(self, parameter_name):
"""计算BBTCase中需要随机计算时间的参数的随机数."""
parameters = self.getParameter()
parameter = parameters.get(parameter_name)

# 如果参数中不存在parameter_name, 直接返回None.
if not parameter:
return None

# 如果parameter_name中只设置一个值，直接返回该值.
if 1 == len(parameter):
return parameter[0]

# 如果设置了多个值，根据要求，只应该取两个，即index为0，1的值.
elif 2 latest):
latest = group.globalTestStatus[tcName]["end_time"]
if not (earliest and latest):
self.logger.debug("There is not enough runtime to generate the timeline log yet. "
"\n startTime:%s \n latestTime: %s" % (str(earliest), str(latest)))
return

# 创建timeLine日志文件.
timeLineFh = self.setupGroupTimeLog(group)

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
cellDuration = None # 单个单元格的宽度.
numberOfCells = None # 单元格的个数.

def hasMultipleDuration(startTime, endTime, tcDict):
for tc in tcDict:
durationCnt = 0
if tcDict[tc]["start_time"] >= startTime and tcDict[tc]["end_time"] 1:
return False
return True

def cDurationExc():

for cDuration in range(1, 1200):
if cDuration * cells >= duration:
tmp = earliest
while tmp 0:

for index in range(len(self.currentRunningTestThreads) - 1, -1, -1):
th = self.currentRunningTestThreads[index]
# 线程消亡才执行状态检查.
if not th.isAlive():
# 如果当前用例已经消亡，即从正在运行的Case中移除.
self.currentRunningTestThreads.pop(index)
# 线程消亡后，线程数量递减.
runningTestCount -= 1

# 如果线程消亡，但是测试用例的状态为Not_Run证明，在运行前且在等待Dependency时发生错误.
if re.match(r'' + str(TEST_STATUS.NOT_RUN) + '', self.tidToTcObject[th.ident].caseStatus) \
and th.errorMsg != '':
self.logger.error("Test case %s: [Thread ID: %s] threw an error, "
"Maybe check case dependency error.\n, %s"
% (self.tidToTcName[th.ident], th.ident, th.errorMsg))

# 线程消亡. 用例状态只有PASS和失败，只要非PASS则证明用例失败.
if re.match(r'' + str(TEST_STATUS.FAILED) + '|' + str(TEST_STATUS.CONFIG_ERROR) + '',
self.tidToTcObject[th.ident].caseStatus):
self.logger.error("Test case %s: [Thread ID: %s] threw an error, please click "
"the related link to see detail. \n" % (self.tidToTcName[th.ident], th.ident))

# 如果用例失败, 且配置了StopOnError, 且存在其他线程依然存活，则杀掉存活的线程，并设置用例状态.
if self.engine.stopOnError:
self.logger.info("StopOnError is set so Controller is going to "
"kill all the remaining tests")

# TODO 处理stop on error, FOR BBT
for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
self.globalTestStatus[self.tidToTcName[thChild.ident]]["status"] = \
TEST_STATUS.KILLED
self.globalTestStatus[self.tidToTcName[thChild.ident]]["end_time"] = time.time()
self.killGroupTestThread(self.tidToTcObject[thChild.ident], thChild)

# 如果已经执行杀线程， 再次进行检测， 线程是否全部消亡.

for thChild in self.currentRunningTestThreads:
if thChild.isAlive():
thChild.join() # 如果没有消亡则等待消亡.
self.logger.debug('Finished Or Exit thread %s' % thChild.ident)

runningTestCount = 0 # 正在运行的线程直接赋值为0， 退出循环.
if self.engine.__class__.__name__ != 'BBTRatsEngine':
self.engine.updateStatus()
break

# 如果线程存活，则每隔5分钟记录以及Timeline.
if (time.time() - 300) >= timeSinceLastStatus:
# Group测试结束后更新Group状态.
__groupStatus = self.generateGroupStatus()
__groupTimeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
self.__endTime = __groupTimeNow
self.setCaseStatus(__groupStatus)
if self.engine.runTestsInParallelFlag:
self.engine.globalTestStatus[self.name].update({"end_time": time.time(),
"status": __groupStatus})
self.makeGroupTimeLog(self)
timeSinceLastStatus = time.time()

time.sleep(1)

# 等待线程全部执行完成.
self.engine.waitAllTestComplete(self.currentRunningTestThreads)
# 退出后打印最后的用例状态.
for th in self.currentRunningTestThreads:
logLink = "Log Link" \
"" % (self.name, self.tidToTcLogs[th.ident])

self.logger.info("Test case %s : %s. \n Thread Id: %s.\n %s"
% (self.tidToTcName[th.ident], self.globalTestStatus[self.tidToTcName[th.ident]]["status"],
th.ident, logLink))

def groupTimeLineLogInitial(self):
"""创建时间图片目录，并拷贝时间日志图标到对应的日志目录
"""
timeImgDstPath = os.path.join(Log.LogFileDir, "Images")

# 创建TimeLine.html文件路径变量.
timeLineFileName = os.path.join(Log.LogFileDir, 'TestCases', self.name, "TimeLine.html")

controllerLink = "" \
"View Group Log ----NotRun" % (self.name)

# 创建Images文件夹，并拷贝文件到文件夹.

imagesList = ('5x15StartPass.gif',
'5x15StartFail.gif',
'5x15EndPass.gif',
'5x15EndFail.gif',
'5x15EndKilled.gif',
'5x15ContainedPass.gif',
'5x15ContainedFail.gif',
'5x15Empty.gif',
'15x15RunPass.gif',
'15x15RunFail.gif',
'15x15Empty.gif',
'Legend.jpg')
import shutil

# 拷贝图片到当前执行的日志目录中.
if not os.path.exists(timeImgDstPath):
os.makedirs(timeImgDstPath)
for imgName in imagesList:
path = os.path.split(os.path.realpath(__file__))[0]
shutil.copy(os.path.join(path, "RatsImgs", imgName), os.path.join(timeImgDstPath, imgName))
fh = open(timeLineFileName, "w")
self.engine.writeCssStyleToTimeLog("0", controllerLink, 240, fh)
fh.close()

@staticmethod
def createGroupImageLinks():
"""创建group time line文件中图片的链接
Returns:
imageLink (dict): 图片链接的字典集合.
"""

startPass = ''
startFail = ''
endPass = ''
endFail = ''
endKilled = ''
containedPass = ''
containedFail = ''
empty = ''
runningPass = ''
runningFail = ''
bigEmpty = ''

return {"startPass": startPass, "startFail": startFail, "endPass": endPass,
"endFail": endFail, "endKilled": endKilled, "containedPass": containedPass,
"containFail": containedFail, "empty": empty, "runningPass": runningPass,
"runningFail": runningFail, "bigEmpty": bigEmpty}

# BBTEngine Configuration调度程序.
def runGroupConfiguration(self, configuration, mode='Config'):
"""运行Configuration对象, 适用与并发执行的测试套.

Args:
configuration (Configuration): 测试配置对象.
mode (str) : Configuration的模式, 默认为Config, 取值范围为: "Config", "DeConfig".

"""
if mode not in ['Config', "DeConfig"]:
self.logger.error("RunConfiguration mode is: %s, must be 'Config' or 'DeConfig', "
"Configuration can not be run.")

# 如果参数为Config执行Config
if configuration.getParameter('Mode')['Mode'] == 'Config' and 'Config' == mode:
self.__groupConfiguration(configuration, mode)

# 如果参数为DeConfig执行DeConfig
elif configuration.getParameter('Mode')['Mode'] == 'DeConfig' and 'DeConfig' == mode:
self.__groupConfiguration(configuration, mode)

def __runGroupConfiguration(self, configuration, tcLogFile):
"""运行Configuration对象, 适用与串行执行的测试套.

Args:
configuration (Configuration): 测试配置对象.
tcLogFile (str): 用例对象日志文件名称。
"""
_datetimeStart = datetime.datetime.now()
configuration.setStartTime(_datetimeStart.strftime('%Y-%m-%d %H:%M:%S'))
testName = configuration.name
_start = time.time()
self.logger.tcStart('TestConfig %s starts' % testName)
self.engine.runHooks('beforeConfig')

_dbStatusUpdate = {
'_stage': 'running',
'_status': TEST_STATUS.RUNNING,
'_start': _datetimeStart,
'_end': _datetimeStart
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
# 如果参数为Config执行Config
if configuration.getParameter('Mode')['Mode'] == 'Config':
self.logger.info('####CONFIGURATION MODE####')
try:
configuration.runConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
else:
configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
self.logger.tcEnd('%s has been successfully configured' % testName)

# 如果参数为DeConfig执行DeConfig
elif configuration.getParameter('Mode')['Mode'] == 'DeConfig':
self.logger.info('####DE-CONFIGURATION MODE####')

try:
configuration.deConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
else:
configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)
self.logger.tcEnd('%s has been successfully de-configured' % testName)

_end = datetime.datetime.now()
_dbStatusUpdate = {
'_duration': str(time.time() - _start) + "S",
'_status': TEST_STATUS.PASS,
'_stage': 'done',
'_end': _end,
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))
self.engine.runHooks('afterConfig')
Log.releaseFileHandler(Log.LogType.TestCase, tcLogFile)

def __groupConfiguration(self, configuration, mode='Config'):
"""run configuration.
Args:
configuration (Configuration): 测试配置对象.
mode (str) : Configuration的模式, 默认为Config, 取值范围为: "Config", "DeConfig".

"""
configLogFile = self.engine.createTestCaseLogFile(configuration.name)
tcUuid = Log.changeGroupCaseLogFile(self.name, Log.LogType.TestCase, configLogFile)
self._initTcStatusDb(configuration, tcUuid)
self.logger.tcStart("TestConfig %s starts." % configuration.name)

_datetimeStart = datetime.datetime.now()
_start = time.time()
configuration.setStartTime(_datetimeStart.strftime('%Y-%m-%d %H:%M:%S'))
testName = configuration.name

_dbStatusUpdate = {
'_stage': 'running',
'_status': TEST_STATUS.RUNNING,
'_start': _datetimeStart,
'_end': _datetimeStart
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
self.logger.info('####CONFIGURATION %s MODE####' % mode)

try:
configuration.setCaseStatus(TEST_STATUS.RUNNING)
if 'Config' == mode:
configuration.runConfiguration()
elif 'DeConfig' == mode:
configuration.deConfiguration()
except Exception, err:
self.logger.error("Config Script failed: \n %s, \nDetail: %s" %
(err.message, traceback.format_exc()))
self._handleException(configuration, err, 'main')
self.logger.debug('Configuration: %s, Status: %s' % (configuration.name, configuration.caseStatus))

else:
if mode == 'Config':
configuration.setCaseStatus(TEST_STATUS.CONFIGURED)
elif mode == 'DeConfig':
configuration.setCaseStatus(TEST_STATUS.DE_CONFIGURED)

self.logger.tcEnd('%s has been successfully %s, Status: %s' % (testName, mode, configuration.caseStatus))

_end = datetime.datetime.now()
_dbStatusUpdate = {
'_end': _end,
'_duration': str(time.time() - _start) + "S",
'_status': TEST_STATUS.PASS,
'_stage': 'done',
}
self.engine.statusDb.update(configuration.statusUuid, **_dbStatusUpdate)
self.engine.runHooks('afterConfig')
Log.releaseFileHandler(Log.LogType.TestCase, configLogFile)
configuration.setEndTime(_end.strftime('%Y-%m-%d %H:%M:%S'))

def contains_inner_dependency(self, dependency):
"""
用例的依赖是否包含内部状态的依赖
:param dependency:
:return:
"""
for dep in dependency:
if "inner" in dep:
return True
return False