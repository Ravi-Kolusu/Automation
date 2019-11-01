Base ::

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Base为测试用例基类，Case、Configuration的父类

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

"""

import re
import os
import threading
import pprint
import warnings
import difflib
import sys
import collections
from .util import (
strclass, safe_repr, unorderable_list_difference,
_count_diff_all_purpose, _count_diff_hashable
)

from UniAutos.Component.ComponentBase import ComponentBase
from UniAutos.TestEngine.Set import Set
from UniAutos.TestEngine.Parameter import Parameter
from UniAutos import Log
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Util.Units import Units
from UniAutos.Exception.ValueException import ValueException
from UniAutos.Exception.TypeException import TypeException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Util.TestStatus import TEST_STATUS, STATUS_UNITS
from UniAutos.Requirement.ConfigureInfoBase import ConfigureInfoBase
from UniAutos.Requirement.ConfigureEnv import wipeConfig

_MAX_LENGTH = 80
DIFF_OMITTED = '\nDiff is %s characters long. Set self.maxDiff to None to see it.'


class _AssertRaisesContext(object):
"""A context manager used to implement TestCase.assertRaises* methods."""

def __init__(self, expected, test_case, expected_regexp=None):
self.expected = expected
self.failureException = test_case.failureException
self.expected_regexp = expected_regexp

def __enter__(self):
return self

def __exit__(self, exc_type, exc_value, tb):
if exc_type is None:
try:
exc_name = self.expected.__name__
except AttributeError:
exc_name = str(self.expected)
raise self.failureException(
"{0} not raised".format(exc_name))
if not issubclass(exc_type, self.expected):
# let unexpected exceptions pass through
return False
self.exception = exc_value # store for later retrieval
if self.expected_regexp is None:
return True

expected_regexp = self.expected_regexp
if not expected_regexp.search(str(exc_value)):
raise self.failureException('"%s" does not match "%s"' %
(expected_regexp.pattern, str(exc_value)))
return True


class Base(object):
"""测试用例基类

功能说明：定义测试用例接口.

Args:
caseValidation (dict): testSet传入的Case使用的数据.格式如下：
test_validation = {"name": "",
"path": "",
"resource": None,
"params": [],
"description": '',
"tags": [],
"required_equipment": [],
"steps_to_perform": [],
"shareable_equipment": 0,
"identities": {"identity": [{"name": "ax_id", "value": 1}, ]},
"instance_id": "",
"order": 1,
"dependencies": {}}

Attributes:
self.caseStatus (str) : case的状态, 默认为NOT_RUN.
self.name (str) : case名称.
self.path (str) : case包路径.
self.tags (list) : case关键字.
self.requiredEquipment (list) : Equipment list, 测试需要的配置、设备、软件.
self.customParam (list) : 传入的xml配置的parameter.
self.resource (instance) : 测试资源信息，为resource对象.
-如： [{"10.245.235.114":
{"cs0": "10.245.235.114", "type": "file"}}, ].
self.identities (dict) : case标识.
# self.dependencies (dict) : Case的测试依赖. 如：self.dependencies = {"dependency": {"..":"..", ..}.
self.order (int) : Case在测试中的执行顺序标识, 如：1.
self.logger (instance) : Logger对象.
self.parameters (dict) : Case的parameter, 用于存储多个parameter对象, 初始化为空的dict.
self.testSteps (list) : Case的测试步骤, 由addStep()接口添加测试的步骤, 默认为空.
self.testSet (instance) : Case所属的testSet对象, 默认为None，由setTestSet()接口设置.
self.casePackageName (str) : Case package name , 用于创建TestCase实例对象.
self.failureReason (str) : 定义case失败的原因，默认为None.
self.runNumber (int) : 用于记录用例对象并发执行的次数.

Returns:
Base (instance): Base类实例对象.

Raises:
None

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)

