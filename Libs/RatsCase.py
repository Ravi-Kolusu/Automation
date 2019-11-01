#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: RatsCase, 多线程并发执行用例类.

版权信息: 华为技术有限公司，版本所有(C) 2014-2015

"""

import random
import time
import threading
from UniAutos.TestEngine.Case import Case
from UniAutos.Util.Units import Units
from UniAutos.Exception.UniAutosException import UniAutosException


class RatsCase(Case):
"""多线程执行的用例类定义.

用于多线程执行时, 编写用例继承使用的基类.

Args:
parameters (dict): testSet传入的Case使用的数据.格式如下：
parameters = {"name": "",
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
self.ratsEngine (UniAutos.TestEngine.RatsEngine.RatsEngine) : 引擎对象.
self.templateId (int) : RatsCase临时Id, 用于标识用例.
self.baseCaseObject (UniAutos.TestEngine.RatsCase.RatsCase) : 用例对象克隆后用例保存克隆前对象.
self.MaxRunTime (int) : 单个用例最长运行时间.
self.runNumber (int) : 用例执行当前运行次数.

Returns:
RatsCase (instance): 并发循环执行的用例对象实例.

Raises:
None.

Examples:
RatsCaseObject = RatsCase(caseValidation)

"""
def __init__(self, parameters):
self.ratsEngine = parameters.pop("engine", None)

# 克隆之前的用例唯一ID
self.templateId = parameters.pop("templateId", random.randrange(1000000))

# 定义一个克隆之前的用例对象，用来保存该用例对象的全局状态用来判断当前的用例是否可以执行.
self.baseCaseObject = parameters.pop("base", None)
super(RatsCase, self).__init__(parameters)
self.maxRunTime = 0
self.runNumber = 0
self.canRunExecFlag = True

def canRun(self):
"""RatsCase是否能执行的判断接口

用例中自定义重写, 若没有重写，默认抛出异常.

Examples:
if CanRun():
return

"""
raise UniAutosException("Method: %s must be to override: %s.%s \n" % ("canRun", self.__module__,
self.__class__.__name__))

def incrementRunNumber(self):
"""设置用例对象执行次数，每次计数加一

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.incrementRunNumber()

"""
self.runNumber += 1

def decrementRunNumber(self):
"""设置用例对象执行次数，每次计数减一， 如果CanRun执行结果为False."""
self.runNumber -= 1

def setEngine(self, engine):
"""设置用例所属的引擎

Args:
engine (instance): 用例所属的引擎.

Examples:
self.setEngine(engine)

"""
self.ratsEngine = engine

def setMaxRunTime(self, maxTime):
"""设置最长运行时间

Args:
maxTime (str): 设置最长运行时间.

Examples:
self.setMaxRunTime(maxTime)

"""
if Units.isTime(maxTime):
convertTime = Units.convert(maxTime, "S")
self.maxRunTime = Units.getNumber(convertTime)

def setKillAble(self, flag):
"""设置用例killAble状态

设置用例对应的线程是否可以被终止.

Args:
flag (bool): 是否能被终止的标记.
True: 可以.
False: 不可以.

Examples:
self.setKillAble(True)

"""
self.ratsEngine.setKillAble(self, flag)

def rescanIoHosts(self):
"""扫描IO的主机

当主机重启等主机链接断开重连时等待主机恢复操作.

Examples:
self.rescanIoHosts()

"""
self.logger.info("Requesting the Controller to Rescan IO Hosts. ")
self.ratsEngine.setIsRescanIo(True)
time.sleep(1)
while self.ratsEngine.isRescanning:
time.sleep(1)
self.logger.info("Controller finished rescanning hosts. ")

def isExpired(self):
"""整个测试总的测试时间是否已经超时

Args:
None.

Returns:
isExpired (bool): 是否已经超时.
True: 超时.
False: 未超时.

Raises:
None.

Examples:
if self.isExpired():
pass

"""
return self.ratsEngine.durationExpired

def getCurrentlyRunningCount(self):
"""获取当前用例执行的个数

Args:
None.

Returns:
None.

Raises:
None.

Examples:
counts = self.getCurrentlyRunningCount()

"""
return self.ratsEngine.getRunningRatsCaseCount(self)

def recordUsingComponent(self, component, destructive, action):
"""记录UniAuto的Component， 用于标记Component正在被该用例使用

This is not a LOCK of a component. Multiple modules may use the same component
if their actions don't conflict. This is just a mechanism to record this module
is using a Component and declaring it's actions (which may be evaluated by other
modules to determine if they can run on this component).

Args:
component (instance): 当前用例正在使用的UniAutos.Component对象.
destructive (bool): 当前用例是否会破坏该Component.
action (str): 操作的类型，这是一个简单的说明， 说明其他用例可以检查并确定他们呢是否可以运行.

Examples:
self.recordUsingComponent(component, True, "SNAPSHOT_SOURCE")

"""
self.ratsEngine.recordComponentForRatsCase(ratsCase=self,
component=component,
destructive=destructive,
action=action,
tid=threading.current_thread().ident)

def recordDoneWithComponent(self, component=None):
"""使用RatsEngine记录该用例使用指定的component完成

Args:
component (instance): 指定的UniAutos.Component对象将会被记录，
如果不指定则在完成后所有的component都会被记录.

Examples:
self.recordDoneWithComponent(component)

"""
self.ratsEngine.recordRatsCaseCompleteWithComponent(ratsCase=self,
component=component)

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
return self.ratsEngine.getCurrentComponentActions(component)

if __name__ == "__main__":
pass

=============================================================================================

#=================================================================================================================================================================================================

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: RatsCase, 多线程并发执行用例类.

版权信息: 华为技术有限公司，版本所有(C) 2014-2015

"""