"""

failureException = AssertionError

maxDiff = 80 * 8

longMessage = False

_diffThreshold = 2 ** 16

# Attribute used by TestSuite for classSetUp

_classSetupFailed = False

@validateParam(case=dict)
def __init__(self, parameters):
super(Base, self).__init__()

# 初始化Requirement, 这种数据结构是为了后续再添加其他类型的requirement.
self.requirement = {"requirement_configuration": []} # key为component类型，value为component对象列表.
self.cleanupConfiguration = True
self.__logCollectFlag = False
self.statusUuid = None

# handle Exception
self.handleErrorCount = 0
self.handleWarnCount = 0
self.handleErrorMsg = ''
self.handleWarnMsg = ''

# 错误计数多线程共享
self.errorCount = 0
self.warnCount = 0
self.errorCountSemaphore = threading.Semaphore()
self.warnCountSemaphore = threading.Semaphore()
self.caseStatus = TEST_STATUS.NOT_RUN
self.processStatus = TEST_STATUS.NOT_RUN
self.name = parameters["name"]
self.path = parameters["location"]
self.tags = parameters.get("tags")
times = parameters.get("times")
self.debugSwitch = True
self.totalNumberOfExec = int(times) if times is not None and Units.isNumber(times) else None
self.numberOfExecuted = 0
self.requiredEquipment = parameters.get("required_equipment")
self.customParam = parameters.get("params")
self.identities = parameters.get("identities")
self.resource = parameters.get("resource")
self.description = parameters.get("description")
self.shareableEquipment = parameters.get("shareable_equipment")
self.instanceId = parameters.get("instance_id")
# self.dependencies = parameters.get("dependencies")
self.order = parameters.get("order")
self.logger = Log.getLogger(str(self.__module__))
self.parameters = {}
self.cleanupStacks = []
self.testSteps = parameters.get("steps_to_perform")
self.alias = parameters.get('alias')
self.inner = None
self.testSet = None
self.casePackageName = re.sub(r'/|\\', ".", self.path)
self.failureReason = ''

# 2015/09/28 h90006090 Add test case startTime and endTime use to tmss fillback.
self.__startTime = '1990-01-01 01:01:01'
self.__endTime = '1990-01-01 01:01:01'
self.__postStatus = TEST_STATUS.NOT_RUN
# self.stopOnKillFlag = False

# 测试执行前需要做的比如添加参数.
self.createMetaData()

# 设置testSet中传入的case parameter到case用.
self.setParameter(self.customParam)

self.configEnvCreateComponents = []
self.createRequirement()
# Map types to custom assertEqual functions that will compare
# instances of said type in more detail to generate a more useful
# error message.
self._type_equality_funcs = {}
self.addTypeEqualityFunc(dict, 'assertDictEqual')
self.addTypeEqualityFunc(list, 'assertListEqual')
self.addTypeEqualityFunc(tuple, 'assertTupleEqual')
self.addTypeEqualityFunc(set, 'assertSetEqual')
self.addTypeEqualityFunc(frozenset, 'assertSetEqual')
try:
self.addTypeEqualityFunc(unicode, 'assertMultiLineEqual')
except NameError:
# No unicode support in this build
pass

@property
def postStatus(self):
return self.__postStatus

def setPostStatus(self, status):
self.__postStatus = status

@property
def baseLogLocation(self):
"""当前日志的Base路径"""
return Log.LogFileDir

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

@property
def randomFaults(self):
"""All random faults, default is {}.
"""
return self.testSet.randomFaults

@property
def currentRandomFault(self):
"""current random fault.
"""
return self.testSet.currentRandomFault

def resetCurrentRandomFault(self):
"""call set resetCurrentRandomFault() to reset currentRandomFault.
"""
self.testSet.resetCurrentRandomFault()

def setCustomFailureReason(self, failureReason):
"""设置测试用例的失败原因
Args：
failureReason (str): Test case's failure reason, the max length is 256.
"""
self.failureReason += failureReason
if len(self.failureReason) > 256:
self.failureReason = self.failureReason[:256]

def addTypeEqualityFunc(self, typeobj, function):
"""Add a type specific assertEqual style function to compare a type.

This method is for use by TestCase subclasses that need to register
their own type equality functions to provide nicer error messages.

Args:
typeobj: The data type to call this function on when both values
are of the same type in assertEqual().
function: The callable taking two arguments and an optional
msg= argument that raises self.failureException with a
useful error message when the two arguments are not equal.
"""
self._type_equality_funcs[typeobj] = function

def setCaseEndTime(self, endTime):
"""设置用例的结束时间.
Args:
endTime (str): case的结束时间.
"""
self.__endTime = endTime


@validateParam(description=str)
def setDescription(self, description):
"""设置self.__testValidation中的该要描述

Args:
description (str): Case的描述信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.setDescription(description)

"""
self.description = description

@validateParam(descriptionMessage=str)
def logCaseDescriptions(self, descriptionMessage):
"""记录Case的描述信息

Args:
descriptionMessage (str)： 需要记录的信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logCaseDescriptions(descriptionMessage)

"""
self.logger.info(descriptionMessage)

def setName(self, customName):
"""并发执行多个相同的用例时，名字需要重新设置
"""
self.name = customName

@validateParam(testSetObj=Set)
def setTestSet(self, testSetObj):
"""设置Case的TestSet

Args:
testSetObj (instance): testSet对象.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.setTestSet(testSetObj)

"""
self.testSet = testSetObj

def createMetaData(self):
"""该方法由具体的用例重写，主要为调用addParameter方法创建测试用例参数。
"""
pass

def createRequirement(self):
"""该方法由具体的用例重写，主要为调用addRequirement方法创建测试用例配置引擎参数。
"""
pass

def setCaseTags(self, *args):
"""Case关键字设置，用于测试用例按关键字过滤.

Args:
args (list): Case的关键字列表.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.setCaseTags("name", "test", "ok").

"""
self.tags.extend(args)

def procedure(self):
"""用户自定义,在TestCase实现时，该接口中调用addStep()设置Case的测试步骤.
"""
return

def logCaseDetailInfo(self):
"""用例中在class的doc中写入测试用例的详细信息，如测试用例ID，测试用例步骤等，通过该方法记录用例的原始详细信息到日志中
"""
if hasattr(self, "__doc__") and self.__doc__:
self.logger.info(self.__doc__)
return

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

@validateParam(stepMessage=str)
def logStep(self, stepMessage):
"""记录step的信息.

Args:
stepMessage (str): 记录的step信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logCaseDescriptions(descriptionMessage)

"""
self.logger.tcStep(stepMessage)

def addStep(self, **kwargs):
"""添加测试用例的步骤

Args：
kwargs (dict): 测试步骤, 为关键字参数，格式参考Examples.

Examples:
def doGetCurTime():
return time()

addStep(action=doGetCurTime, # 或者为: action="doGetCurTime()"
action_params={"cur_time": curTime},
debug_info="Get current time"})

注: action为function或可执行的代码段(str)

"""

# todo 测试步骤格式检查（参数检查）.
self.testSteps.append(kwargs)

def addParameter(self, **kwargs):
"""用例中添加参数, 子类继承重写preTestCase()接口中调用.

Args:
**kwargs : 测试用例参数. 为关键字参数，键值对说明如下：
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

def getParameterObj(self, *args):
"""获取Parameter对象

Args:
args (list or None): 需要获取parameter object的parameter name， 或者不指定返回全部.

Return：
paramObj (dict): key为name，value为Parameter Object的字典。不指定args时，返回就是self.parameters.

Raises:
ValueException: 需要获取的parameter不存在.

Examples:
1、返回全部的parameter：
getParameterObj();

2、返回指定名称的parameter:
getParameterObj(["name1", "name2"])

"""
paramObj = {}

if not args:
return self.parameters

for key in args:
if key not in self.parameters:
raise ValueException("parameter name: '%s' does not exist. " % key)

paramObj[key] = self.parameters[key]

return paramObj

def getTestSetData(self, *args):
"""获取case保存在testSet中的指定key的数据.

Args:
*args : 需要获取的data的key的列表.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.getTestSetData(data)

"""
currentTh = threading.current_thread()
if hasattr(currentTh, 'dataLocks') and isinstance(currentTh.dataLocks, list):
self.logger.info("+++++++++++++++++++++++++++get data add lock")
currentTh.dataLocks.append(self.testSet.caseDataSemaphore)
return self.testSet.getData(args)

@validateParam(caseData=dict)
def saveData(self, caseData):
"""case需要保存数据到testSet中，方便其他case使用.

Args:
caseData (dict): 需要保存的数据，key，value组成.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.saveData(data)

"""
currentTh = threading.current_thread()
if hasattr(currentTh, 'dataLocks') and isinstance(currentTh.dataLocks, list):
self.logger.info("+++++++++++++++++++++++++++save data add lock")
currentTh.dataLocks.append(self.testSet.caseDataSemaphore)
self.testSet.saveData(caseData)

def logParameter(self):
"""记录Case的Parameter.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logParameter(paramMessage)

"""
self.logger.info("Parameter: \n" + str(self.getParameter()))

def setParameter(self, customParamList=None):
"""传入从xml中获取的parameter value，设置到parameter中.

Args:
customParamList (list): xml配置的参数list, 默认为None. 如:
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
logMessage = "A value for: '%s' must be specified." % param["name"]
self.logger.error(logMessage)
hasInvalidValue = True

if hasInvalidValue:
raise ValueException("One or more parameters are invalid, please check log for more information. ")

@validateParam(shareable=bool)
def setEquipmentShareable(self, shareable):
"""设置Case的测试设备是否可共享.

Args:
shareable (bool): 是否可共享.
True: 可共享。
False；不可共享.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setEquipmentShareable(shareable)

"""
self.shareableEquipment = shareable

def isFailed(self):
"""判断TestCase执行是否失败.

Returns:
True (bool): caseStatus为FAIL.
False (bool): caseStatus为不为FAIL.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.isFailed()

"""
return self.caseStatus == TEST_STATUS.FAILED

def isPassed(self):
"""判断TestCase执行是否成功.

Returns:
True (bool): caseStatus为PASS.
False (bool): caseStatus为不为PASS.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.isPassed()

"""
return self.caseStatus == TEST_STATUS.PASS

@validateParam(status=str)
def setCaseStatus(self, status):
"""设置TestCase的状态

用于设置case的状态.

Args:
status (str): case的状态.

Notes:
1、定义的Case的状态为：ConfigError|Running|Pass|Fail|Configured|Kill|NotRun

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setCaseStatus("pass")

"""
status_Units = "|".join(STATUS_UNITS)
statusRegex = "^(" + status_Units + ")$"

if not re.match(r'' + str(statusRegex) + '', status, re.IGNORECASE):
raise ValueException("Case Status: '%s' is undefined. " % status)

# 在并发循环时，克隆的用例会回填基础用例状态，当一次执行失败则基础用例的状态应该为失败.
if self.caseStatus == TEST_STATUS.FAILED or self.caseStatus == TEST_STATUS.CONFIG_ERROR:
return
self.caseStatus = status

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

def setFailureReason(self, reason):
"""设置Case执行失败的原因

由controller调用设置.

Args:
reason (str): case执行失败的原因.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.setFailureReason(reason)

"""
self.failureReason = reason

def getErrorCount(self):
"""获取TestCase中ErrorCount的计数

Returns:
count (int): 错误次数.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.getErrorCount()

"""
self.errorCountSemaphore.acquire()
count = self.errorCount
self.errorCountSemaphore.release()
return count

def getWarningCount(self):
"""获取TestCase中的WarningCount的计数

Returns:
count (int): 告警次数.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.getWarningCount()

"""
self.warnCountSemaphore.acquire()
count = self.warnCount
self.warnCountSemaphore.release()
return count

def incrementErrorCount(self):
"""增加ErrorCount计数

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.incrementErrorCount()

"""
self.errorCountSemaphore.acquire()
self.errorCount += 1
self.errorCountSemaphore.release()

def incrementWarningCount(self):
"""增加WarnCount的计数

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.incrementWarningCount()