import random
import time
import threading
from UniAutos.TestEngine.Case import Case
from UniAutos.Util.Units import Units
from UniAutos.Exception.UniAutosException import UniAutosException


class RatsCase(Case):
"""多线程执行的用例类定义.

用于多线程执行时, 编写用例继承使用的基类.

Args:
parameters (dict): testSet传入的Case使用的数据.格式如下：
parameters = {"name": "",
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
self.ratsEngine (UniAutos.TestEngine.RatsEngine.RatsEngine) : 引擎对象.
self.templateId (int) : RatsCase临时Id, 用于标识用例.
self.baseCaseObject (UniAutos.TestEngine.RatsCase.RatsCase) : 用例对象克隆后用例保存克隆前对象.
self.MaxRunTime (int) : 单个用例最长运行时间.
self.runNumber (int) : 用例执行当前运行次数.

Returns:
RatsCase (instance): 并发循环执行的用例对象实例.

Raises:
None.

Examples:
RatsCaseObject = RatsCase(caseValidation)

"""
def __init__(self, parameters):
self.ratsEngine = parameters.pop("engine", None)

# 克隆之前的用例唯一ID
self.templateId = parameters.pop("templateId", random.randrange(1000000))

# 定义一个克隆之前的用例对象，用来保存该用例对象的全局状态用来判断当前的用例是否可以执行.
self.baseCaseObject = parameters.pop("base", None)
super(RatsCase, self).__init__(parameters)
self.maxRunTime = 0
self.runNumber = 0
self.canRunExecFlag = True

def canRun(self):
"""RatsCase是否能执行的判断接口

用例中自定义重写, 若没有重写，默认抛出异常.

Examples:
if CanRun():
return

"""
raise UniAutosException("Method: %s must be to override: %s.%s \n" % ("canRun", self.__module__,
self.__class__.__name__))

def incrementRunNumber(self):
"""设置用例对象执行次数，每次计数加一

Examples:
from UniAutos.TestController.Base import Base
baseObject = Base(test_validation)
baseObject.incrementRunNumber()

"""
self.runNumber += 1

def decrementRunNumber(self):
"""设置用例对象执行次数，每次计数减一， 如果CanRun执行结果为False."""
self.runNumber -= 1

def setEngine(self, engine):
"""设置用例所属的引擎

Args:
engine (instance): 用例所属的引擎.

Examples:
self.setEngine(engine)

"""
self.ratsEngine = engine

def setMaxRunTime(self, maxTime):
"""设置最长运行时间

Args:
maxTime (str): 设置最长运行时间.

Examples:
self.setMaxRunTime(maxTime)

"""
if Units.isTime(maxTime):
convertTime = Units.convert(maxTime, "S")
self.maxRunTime = Units.getNumber(convertTime)

def setKillAble(self, flag):
"""设置用例killAble状态

设置用例对应的线程是否可以被终止.

Args:
flag (bool): 是否能被终止的标记.
True: 可以.
False: 不可以.

Examples:
self.setKillAble(True)

"""
self.ratsEngine.setKillAble(self, flag)

def rescanIoHosts(self):
"""扫描IO的主机

当主机重启等主机链接断开重连时等待主机恢复操作.

Examples:
self.rescanIoHosts()

"""
self.logger.info("Requesting the Controller to Rescan IO Hosts. ")
self.ratsEngine.setIsRescanIo(True)
time.sleep(1)
while self.ratsEngine.isRescanning:
time.sleep(1)
self.logger.info("Controller finished rescanning hosts. ")

def isExpired(self):
"""整个测试总的测试时间是否已经超时

Args:
None.

Returns:
isExpired (bool): 是否已经超时.
True: 超时.
False: 未超时.

Raises:
None.

Examples:
if self.isExpired():
pass

"""
return self.ratsEngine.durationExpired

def getCurrentlyRunningCount(self):
"""获取当前用例执行的个数

Args:
None.

Returns:
None.

Raises:
None.

Examples:
counts = self.getCurrentlyRunningCount()

"""
return self.ratsEngine.getRunningRatsCaseCount(self)

def recordUsingComponent(self, component, destructive, action):
"""记录UniAuto的Component， 用于标记Component正在被该用例使用

This is not a LOCK of a component. Multiple modules may use the same component
if their actions don't conflict. This is just a mechanism to record this module
is using a Component and declaring it's actions (which may be evaluated by other
modules to determine if they can run on this component).

Args:
component (instance): 当前用例正在使用的UniAutos.Component对象.
destructive (bool): 当前用例是否会破坏该Component.
action (str): 操作的类型，这是一个简单的说明， 说明其他用例可以检查并确定他们呢是否可以运行.

Examples:
self.recordUsingComponent(component, True, "SNAPSHOT_SOURCE")

"""
self.ratsEngine.recordComponentForRatsCase(ratsCase=self,
component=component,
destructive=destructive,
action=action,
tid=threading.current_thread().ident)

def recordDoneWithComponent(self, component=None):
"""使用RatsEngine记录该用例使用指定的component完成

Args:
component (instance): 指定的UniAutos.Component对象将会被记录，
如果不指定则在完成后所有的component都会被记录.

Examples:
self.recordDoneWithComponent(component)

"""
self.ratsEngine.recordRatsCaseCompleteWithComponent(ratsCase=self,
component=component)

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
return self.ratsEngine.getCurrentComponentActions(component)

if __name__ == "__main__":
pass