"""
self.warnCountSemaphore.acquire()
self.warnCount += 1
self.warnCountSemaphore.release()

def __logStepAndStatus(self, logMessage):
"""设置步骤和状态信息

调用test Set 、 test controller接口设置.

Args:
logMessage (str): 需要记录的日志信息.

Examples:
在当前类中使用.
self.__logStepAndStatus(logMessage)
"""
status = dict()
status["name"] = self.name
# todo test Set and controller object define

def addCleanUpStack(self, cleanActions):
"""添加测试后清理到堆栈中.

Args:
cleanActions (list|ComponentBase|str): 需要清理的操作，列表的元素为function、可执行的代码段(str)或业务对象.

Raises:
InvalidParamException: 传入的参数类型错误时抛出异常.

Notes:
1、若cleanActions中的列表元素为function, 则不能传入参数，需要的参数操作处理在function定义中实现.
2、cleanActions中的操作执行的顺序为: 从最后一个列表元素依次向前执行.如：
cleanActions = [Action1, Action2, Action3, ], 先执行Action3, 其次为Action2，最后为Action1.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
def addSelf():
number = 1
return number += 1
func = "addSelf()"
cleanActions = [addSelf, func]
caseObjects.addCleanUpStack(cleanActions)

Changes:
2015-07-15 h90006090 修改支持传入的参数为list的情况， 增加错误参数的检查，确保传入的参数正确.

"""
# todo cleanAction 是一个Component对象需要定义
if isinstance(cleanActions, list):
for tmp in cleanActions:
if not isinstance(tmp, ComponentBase) and not hasattr(tmp, "__call__") and not isinstance(tmp, str):
raise InvalidParamException("Only UniAutos.ComponentBase objects, Pointers to methods, "
"and Code references (str) may be passed to addToCleanup().")
self.cleanupStacks.extend(cleanActions)
elif isinstance(cleanActions, dict):
raise InvalidParamException("cleanup Actions [%s] type is [%s] failed, "
"must be str、Component、list，" % (cleanActions, type(cleanActions)))
else:
self.cleanupStacks.append(cleanActions)

def addToPostTestSet(self, postSetActions):
"""添加Case需要测试套进行清理的操作到测试套.

Args:
postSetActions (list): 用例在测试套中清理的操作.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.addToPostTestSet(postSetAction)

"""
# todo 线程id判断
self.testSet.addPostSetActions(postSetActions)

def removeFormCleanUpStack(self):
"""移除最后cleanup Stack 中的最后一个清理操作.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.removeFormCleanUpStack()

"""
self.cleanupStacks.pop()

def performCleanUp(self):
"""处理cleanup stack

Raises:
UniAutosException: 清理操作出现错误时抛出异常.

Examples:
在用例中写入如下代码:
def postTestCase(self):
self.performCleanUp()
return
或者：
用例中直接删除postTestCase的方法定义，让用例直接调用父类的postTestCase方法.

Changes:
2015-07-15 h90006090 1、循环查找component中的properties时使用了candidateKeys，导致变量类型错误.
2、device的waitForDeadComponent方法使用的变量为list，传入的为
component时出现类型错误，修改传入类型为list.
"""
# todo perform前的操作
# 执行清理操作

errorCount = self.getErrorCount()

if self.cleanupStacks:
self.logger.info("Performing Test Defined cleanup Actions. ")
else:
self.logger.warn("Test have not clean Actions. ")

while len(self.cleanupStacks):
cleanAction = self.cleanupStacks.pop()

# postAction为函数
if hasattr(cleanAction, '__call__'):

# 没有具体的Exception可以捕获.
try:
cleanAction()
except Exception, error:
self.logger.error("CleanUp Action threw an exception: %s" % error)

# postAction为可执行的代码段
elif isinstance(cleanAction, str):

# 没有具体的Exception可以捕获.
try:
exec cleanAction
except Exception, error:
self.logger.error("CleanUp Action threw an exception: %s" % error)

# 移除业务
elif isinstance(cleanAction, ComponentBase):
if hasattr(cleanAction, "properties"):
candidateKeys = cleanAction.getCandidateKeys()
for key in candidateKeys:
if key in cleanAction.properties and cleanAction.properties[key]:
self.logger.debug("Cleaning Object %s with key of [%s]."
% (cleanAction, cleanAction.properties[key]))
canKey = key
break
if cleanAction.isDead():
continue
# componentDevice = cleanAction.owningDevice

# Changed 2015/10/09 h90006090 修改为使用Component的classFullName.
# if componentDevice.getDirtyFlag(cleanAction.classFullName):
# # TODO 以下代码需要性能优化, 暂时保留，不确定删除带来的影响, 暂时无影响，后续有影响，考虑方案
# try:
# componentDevice.find(cleanAction.classFullName,
# criteria={canKey: cleanAction.properties[canKey]},
# forceSync=True)
# except Exception, error:
# self.logger.error("Perform Cleanup Action threw an exception: %s" % error)
# if cleanAction.isDead():
# continue
# else:
try:
cleanAction.wipe()
# TODO 保留代码可能有影响.
# componentDevice.waitForDeadComponent([cleanAction])
except Exception, error:
self.logger.error("Perform Cleanup Action threw an exception: %s" % error)

if (self.getErrorCount() - errorCount) > 0:
raise UniAutosException("%s errors occurred when performing cleanup action, "
"please check above logs for detail" % (self.getErrorCount() - errorCount))

# todo destroy configuration

def hasIdentity(self, identity):
"""检查用例是否有标识.

Args:
identity (dict): 用例标识的字典.如：identity = {"name": "Test lun"}

Returns:
True (bool): 有指定的identity.
False (bool): 没有指定的identity.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.hasIdentity(identity)

"""
if self.identities is None:
return False

for child in self.identities["identity"]:
if identity["name"].lower() == child["name"].lower():
return True

return False

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

@validateParam(identity=dict)
def addIdentity(self, identity):
"""Case中添加identity

Args:
identity (dict): Case的身份标识.如：
identity = {"name": "YMC", "id": "TC-001"}

Raises:
ValueException: 需要添加的identity已经存在.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.addIdentity(identity)

"""
if self.hasIdentity({"name": identity["name"]}):
raise ValueException("The identity: '%s' already exists on this test. " % identity["name"])

self.identities["identity"].append(identity)

def logInfo(self, infoMessage):
"""记录case的info信息

Args:
infoMessage (str): 记录的info信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logInfo(infoMessage)

"""
self.logger.info(infoMessage)

def logError(self, errorMessage='None', exceptionMsg='None'):
"""记录case的error信息

Args：
errorMessage (str): 记录的error信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logError(errorMessage)

"""
self.logger.error(errorMessage, exceptionMsg)

def logDebug(self, debugMessage):
"""记录case的debug信息到日志

Args：
debugMessage (str): 记录的debug信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logDebug(debugMessage)

"""
self.logger.debug(debugMessage)

def logTrace(self, traceMessage):
"""记录case的trace信息到日志

Args:
traceMessage (str): 记录的trace信息.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
caseObjects.logTrace(traceMessage)

"""
self.logger.trace(traceMessage)

def stopOnError(self):
"""若是Case执行失败，停止测试

调用控制器方法停止测试.

Raises:
RuntimeError: 测试失败时抛出运行错误.

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.stopOnError()

"""
if re.match(r'^Fail|ConfigError$', self.caseStatus):
self.testSet.engine.setStopOnError(True)
raise UniAutosException("This case failed with stop_on_error. Test Set will stop here "
"and postTestCase will not continue. ")
return

@classmethod
def acquireWaitPoint(cls, point, timeout=None):
"""设置用例执行暂停标签

当某个操作前需要暂停等待另一个用例做完某个操作时使用, 由另一个线程执行完成特定操作后按照指定标签通知线程继续用例继续执行.

Args:
point (str): 暂停的标签. 该标签必须成对出现且必须设置超时机制, 否则可能会死锁; 指定的字符串不能为已经定义的变量，函数等.
timeout (int): 超时时间, 默认为None， 若通知的时机错误、没有指定标签通知，则可能会死锁， 建议设置超时时间.

Examples:
Base.acquireWaitPoint("Create", 100)

"""
globals()[point] = threading.Event()
globals()[point].wait(timeout=timeout)

@classmethod
def releaseWaitPoint(cls, point):
"""通知设置了用例执行暂停标签的线程继续执行.

Args:
point (str): 暂停的标签. 该标签必须成对出现且必须设置超时机制, 否则可能会死锁;
指定的字符串不能为已经定义的变量，函数等; 此处指定的标签必须时已经设置的标签.

Examples:
Base.releaseWaitPoint("Create")

"""
try:
globals()[point].set()
globals()[point] = None
del globals()[point]
except Exception, error:
Log.getLogger(cls.__module__).warn("Release Point: %s Failed . Wait Timeout. "
"if you not define timeout , it will be hung." % point)

def addCreatedConfigEnvComponent(self, compObject):
"""存储由ConfigureEnv模块创建的UniAutos.ComponentBase实例对象到当前测试用例对象

Args:
compObjects (instance): component实例对象.

"""
if isinstance(compObject, list):
for compObj in compObject:
if isinstance(compObj, ComponentBase):
self.configEnvCreateComponents.append(compObj)
else:
self.logger.warn("%s is not component instance , "
"addCreateConfigEngineComponent()Failed " % compObj)
if isinstance(compObject, ComponentBase):
self.configEnvCreateComponents.append(compObject)
else:
self.logger.warn("%s is not component instance , "
"addCreateConfigEngineComponent()Failed " % compObject)

def getNextCreatedConfigEnvComponent(self):
"""按照堆栈出栈的方式获取当前list中的最后一个component，并且从list中移除.
Returns:
compObj (instance): 获取的component对象.

"""

if not self.configEnvCreateComponents:
compObj = None
else:
compObj = self.configEnvCreateComponents.pop() # 从list中删除.
return compObj

def clearValidatedByConfigureEnvComponents(self):
"""清除所有已知设备的Components的validated标记.

统一对当前用例在使用的所有设备上添加的component对象的验证标记清除.
"""
devices = self.resource.getAllDevices()
for devType in devices:
if re.match("^block|file|unified$", devType):
dev = devices[devType]
for devId in dev:
dev[devId].removeValidatedByEngine()

def addRequirement(self, requirementParams):
"""添加测试需要的配置、设备等信息.

Args:
requirementParams (dict): 生成Requirement对象的参数, 键值对说明如下：

{requirement_configuration (list): 配置列表，一个元素即为一个配置.
[
{"device_type" (str): 配置项对应的设备类型，取值范围为："unified".
"device_id" (str): 配置项对象的设备id，取值范围为指定设备类型在xml中配置的id.
"requirement" (dict): 该设备中需要配置的业务字典数据，key为业务别名， value为list，
-且list中单个元素的值为创建业务使用的参数字典（参考各业务的
-componentCreate方法说明.）。
{"DiskDomain" (list): diskDomain的配置列表，一个元素代表一个diskDomain。
"MappingView": (list): MappingView的配置列表，一个元素代表一个MappingView.
}
},
]
}

如：
{"requirement_configuration"：
[
{"device_type": "unified",
"device_id": "1",
"requirement":
{"disk_domain": [],
"mapping_view": []
}
}, # 第一台设备的配置
{"device_type": "unified",
"device_id": "2",
"requirement":
{"disk_domain": [],
"mapping_view": []
}
}, # 第二台设备的配置
.. # n台设备的配置
]
}

Returns:
None

Raises:
None

Examples:
def createMetaData():
addRequirement({"requirement_configuration"：
[
{"device_type": "unified",
"device_id": "1",
"requirement":
{"lun":
[{"name": "ConfigLun02",
"storage_pool_id": "1",
"capacity": "1GB",
"count": 1
},
]
}}
],})
return

Notes:
在测试用例的createMetaData方法中调用.

"""
for key in requirementParams:
if key == "requirement_configuration":
configureInfoParams = requirementParams[key]
self.__addConfigureInfonRequirement(configureInfoParams)
# todo if need other requirement , add at here

def removeConfiguration(self):
"""移除当前用例的配置信息（requirement）
"""
devices = self.resource.getAllDevices()

def threadSub(dev, tcObject=None):
wipeConfig(dev, testObject=tcObject)

threads = list()
for device in devices:
if hasattr(device, "type") and re.match(r'block|file|unified', device.type):
th = threading.Thread(target=threadSub, args=(device, self))
threads.append(th)
for th in threads:
th.start()

for th in threads:
if th.isAlive():
th.join()

return

def __addConfigureInfonRequirement(self, configList):
"""add configuration requirement on array
Args:
configList (list): Requirement对象的参数列表,每个元素为一个字典，元素键值对说明如下：

[
{"device_type" (str): 配置项对应的设备类型，取值范围为："unified".
"device_id" (str): 配置项对象的设备id，取值范围为指定设备类型在xml中配置的id.
"requirement" (dict): 该设备中需要配置的业务字典数据，key为业务别名， value为list，
-且list中单个元素的值为创建业务使用的参数字典（参考各业务的
-componentCreate方法说明.）。
{"DiskDomain" (list): diskDomain的配置列表，一个元素代表一个diskDomain。
"MappingView": (list): MappingView的配置列表，一个元素代表一个MappingView.
}
},
]

如：
[
{"device_type": "unified",
"device_id": "1",
"requirement":
{"disk_domain": [],
"mapping_view": []
}
}, # 第一台设备的配置
{"device_type": "unified",
"device_id": "2",
"requirement":
{"disk_domain": [],
"mapping_view": []
}
}, # 第二台设备的配置
.. # n台设备的配置
]

"""
for child in configList:
if "clean_up" in child:
self.cleanupConfiguration = child["clean_up"]
continue
deviceId = child.get("device_id")
deviceType = child.get("device_type")
requirementParamsDict = child.get("requirement")
# if not deviceId or not deviceType or re.match(r'block|file|unified|any', deviceType):
# 目前仅支持unified.
if not deviceId and not deviceType and not re.match(r'unified', deviceType) and not requirementParamsDict:
raise InvalidParamException("Add requirement parameter failed, there have not specified device_type "
"or device_id, or device_type not one of unified, or not specified "
"requirement, Please check addRequirement function of this Case and review"
"the function's help. ")

tmpRequirement = ConfigureInfoBase(self, deviceType, deviceId, requirementParamsDict)
self.requirement["requirement_configuration"].append(tmpRequirement)

return

def clearConfiguredKeyOnDevices(self):
"""Clears the validated by engine reference on all known device components.
"""
allDevices = list()
# 目前只支持unified.
allDevices.extend(self.resource.getSpecifiesTypeDevices("unified"))
# allDevices.extend(self.resource.getSpecifiesTypeDevices("block"))
# allDevices.extend(self.resource.getSpecifiesTypeDevices("file"))
for dev in allDevices:
if hasattr(dev, "configured"):
dev.configured = False
if hasattr(dev, "configId"):
dev.configId = False
return

def getDevice(self, deviceType, deviceId):
"""获取指定设备类型，设备id的设备对象
Returns:
device (instance): 设备对象.
"""
return self.resource.getDevice(deviceType, deviceId)

def getHost(self, role, platform=None):
"""获取指定类型或操作系统的HOST对象

Args:
role (str): host类型 可选值 io,ldap,ad,cps等，io 表示提供业务读写的host.
platform (str|None): host的操作系统平台，默认为None.

Returns:
device (list): host对象列表.

Examples:
1.获取所有的linux主机
linux_host = case.getHost(hostRole='io', platform='linux')

2.获取所有的LDAP服务器
ldap_server = case.getHost(hostRole='ldap')
"""
return self.resource.getHost(role, platform)

def handleException(self, types, msg, tracePoint):
"""hold exception
Args:
types (str): error type, 'warning' or 'error'.
msg (str): error msg.
tracePoint (str): trace point.
Examples:
try:
a = 1+"1"
except Exception, err:
self.handleException("error", "---add Error:", traceback.format_exc())

"""
if types == "warning":
self.handleWarnCount += 1
self.handleWarnMsg += msg + ":\n" + tracePoint + "\n"

elif types == "error":
self.handleErrorCount += 1
self.handleErrorMsg += msg + ":\n" + tracePoint + "\n"

def logHandleReport(self):
"""
Examples:
self.logHandleReport()

"""
self.logError("\nThere have ErrorCount: %s\nErrorMsg: %s\n" % (self.handleErrorCount, self.handleErrorMsg))
self.logError("\nThere have WarningCount: %s\nWarningMsg: %s\n" % (self.handleWarnCount, self.handleWarnMsg))

def releaseHandleException(self):
"""clear all hold Exception info.
Examples:
self.releaseHandleException()

"""
self.handleErrorCount = 0
self.handleWarnCount = 0
self.handleWarnMsg = ''
self.handleErrorMsg = ''

def setTmssId(self, tmssId):
"""set case's tmss id.
Args:
tmssId (str): Case tmss id.
"""
if self.hasIdentity({'name': 'tmss_id'}):
for identity in self.identities["identity"]:
if identity["name"] == 'tmss_id':
identity['id'] = tmssId
else:
self.identities['identity'].append({'name': 'tmss_id',
'id': tmssId})

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

# ####### Follow is assert function #######

def fail(self, msg=None):
"""Fail immediately, with the given message."""
raise self.failureException(msg)

def assertFalse(self, expr, msg=None):
"""Check that the expression is false."""
if expr:
msg = self._formatMessage(msg, "%s is not false" % safe_repr(expr))
raise self.failureException(msg)

def assertTrue(self, expr, msg=None):
"""Check that the expression is true."""
if not expr:
msg = self._formatMessage(msg, "%s is not true" % safe_repr(expr))
raise self.failureException(msg)

def _formatMessage(self, msg, standardMsg):
"""Honour the longMessage attribute when generating failure messages.
If longMessage is False this means:
* Use only an explicit message if it is provided
* Otherwise use the standard message for the assert

If longMessage is True:
* Use the standard message
* If an explicit message is provided, plus ' : ' and the explicit message
"""
# Removed
# if not self.longMessage:
# return msg or standardMsg

if msg is None:
return standardMsg
try:
# don't switch to '{}' formatting in Python 2.X
# it changes the way unicode input is handled
return '%s : %s' % (standardMsg, msg)
except UnicodeDecodeError:
return '%s : %s' % (safe_repr(standardMsg), safe_repr(msg))

def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
"""Fail unless an exception of class excClass is raised
by callableObj when invoked with arguments args and keyword
arguments kwargs. If a different type of exception is
raised, it will not be caught, and the test case will be
deemed to have suffered an error, exactly as for an
unexpected exception.

If called with callableObj omitted or None, will return a
context object used like this::

with self.assertRaises(SomeException):
do_something()

The context manager keeps a reference to the exception as
the 'exception' attribute. This allows you to inspect the
exception after the assertion::

with self.assertRaises(SomeException) as cm:
do_something()
the_exception = cm.exception
self.assertEqual(the_exception.error_code, 3)
"""
context = _AssertRaisesContext(excClass, self)
if callableObj is None:
return context
with context:
callableObj(*args, **kwargs)

def _getAssertEqualityFunc(self, first, second):
"""Get a detailed comparison function for the types of the two args.

Returns: A callable accepting (first, second, msg=None) that will
raise a failure exception if first != second with a useful human
readable error message for those types.
"""
#
# NOTE(gregory.p.smith): I considered isinstance(first, type(second))
# and vice versa. I opted for the conservative approach in case
# subclasses are not intended to be compared in detail to their super
# class instances using a type equality func. This means testing
# subtypes won't automagically use the detailed comparison. Callers
# should use their type specific assertSpamEqual method to compare
# subclasses if the detailed comparison is desired and appropriate.
# See the discussion in http://bugs.python.org/issue2578.
#
if type(first) is type(second):
asserter = self._type_equality_funcs.get(type(first))
if asserter is not None:
if isinstance(asserter, basestring):
asserter = getattr(self, asserter)
return asserter

return self._baseAssertEqual

def _baseAssertEqual(self, first, second, msg=None):
"""The default assertEqual implementation, not type specific."""
if not first == second:
standardMsg = '%s != %s' % (safe_repr(first), safe_repr(second))
msg = self._formatMessage(msg, standardMsg)
raise self.failureException(msg)

def assertEqual(self, first, second, msg=None):
"""Fail if the two objects are unequal as determined by the '=='
operator.
"""
assertion_func = self._getAssertEqualityFunc(first, second)
assertion_func(first, second, msg=msg)

def assertNotEqual(self, first, second, msg=None):
"""Fail if the two objects are equal as determined by the '!='
operator.
"""
if not first != second:
msg = self._formatMessage(msg, '%s == %s' % (safe_repr(first),
safe_repr(second)))
raise self.failureException(msg)

def assertAlmostEqual(self, first, second, places=None, msg=None, delta=None):
"""Fail if the two objects are unequal as determined by their
difference rounded to the given number of decimal places
(default 7) and comparing to zero, or by comparing that the
between the two objects is more than the given delta.

Note that decimal places (from zero) are usually not the same
as significant digits (measured from the most signficant digit).

If the two objects compare equal then they will automatically
compare almost equal.
"""
if first == second:
# shortcut
return
if delta is not None and places is not None:
raise TypeError("specify delta or places not both")

if delta is not None:
if abs(first - second) delta:
return
standardMsg = '%s == %s within %s delta' % (safe_repr(first),
safe_repr(second),
safe_repr(delta))
else:
if places is None:
places = 7
if not (first == second) and round(abs(second-first), places) != 0:
return
standardMsg = '%s == %s within %r places' % (safe_repr(first),
safe_repr(second),
places)

msg = self._formatMessage(msg, standardMsg)
raise self.failureException(msg)

# Synonyms for assertion methods

# The plurals are undocumented. Keep them that way to discourage use.
# Do not add more. Do not remove.
# Going through a deprecation cycle on these would annoy many people.
assertEquals = assertEqual
assertNotEquals = assertNotEqual
assertAlmostEquals = assertAlmostEqual
assertNotAlmostEquals = assertNotAlmostEqual
assert_ = assertTrue

# These fail* assertion method names are pending deprecation and will
# be a DeprecationWarning in 3.2; http://bugs.python.org/issue2578
# def _deprecate(original_func):
# def deprecated_func(*args, **kwargs):
# warnings.warn(
# 'Please use {0} instead.'.format(original_func.__name__),
# PendingDeprecationWarning, 2)
# return original_func(*args, **kwargs)
# return deprecated_func
#
# failUnlessEqual = _deprecate(assertEqual)
# failIfEqual = _deprecate(assertNotEqual)
# failUnlessAlmostEqual = _deprecate(assertAlmostEqual)
# failIfAlmostEqual = _deprecate(assertNotAlmostEqual)
# failUnless = _deprecate(assertTrue)
# failUnlessRaises = _deprecate(assertRaises)
# failIf = _deprecate(assertFalse)

def assertSequenceEqual(self, seq1, seq2, msg=None, seq_type=None):
"""An equality assertion for ordered sequences (like lists and tuples).

For the purposes of this function, a valid ordered sequence type is one
which can be indexed, has a length, and has an equality operator.

Args:
seq1: The first sequence to compare.
seq2: The second sequence to compare.
seq_type: The expected datatype of the sequences, or None if no
datatype should be enforced.
msg: Optional message to use on failure instead of a list of
differences.
"""
if seq_type is not None:
seq_type_name = seq_type.__name__
if not isinstance(seq1, seq_type):
raise self.failureException('First sequence is not a %s: %s'
% (seq_type_name, safe_repr(seq1)))
if not isinstance(seq2, seq_type):
raise self.failureException('Second sequence is not a %s: %s'
% (seq_type_name, safe_repr(seq2)))
else:
seq_type_name = "sequence"

differing = None
try:
len1 = len(seq1)
except (TypeError, NotImplementedError):
differing = 'First %s has no length. Non-sequence?' % (
seq_type_name)

if differing is None:
try:
len2 = len(seq2)
except (TypeError, NotImplementedError):
differing = 'Second %s has no length. Non-sequence?' % (
seq_type_name)

if differing is None:
if seq1 == seq2:
return

seq1_repr = safe_repr(seq1)
seq2_repr = safe_repr(seq2)
if len(seq1_repr) > 30:
seq1_repr = seq1_repr[:30] + '...'
if len(seq2_repr) > 30:
seq2_repr = seq2_repr[:30] + '...'
elements = (seq_type_name.capitalize(), seq1_repr, seq2_repr)
differing = '%ss differ: %s != %s\n' % elements

for i in xrange(min(len1, len2)):
try:
item1 = seq1[i]
except (TypeError, IndexError, NotImplementedError):
differing += ('\nUnable to index element %d of first %s\n' %
(i, seq_type_name))
break

try:
item2 = seq2[i]
except (TypeError, IndexError, NotImplementedError):
differing += ('\nUnable to index element %d of second %s\n' %
(i, seq_type_name))
break

if item1 != item2:
differing += ('\nFirst differing element %d:\n%s\n%s\n' %
(i, item1, item2))
break
else:
if len1 == len2 and seq_type is None and type(seq1) != type(seq2):
# The sequences are the same, but have differing types.
return

if len1 > len2:
differing += ('\nFirst %s contains %d additional '
'elements.\n' % (seq_type_name, len1 - len2))
try:
differing += ('First extra element %d:\n%s\n' %
(len2, seq1[len2]))
except (TypeError, IndexError, NotImplementedError):
differing += ('Unable to index element %d '
'of first %s\n' % (len2, seq_type_name))
elif len1 < len2:
differing += ('\nSecond %s contains %d additional '
'elements.\n' % (seq_type_name, len2 - len1))
try:
differing += ('First extra element %d:\n%s\n' %
(len1, seq2[len1]))
except (TypeError, IndexError, NotImplementedError):
differing += ('Unable to index element %d '
'of second %s\n' % (len1, seq_type_name))
standardMsg = differing
diffMsg = '\n' + '\n'.join(
difflib.ndiff(pprint.pformat(seq1).splitlines(),
pprint.pformat(seq2).splitlines()))
standardMsg = self._truncateMessage(standardMsg, diffMsg)
msg = self._formatMessage(msg, standardMsg)
self.fail(msg)

def _truncateMessage(self, message, diff):
max_diff = self.maxDiff
if max_diff is None or len(diff)