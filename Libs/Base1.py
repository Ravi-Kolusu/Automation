#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
DeviceBase, Dispatcher, SQlconnection, codec, commandbase, time, fault, WrapperHolder, Uniwebbase, Toolbase, CLI, TemplateCLIObj, Dryrun
功 能: Device基类

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2015/4/17 严旭光 y00292329 created
Base-1

"""

import threading
import uuid
import sys
import datetime
import time
import copy
import traceback
from UniAutos import Log
from UniAutos.Util.Fault import Fault
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.TimeoutException import TimeoutException
from UniAutos.Util.Units import Units
from UniAutos.Exception.DeadComponentException import DeadComponentException
from UniAutos.Util.Codec import getFormatString
from UniAutos.Util.Time import sleep
from UniAutos.Exception.UniAutosException import UniAutosException


class DeviceBase(object):
"""设备基类

Args:
None

Returns:
DeviceBase: 设备对象

Raises:
None

Examples:
1、初始化一个设备
device = DeviceBase()

Changes:
2015-05-12 y00292329 Created

"""
devices = []
logger = Log.getLogger(__name__)
fifoLock = threading.Lock()

def __init__(self):
super(DeviceBase, self).__init__()
self.__id = uuid.uuid1()
self.__enableComponentsDict = dict()
self.__faultList = []
self._currentComponentsDict = dict()
self.environmentInfo = None
self.__owendObjLock = threading.RLock()
self.__cleanCandidateKeys = dict()
self.__dirtyFlag = dict()
self.classDict = dict()
self.propertyCacheEnabled = dict()
self.setupEnableComponents()
self.__initializeSemaphores()
self.ignorePauseNewLocksFlag = False
self.devices.append(self)
self.resource = None
self.__retry_codes = {}
self.__ignore_codes = {}
self.__retry_count = 0
self.__retry_interval = 0 # unit is second.
self.__wrapper_ignores = {}

@property
def id(self):
"""设备的唯一ID

Args:

Returns:
string: 设备唯一ID

Raises:
None

Examples:
1、获取设备ID
device.id

Changes:
2015-04-17 y00292329 Created

"""
return self.__id

def setupEnableComponents(self):
"""初始化设备允许创建的业务列表,由子类继承实现

Changes:
2015-04-17 y00292329 Created

"""
pass

def addAlias(self, alias, packageName):
"""通过alias对多个类型的class进行映射，方便一次性取出所有同类型的component对象

Args:
alias (string) : 业务别名，对同一类的多个component对象进行抽象
packageName (string) : 属于该package下面的所有component对象

Returns:
None

Raises:
None

Examples:
1、为设备添加Lun类型
device.addType('Lun','UniAutos.Component.Lun.Huawei.OceanStor')

Changes:
2015-04-17 y00292329 Created

"""
if packageName.lower() in self.__enableComponentsDict:
self.__enableComponentsDict[alias.lower()] = self.__enableComponentsDict[packageName.lower()]
return

@validateParam(alias=str, klass=str)
def addType(self, alias, classFullName):
"""添加设备允许的业务类型

Args:
alias (string): 业务别名
classFullName (string): 业务类的全名

Returns:
None

Raises:
InvalidParamException: 传入的业务名不存在

Examples:
1、为设备添加Lun类型
device.addType('Lun','UniAutos.Component.Lun.Huawei.OceanStor')

Changes:
2015-04-17 y00292329 Created

"""
if not classFullName.startswith('UniAutos.Component.'):
raise InvalidParamException('Alias: ' + alias
+ ', ClassFullName: ' + classFullName
+ ' is not a Component')

classNameList = classFullName.split('.')
className = classNameList.pop()
module = ".".join(classNameList)
__import__(module)
module = sys.modules[module]
klass = getattr(module, className)

alias = alias.lower()
classFullName = classFullName.lower()
if alias not in self.__enableComponentsDict.iterkeys():
self.classDict[classFullName] = klass
self.__enableComponentsDict[alias] = [classFullName]
self.__enableComponentsDict[classFullName] = [classFullName]
lst = classFullName.split('.')
for i in range(3, len(lst)):
key = '.'.join(lst[0:i])
key = key.lower()
if key not in self.__enableComponentsDict:
self.__enableComponentsDict[key] = []
self.__enableComponentsDict[key].append(classFullName)

# @validateParam(component=Component)
def addComponent(self, *args):
"""添加业务，主要由Component调用，Component在初始化过程中，调用setDevice方法，设置自身所属的设备，同时将自身添加到设备中

Args:
component (Component): 业务对象

Returns:
None

Raises:
InvalidParamException: 业务对象不属于当前设备

Examples:

Changes:
2015-04-21 y00292329 Created

"""
try:
self.semaphores['owned_object_lock'].acquire()
for component in args:
fullClassName = component.__module__ + '.' + component.__class__.__name__
fullClassName = fullClassName.lower()
if fullClassName not in self._currentComponentsDict:
self._currentComponentsDict[fullClassName] = {}
self.logger.debug('Add component, alias: %s, id: %s' % (component.__class__.__name__, str(id(component))))
self._currentComponentsDict[fullClassName][id(component)] = component
finally:
self.semaphores['owned_object_lock'].release()

def removeComponent(self, *args):
"""删除业务对象，主要由Component调用，Component在remove的方法中，调用device.removeComponent方法，设置自身所属的设备，同时将自身从设备中删除

Args:
component (Component): 业务对象

Returns:
None

Raises:
InvalidParamException: 业务对象不属于当前设备

Examples:

Changes:
2015-04-21 y00292329 Created

"""
try:
self.semaphores['owned_object_lock'].acquire()
for component in args:
fullClassName = component.__module__ + '.' + component.__class__.__name__
fullClassName = fullClassName.lower()

self.logger.debug('Removing component: %s, Id: %s' % (str(component.properties), id(component)))
component.zombify()
if id(component) in self._currentComponentsDict[fullClassName]:
del self._currentComponentsDict[fullClassName][id(component)]
else:
self.logger.debug("Component: %s have been removed" % id(component))

#### For Vstore Add:
# self.syncDeleteComponents(component)
finally:
self.semaphores['owned_object_lock'].release()

def removeAllComponent(self):
"""删除内存中保存的业务数据

Args:


Returns:


Raises:


Examples:


Changes:
2016-01-30 y00292329 Created

"""
try:
self.semaphores['owned_object_lock'].acquire()
for k, v in self._currentComponentsDict.iteritems():
if k.startswith('uniautos.component.controller') or k.startswith('uniautos.component.upgrade'):
continue
self.threadComponentClassLock(k)
try:
self.removeComponent(*v.values())
finally:
self.threadUnlock(k)
self.markDirty()
finally:
self.semaphores['owned_object_lock'].release()

@validateParam(fault=Fault)
def registerFault(self, fault):
"""为设备注册故障

Args:
fault (Fault): 故障对象

Returns:
None

Raises:
None

Examples:
1、注册一个故障
fault = Fault()
device.registerFault(fault)

Changes:
2015-04-17 y00292329 Created

"""
if fault not in self.__faultList:
self.__faultList.append(fault)

@validateParam(fault=Fault)
def unregisterFault(self, fault):
"""移除设备中注册的故障

Args:
fault (Fault): 要移除的故障对象

Returns:
None

Raises:
None

Examples:
device.unregisterFault(fault)

Changes:
2015-04-17 y00292329 Created

"""
if fault in self.__faultList:
# fault.recover()
self.__faultList.remove(fault)

def recoverAllFaults(self):
"""恢复设备所有的故障

Args:
None

Returns:
None

Raises:
None

Examples:
1、恢复所有故障
device.recoverAllFaults()

Changes:
2015-04-17 y00292329 Created

"""
if self.__faultList:
faults = list(self.__faultList)
faults.reverse()
for fault in faults:
fault.recover()

@validateParam(alias=str)
def getCurrentOwnedComponents(self, alias=None):
"""根据别名，返回设备当前拥有的业务列表

Args:
alias (string): 业务的别名

Returns:
list: 设备当前拥有的业务列表

Raises:
None

Examples:
1、获取所有的Lun
storage.getCurrentOwnedComponents('lun')

Changes:
2015-04-17 y00292329 Created

"""
try:
self.semaphores['owned_object_lock'].acquire()
if alias:
if alias not in self._currentComponentsDict.iterkeys():
return {}
return self._currentComponentsDict[alias.lower()]
else:
return self._currentComponentsDict
finally:
self.semaphores['owned_object_lock'].release()

def createComponent(self, alias, *args, **kwargs):
"""创建业务

Args:
alias (string): 业务别名
args (list): 创建业务需要的参数
kwargs (dict): 创建业务需要的参数

Returns:
Component: 业务对象

Raises:
InvalidParamException: 当前设备不允许创建改业务

Examples:
1、创建LUN
device.createComponent('Lun',size='50G')

Changes:
2015-04-17 y00292329 Created

"""

try:

alias = alias.lower()
if alias not in self.__enableComponentsDict.iterkeys():
raise InvalidParamException("Alias: %s not in enabled components dict: \n %s" %
(alias, getFormatString(self.__enableComponentsDict)))
return self.classDict[self.__enableComponentsDict[alias][0]].create(self, *args, **kwargs)
finally:
pass

@property
def currentComponentsDict(self):
return self._currentComponentsDict

@property
def enableComponentsDict(self):
return self.__enableComponentsDict

def find(self, alias, forceSync=False, onlyNew=False, criteria=None,
createByConfigureEnv=False, onlyConfigureEnv=False, validatedByConfigureEnv=False):
"""查找当前设备的业务

Args:
alias (string): 业务别名, 如: "Lun", "pool".
forceSync (boolean): 是否强制同步，默认否
onlyNew (boolean): 只返回新发现的对象， 默认否
criteria (dict): 业务的查询条件, key为业务的Property, value为property值的字符串或正则表达式.
onlyConfigureEnv (bool): 查找标记为createByConfigureEnv和validatedByConfigureEnv的component,
-可选参数，默认为False.
createByConfigureEnv (bool): 只查找标记为createByConfigureEnv的component, 可选参数，默认为False.
validatedByConfigureEnv (bool): 只查找标记为validatedByConfigureEnv的component, 可选参数，默认为False.

Returns:
list: 业务对象列表

Raises:
InvalidParamException: 业务的查询条件有误 或 业务别名不存在

Examples:
# example1: 属性值name等于来查找
lunList = storageDevice.find('Lun', criteria={'name': params["lun_oldName"]})

# example2: 属性值name匹配正则表达式查找
namRegx = re.compile(r'^frank')
lunList = storageDevice.find('Lun', criteria={'name': namRegx})

# example3: 查找lun的capacity大于200GB的Lun对象
lunList = storageDevice.find("Lun", criteria={'capacity': {">": '200GB'}})

# example4: 演示调用自定义的回调函数来进行过滤查找
def test(param):
if param == "Online":
return True
else:
return False
lunList = storageDevice.find("Lun", criteria={'capacity': {">": '200GB'}, "running_status": test})

Changes:
2015-04-21 y00292329 Created

"""
alias = alias.lower()
if alias not in self.__enableComponentsDict.iterkeys():
raise InvalidParamException("Alias: %s not in enabled components dict: \n %s" %
(alias, getFormatString(self.__enableComponentsDict)))
newObjs = []
for fullName in self.__enableComponentsDict[alias]:
objs = self.classDict[fullName.lower()].sync(self, criteria, forceSync)
newObjs.extend(objs)

if criteria is None:
def meetCriteria(obj):
return True, obj
else:
def meetCriteria(obj):
try:
for k, v in criteria.iteritems():
if '\\s' in str(v) :
v = v.replace('\\s',' ')
propVal = obj.getProperty(k)
if propVal is None:
return False, obj
if not self.__compareCriteria(propVal, v):
return False, obj
return True, obj
except DeadComponentException:
self.logger.trace(str(obj.properties))
return False, obj
findObjs = []
if onlyNew:
findObjs = [obj for obj in newObjs if meetCriteria(obj)[0]]
else:
for fullName in self.__enableComponentsDict[alias]:
try:
self.threadComponentClassLock(fullName)
currentComponent = self.getCurrentOwnedComponents(fullName).values()
findObjs.extend([obj for obj in currentComponent[::-1] if meetCriteria(obj)[0]])
finally:
# pass
self.threadUnlock(fullName)
if onlyConfigureEnv:
findObjs = [obj for obj in findObjs if obj.isCreateByConfigureEnv or obj.isValidatedByConfigureEnv]
if createByConfigureEnv:
findObjs = [obj for obj in findObjs if obj.isCreateByConfigureEnv]
if validatedByConfigureEnv:
findObjs = [obj for obj in findObjs if obj.isValidatedByConfigureEnv]

# 如果是Vstore,同步数据到Unified Device
self.syncComponents(newObjs)
return findObjs

def __compareCriteria(self, propertyValue, criteria):
"""对比属性是否符合条件

Args:
propertyValue (Str) : 属性的值
criteria (Dict) : 判断的条件

Returns:
boolean: 符合条件返回True，否则返回False

Raises:
None

Examples:

Changes:
2015-04-21 y00292329 Created

"""
if isinstance(criteria, list):
return propertyValue in criteria or False
elif isinstance(criteria, dict):
# TODO
return self.__compareDictCriteria(propertyValue, criteria)
elif criteria.__str__().startswith('=': '10GB', '': '10GB', ' 0:
returnBool = True
checkMsgs.append("Component %s has %s Class locks request waiting in the queue "
% (fullName, inQueue))

objects = self.getCurrentOwnedComponents(fullName)

for compObj in objects:
if compObj.semaphores['in_use_by_thread'] != -1:
returnBool = True
checkMsgs.append("Component %s has a Component Instance lock by thread %s "
% (fullName, compObj.semaphores['in_use_by_thread']))

compThreadsQueue = len(self.semaphores['fifo_list'])
if compThreadsQueue > 0:
returnBool = True
checkMsgs.append("Component %s has %s Component Instance locks request waiting in the queue"
% (fullName, compThreadsQueue))

if returnBool:
msg = '\n'.join(checkMsgs)
self.logger.debug(msg)
return True
return False

def pauseNewComponentLocks(self):
"""Tells the framework to not allow any new thread locks for component classes.
If a thread has any active locks (or entries in the queue) though they will be allowed
to flush out. So basically this means to stop new locks but let any that are in progress
finish up. It will also allow new locks if a recursive lock is required to close out
a task. For example, if thread 1 has a lock on LUN and needs to lock Snapshots
too, the new snapshow lock will be allowed because it is required to complete the
transaction to release the LUN lock.

"""

self.logger.debug("Device: %s, ID: %s, Type: %s, Pausing the ability to get new Class Locks"
% (self, self.id, self.__class__.__name__))
self.semaphores['pause_new_locks'] = 1
sleep(5)

def unPauseNewComponentLocks(self):
"""Tells the framework to resume allowing new component locks
please also read pauseNewComponentLocks()

"""

self.logger.debug("Device: %s, ID: %s, Type: %s, Unpausing the ability to get new Class Locks"
% (self, self.id, self.__class__.__name__))
self.semaphores['pause_new_locks'] = 0

def setRetrySetting(self, count=5, interval=10, retry_codes=None, ignore_codes=None, wrapper_ignores=None):
"""设置设备的Retry和Ignore配置

Args:
count (int): 重试次数.
interval (int): 重试的间隔.
retry_codes (dict): 需要重试的命令回显关键字.
ignore_codes (dict): 需要忽略的命令回显关键字.
wrapper_ignores (dict): 需要忽略的命令回显关键字.
"""
if ignore_codes is not None:
self.__ignore_codes = ignore_codes

if retry_codes is not None:
self.__retry_codes = retry_codes

if wrapper_ignores is not None:
self.__wrapper_ignores = wrapper_ignores

self.__retry_interval = interval

self.__retry_count = count

def restoreRetrySetting(self):
"""恢复Default重试配置.
"""
self.__retry_codes = {}
self.__retry_count = 5
self.__retry_interval = 10
self.__ignore_codes = {}
self.__wrapper_ignores = {}

@property
def retry_codes(self):
"""Retry Codes"""
return self.__retry_codes

@property
def ignore_codes(self):
"""Ignore Codes"""
return self.__ignore_codes

@property
def retry_count(self):
"""Retry Count"""
return self.__retry_count

@property
def retry_interval(self):
"""Retry interval"""
return self.__retry_interval

def set_retry_codes(self, retry_codes):
"""设置设备的Retry Codes

Args:
retry_codes (dict): 需要重试的命令回显关键字.
"""
self.__retry_codes = retry_codes

def set_retry_count(self, count):
"""设置设备的Retry Count配置

Args:
count (int): 重试次数.
"""
self.__retry_count = count

def set_retry_interval(self, retry_interval):
"""设置设备的Retry Interval配置

Args:
retry_interval (int): 重试的间隔.
"""
self.__retry_interval = retry_interval

def set_ignore_codes(self, ignore_codes):
"""设置设备的Ignore Codes配置

Args:
ignore_codes (dict): 需要忽略的命令回显关键字.
"""
self.__ignore_codes = ignore_codes

def set_wrapper_ignores(self, wrapper_ignores):
"""设置设备的Ignore Codes配置

Args:
wrapper_ignores (dict): 需要忽略的命令回显关键字.
"""
self.__wrapper_ignores = wrapper_ignores

@property
def wrapper_ignores(self):
return self.__wrapper_ignores

def syncRemoveComponent(self, *args):
"""删除业务对象，主要由Component调用，Component在remove的方法中，调用device.removeComponent方法，设置自身所属的设备，同时将自身从设备中删除

Args:
component (Component): 业务对象

Raises:
InvalidParamException: 业务对象不属于当前设备
"""
try:
self.semaphores['owned_object_lock'].acquire()
for component in args:
fullClassName = component.__module__ + '.' + component.__class__.__name__
fullClassName = fullClassName.lower()

self.logger.debug('Removing component: %s, Id: %s' % (str(component.properties), id(component)))
component.zombify()
if id(component) in self._currentComponentsDict[fullClassName]:
del self._currentComponentsDict[fullClassName][id(component)]
else:
self.logger.debug("Component: %s have been removed" % id(component))

finally:
self.semaphores['owned_object_lock'].release()

def syncDeleteComponents(self, component):
#### For Vstore Add:
# 如果当前的设备是vstore，移除component时需要同时移除unified中的对象，
commonKey = component.getCandidateKeys()[0]
commonProperty = component.properties.get(commonKey)
fullClassName = component.__module__ + '.' + component.__class__.__name__
fullClassName = fullClassName.lower()
if self.__class__.__name__ == 'VstoreUnified':

# 如果当前的Component对象是vstore的，且当前使用vstore的对象查询，如果需要移除的component的device不是当前设备不需要移除
if not hasattr(self, 'unifiedDevice'):
return
unified = getattr(self, 'unifiedDevice')
if component.owningDevice is self and fullClassName in unified._currentComponentsDict:
try:
unified.threadComponentClassLock(fullClassName)
_components = unified._currentComponentsDict[fullClassName]
for _identity in _components.keys()[::-1]:
if _components[_identity].properties.get(commonKey) == commonProperty:
unified.syncRemoveComponent(_components[_identity])
break
finally:
unified.threadUnlock(fullClassName)
# 如果当前设备是unified，移除component时需要同时移除所有vstore中的component
else:
if not hasattr(self, 'vstoreDevices'):
return
vstoreDevices = getattr(self, 'vstoreDevices')
for _name, vstoreDevice in vstoreDevices.items():
if fullClassName in vstoreDevice._currentComponentsDict:
try:
vstoreDevice.threadComponentClassLock(fullClassName)
_components = vstoreDevice._currentComponentsDict[fullClassName]
for _identity in _components.keys()[::-1]:

if _components[_identity].properties.get(commonKey) == commonProperty:
vstoreDevice.syncRemoveComponent(_components[_identity])
break
finally:
vstoreDevice.threadUnlock(fullClassName)

def syncComponents(self, components):
"""如果是VstoreDevice，需要同步数据到UnifiedDevice
Args:
components (list) 需要同步的业务对象列表
"""
if not components:
return
fullClassName = components[0].classFullName
fullClassNameLower = fullClassName.lower()
commonKey = components[0].getCandidateKeys()[0]
isSyncUnified = components[0].syncUnified
if self.__class__.__name__ == 'VstoreUnified' and isSyncUnified:
unified = getattr(self, 'unifiedDevice')
try:
unified.threadComponentClassLock(fullClassNameLower)
if fullClassNameLower not in unified._currentComponentsDict:
unified._currentComponentsDict[fullClassNameLower] = {}
componentsCandidateKeys = {c.properties.get(commonKey): c
for c in unified.currentComponentsDict[fullClassNameLower].values()}
for component in components:
key = component.properties.get(commonKey)
if key is None:
continue
if key not in componentsCandidateKeys.keys():
self.logger.debug("Sync component to unified device")
_cmp = copy.copy(component)
_cmp.owningDevice = unified
# 重置isDead属性
_cmp.active()
_cmp.properties = component.properties
_cmp.rawProperties = component.rawProperties
else:
componentsCandidateKeys[key].properties = component.properties
componentsCandidateKeys[key].rawProperties = component.rawProperties

except Exception:
self.logger.exception("Sync Component to unified device failed.")
finally:
unified.threadUnlock(fullClassNameLower)

=========================================

#!/usr/bin/python
# -*- coding: UTF-8 -*-

import datetime
import threading
import re
import sys
import importlib
import traceback

from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.ObjectNotFoundException import ObjectNotFoundException
from UniAutos.Exception.PropertyException import PropertyException
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException

from UniAutos import Log
from UniAutos.Util.WrapperHolder import WrapperHolder
from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Wrapper.Api.ApiBase import ApiBase
from UniAutos.Wrapper.Tool.Selenium.UniWebBase import UniWebBase
from UniAutos.Util.Units import Units, SECOND
from UniAutos.Wrapper.Api.VmwareBase import VmwareBase
from UniAutos.Util.Time import sleep
from UniAutos.Util.Codec import getFormatString
from UniAutos.Wrapper.Template.CLI import CliWrapper
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import Adapter
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import CmdMapping

# NewWrapper = True
NewWrapper = False


class Dispatcher(object):
"""命令分发器,所有下发到设备的命令都会经由分发器，选择合适的Wrapper来执行
Wrapper分为：
CLI - Command Line Interface命令行接口模式
API - 通过API远程调用，比如Rest，Vmware SDK，etc.

Changes:
2015-06-01 y00292329 Created

"""

validateParamsFlag = False

ignoreDispatchPauseLock = False

# 操作allowTid的锁
__allDispatchLock = threading.Lock()
# 标记只允许下发命令的线程id
__allowTid = -1

def __init__(self):
"""Dispatcher命令下发的构造器，一般情况下作为Device Class类的基类。

Examples:
from UniAutos.Dispatcher import Dispatcher
class HostBase(Dispatcher)
...

"""
self.original_wrapper_list = []
self.wrapper_list = []
self._pauseDispatches = dict()
self._dispatchesInProgress = dict()
self._pauseDispatches['until'] = None
self.logger = Log.getLogger(__name__)
self.highPriorityView = dict()
# 操作allowTid的锁
self.__allDispatchLock = threading.Lock()
# 标记只允许下发命令的线程id
self.__allowTid = -1

@property
def dispatchesInProgress(self):
return self._dispatchesInProgress

def registerToolWrapper(self, host, wrapper=None, wrapper_type=None, require=None):
"""注册Wrapper,可以直接传递一个Wrapper对象，也可以传递一个函数，该函数可以生成一个Wrapper对象。

Args:
host (Host): Wrapper所属的主机

**下面参数必须二选一
wrapper (Wrapper): Wrapper对象
wrapper_type (str): Wrapper的类型

**如果wrapper_type被赋值，则require必须使用
require (function): 生成Wrapper的代码

Examples:
1. dispatcherClass.registerToolWrapper(host, wrapper=adminCliWrapper)
2. def requireFunc(params):
return AdminCli(params)
dispatcherClass.registerToolWrapper(host, wrapper_type='UniAutos.Wrapper.Tool.AdminCli.AdminCli'
require=requirFunc)

"""

wrapperDictInfo = {}
for hostWrapperPair in self.wrapper_list:
hostWrapper = hostWrapperPair["wrapper"]
wrapperClassName = hostWrapper.__module__ + '.' + hostWrapper.__class__.__name__
# if (wrapper_type is not None and wrapper_type == wrapperClassName) or \
# 修改判断方式，通过hostWrapperPair['wrapper_type']获取wrapper_type
if (wrapper_type is not None and wrapper_type == hostWrapperPair['wrapper_type']) or \
(wrapper is not None and wrapper.__module__ + '.' + wrapper.__class__.__name__ == hostWrapperPair[
'wrapper_type']):
self.logger.debug('The test script requested to re-register the wrapper: ' +
wrapperClassName + '\n but is was already registered')
return
if wrapper is not None:
wrapperDictInfo['require'] = 1
wrapperDictInfo['wrapper'] = wrapper
wrapperDictInfo['host'] = host
wrapperDictInfo["wrapper_type"] = wrapper.__module__ + '.' + wrapper.__class__.__name__
if isinstance(self, DeviceBase):
wrapper.setDevice(self)
else:
wrapperDictInfo['require'] = 0
# TODO Wrapper holder
wrapperDictInfo['wrapper'] = WrapperHolder(require, wrapper_type, host)
wrapperDictInfo['host'] = host
wrapperDictInfo["wrapper_type"] = wrapper_type
self.wrapper_list.append(wrapperDictInfo)

self.original_wrapper_list = self.wrapper_list

def getWrapper(self, wrapperClassName=None):
"""获取注册在这个Dispatcher上的wrapper/host对象

Args:
wrapperClassName (Str) : (可选参数)Wrapper Class Str，例如：AdminCli

Returns:
if wrapperClassName is specified, then returned the wrapper dict info
otherwise it returns the whole wrapper list
{ 'wrapper' : wrapperObject, 'host' : hostObject, 'wrapper_type' : classString, 'required' : boolean, 'require' : codeRefs}
{ 'wrapper' : wrapperObject, 'host' : hostObject, 'wrapper_type' : classString, 'required' : boolean, 'require' : codeRefs}
...

Raises:
UniAutosException

Examples:
None

"""

if wrapperClassName:
for wrapperinfoDict in self.wrapper_list:
if 'wrapper' in wrapperinfoDict:
fullName = wrapperinfoDict['wrapper'].__module__ + '.' + wrapperinfoDict[
'wrapper'].__class__.__name__
if re.match(r'UniAutos\.Wrapper\.(Tool|Api)(\.\w+)*' + wrapperClassName + '(\.\w+)*',
fullName,
re.IGNORECASE):
return wrapperinfoDict
elif 'wrapper_type' in wrapperinfoDict:
if re.match(r'UniAutos\.Wrapper\.(Tool|Api)(\.\w+)*' + wrapperClassName + '(\.\w+)*',
wrapperinfoDict['wrapper_type'],
re.IGNORECASE):
return wrapperinfoDict

raise UniAutosException("Unable to find the requested wrapper:['%s'] in the test bed. "
"Please verify the test bed is correct.\n"
"Current Wrapper list:\n %s" %
(wrapperClassName, getFormatString(self.wrapper_list)))

return self.wrapper_list

def dispatch(self, methodName, wrapperParamsDict=None, interactRule=None, option=None):
"""找到一个配置的Tool Wrapper去执行所对应的方法，调用该方法，并且返回相应的结果

Args:
methodName(String): Tool wrapper方法的名字
wrapperParamsDict(Dict): wrapper方法所用的方法参数

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value

rc : 返回命令所退出的Integer值，典型的一个非零的返回值就意味着整个命令失败了，反之成功
stdout : List, 包含命令返回回来的命令回显列表
stderr : List, 可选返回值，包含命令返回回来的命令错误回显列表
parsed : Dict, 可选返回值，包含解析之后的标准输出stdout的回显

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatcher.dispatch(methodName, methodParams)

"""
if wrapperParamsDict is None:
wrapperParamsDict = dict()
if interactRule is None:
interactRule = dict()
if option is None:
option = dict()
if NewWrapper:
if methodName.find("_") == -1:
newName = CmdMapping.WrapperHash.get(methodName, None)
if newName:
if isinstance(newName, dict):
extra = newName.get("extra", {})
wrapperParamsDict.update(extra)
func = Adapter.__dict__.get(newName["method"])
newName, wrapperParamsDict = func(wrapperParamsDict)
return self.runNewWrapper(newName, wrapperParamsDict, interactRule, option)
else:
return self.runNewWrapper(methodName, wrapperParamsDict, interactRule, option)
else:
if methodName.find("_") != -1:
return self.runNewWrapper(methodName, wrapperParamsDict, interactRule, option, 1)
else:
return self.__dispatchCommon(methodName, 1, wrapperParamsDict)

def runNewWrapper(self, methodName, params, interactRule=None, option=None, interrupt=0):
"""
Changes:
2016-05-10 y00292329 Created

"""
dispatching = None
try:
if interrupt != 0:
dispatching = self.markAsDispatching()
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
result = cliWrapper.runWrapper(methodName, params, interactRule, option)
return [result]
finally:
if dispatching:
dispatching()

def setCliWrapperConf(self, option):
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
cliWrapper.setOption(option)

def getClassPropertyDispatch(self, componentClass, propertiesList=None):
"""检索业务类的属性(如果没有给定要检索的属性，则检索所有属性)

Args:
componentClass (type): 业务类型
propertiesList (list): 需要检索的属性

Returns:
propsSetLists(List) - Properties array, include the prop dict returned from
[{
idProp : id,
prop1 : val1,
prop1 : val2,
...
}
...
]

Raises:
UniAutosException

Examples:
#cls为component的class名的字符串
#properties为需要获取的属性列表
unifiedDevice.getClassPropertyDispatch(cls, properties)

"""

allProps = False

if not propertiesList:
allProps = True
propertiesList = []

propertiesDict = {}
for prop in propertiesList:
propertiesDict[prop] = 1

propsSetLists = []
for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
hostObj = twInfoDict['host']
if NewWrapper:
wrapperList = filter(
lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
temp = self.createWrapperParams(componentClass.__module__ + '.' + componentClass.__name__, "show")
result = cliWrapper.runWrapper(temp.get("methodName"), temp.get("params", {}))
info = result.get('parser', {})
propInfoDict = {'propSets': [info], "properties": propertiesList}
else:
# propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, compObject, propertiesList, hostObj)
propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, hostObj=hostObj,
propertiesList=propertiesDict.keys(), )
for propsDict in propInfoDict['propSets']:
propsSetLists.extend(propsDict.values())

for props in propInfoDict['properties']:
if props in propertiesDict:
del propertiesDict[props]

if len(propertiesDict) == 0:
break

if not allProps and len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' + wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('THe following properties for %s could not be '
'retrieved from any of configured tool wrappers (%s): %s'
% (componentClass, ','.join(wrappers), ','.join(propertiesDict.keys())))

return propsSetLists

def syncClassDispatch(self, componentClass, criteriaDict=None, syncParamsDict=None, device=None, ):
"""使用Tool Wrappers同步更新这个类别里面所有对象实例的properties

Args:
componentClass(String): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
criteriaDict(Dict): 根据同步的对象属性Dict和过滤的Dict进行匹配
syncParamsDict(Dict): 需要同步的参数属性Dict
device(UniAUtos.Device): UniAutos Device 对象

Returns:
returnDict(Dict): 获得相应的Wrapper对象

Raises:
UniAutos.Exception.UniAutosException

"""

if not syncParamsDict:
syncParamsDict = {}
classes = []
candidateKeys = componentClass.getCandidateKeys()

searchKeys = candidateKeys
if criteriaDict is not None:
for critProp in criteriaDict.keys():
if critProp not in searchKeys:
searchKeys.append(critProp)

propInfoDict = {}
twInfoDict = {}
if NewWrapper:
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
propInfoDict = self.createPropertyInfoHash(componentClass, searchKeys)
twInfoDict = wrapperList[0]
else:
for wrapperDict in self.wrapper_list:
wrapperObj = wrapperDict['wrapper']
if wrapperDict['wrapper'].getDevice is None:
if (isinstance(self, DeviceBase)):
wrapperDict['wrapper'].setDevice(self)
propInfoDict = wrapperObj.createPropertyInfoHash(componentClass, searchKeys)
loopBreak = False
if criteriaDict is not None:
for prop in criteriaDict:
if prop not in propInfoDict:
loopBreak = True
break
if loopBreak:
continue
twInfoDict = wrapperDict
break
else:
if propInfoDict:
twInfoDict = wrapperDict
break
else:
continue
if twInfoDict is None:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('None of the configured tool wrappers (%s) supply '
'any of the defined identifier properties (%s) '
'for %s.' % (','.join(wrappers), ','.join(searchKeys), componentClass))

host = twInfoDict.get('host')
wrapper = twInfoDict.get('wrapper')

methodDict = {}
partial = False
if NewWrapper:
result = propInfoDict.get("show")
if isinstance(result, dict):
params = result.get("extra", {})
if result.get("method").startswith("adapter"):
methodName, params = Adapter.__dict__.get(result["method"])(params)
else:
methodName = result.get("method")
syncParamsDict.update(params)
partial = result.get("partial", False)
else:
methodName = result
methodDict = {"methdName": methodName}
else:
for propValue in propInfoDict.values():
if propValue.has_key('getmethod'):
funcId = propValue['getmethod']
if not methodDict.has_key(funcId):
methodDict[funcId] = funcId
if not syncParamsDict:
classObj = wrapper.getCommonPropertyInfo(propValue['getmethod'], searchKeys)
classes.extend(classObj)

if len(classes) == 0:
classes.append(componentClass.__module__ + '.' + componentClass.__name__)

# threadLock here for all classes
threadComponentClassLocks = []
try:
for klass in classes:
device.threadComponentClassLock(klass)
threadComponentClassLocks.append(klass)
newCriteriaDict = {}
optionKeys = candidateKeys + componentClass.getOptionKeys()

fullFind = True

if criteriaDict is not None:
for criteriaKey in criteriaDict.keys():
if type(criteriaDict[criteriaKey]).__name__ in ['str', 'bool', 'int', 'float']:
if (criteriaKey in optionKeys):
newCriteriaDict[criteriaKey] = criteriaDict[criteriaKey]

if len(newCriteriaDict) != 0:
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(newCriteriaDict)
else:
tempKeys = componentClass.getCandidateKeys()
if criteriaDict:
for criteriaKey in criteriaDict.keys():
if (criteriaKey in tempKeys):
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(criteriaKey)

twProps = []
for methodName in methodDict.values():
runWrapperParams = {}
if host is not None:
runWrapperParams['host'] = host
runWrapperParams['wrapper'] = wrapper
ret = self.__callWrapper(runWrapperParams, methodName, syncParamsDict, 1)

for result in ret:
twProps.extend(result['parser'].values())
if result.get("partial", False) or partial:
fullFind = False
return {'properties': twProps,
'classes': classes,
'full_find': fullFind,
'thread_locks': threadComponentClassLocks}
except Exception as e:
self.logger.info(traceback.format_exc())
for name in threadComponentClassLocks:
device.threadUnlock(name)
raise e

def getPropertyDispatch(self, compObject, propertiesList):
"""为相应的Component对象通过查询所配置的Tool Wrappers获取所需要的属性,直到所有属性被查询到

Args:
compObject(UniAUtos.Component.ComponentBase): UniAutos Component对象
propertiesList(List): 所想要得到的属性列表

Returns:
objPropsDict(Dict): 获得对应对象的属性Dict

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatcher.getPropertyDispatch(self, properties)

"""

allProps = False
if propertiesList is None:
propertiesList = []
if not propertiesList:
allProps = True

propertiesDict = {}
for prop in propertiesList:
propertiesDict[prop] = 1

componentClass = compObject.__module__ + "." + compObject.__class__.__name__

objPropsDict = {}
for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
hostObj = twInfoDict['host']
if NewWrapper:
wrapperList = filter(
lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
temp = self.createWrapperParams(componentClass, "detail")
params = {}
for k, v in temp.get("paramsName").items():
params[k] = compObject.properties.get(v, "")
params.update(temp.get("params", {}))
result = cliWrapper.runWrapper(temp.get("methodName"), params)
info = result.get('parser', {})
propInfoDict = {'propSets': [info], "properties": propertiesList}
else:
propInfoDict = self.__getPropertyDispatchTw(componentClass, wrapperObj, compObject, propertiesList,
hostObj)

for propSetDict in propInfoDict['propSets']:
propsDict = None
if len(propSetDict.keys()) == 1:
propsDict = propSetDict.values()[0]
else:
for key in compObject.getCandidateKeys():
if not compObject.isClean([key]):
compObject.getProperty(key)
if compObject.isClean([key]):
keyVal = compObject.getProperty(key)
if keyVal in propSetDict:
propsDict = propSetDict.get(keyVal)
break
if not propsDict:
wrapperName = compObject.__module__ + '.' + compObject.__class__.__name__
objectName = compObject.__module__ + '.' + compObject.__class__.__name__
msg = 'Failed to detect which candidate key is used for ' + \
wrapperName + ' for ' + objectName + '\'s properties'

candidateKeys = compObject.getCandidateKeys()
msg = msg + "\nResult of the wrapper call:\n" + getFormatString(propInfoDict)
msg = msg + "\nAll the properties that exist on this object already\n" + getFormatString(
compObject.properties)
msg = msg + "\nCandidate Keys tried:\n" + getFormatString(candidateKeys)
raise PropertyException(msg)
objPropsDict = dict(propsDict, **objPropsDict)

for props in propInfoDict['properties']:
if props in propertiesDict:
del propertiesDict[props]

if NewWrapper or (not allProps and len(propertiesDict) == 0):
break

if not allProps and len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('The following properties for %s could not be '
'retrieved from any of configured tool wrappers (%s): %s'
% (compObject.classFullName,
','.join(wrappers),
','.join(propertiesDict.keys())))

return objPropsDict

def setPropertyDispatch(self, compObject, propertiesDict):
"""为相应的Component对象通过查询所配置的Tool Wrappers设置属性的值,直到所要求的属性被设置

Args:
compObject(UniAutos.Component.ComponentBase): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
propertiesDict(Dict): 需要被设置的属性Dict，包含属性的Key-Value

Returns:
objPropsDict(Dict): 获得被设置的对象属性Dict

Raises:
UniAutos.Exception.UniAutosException

Examples:
dispatch.setPropertyDispatch(self, properties)

"""

parsedDict = {}
if NewWrapper:
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
componentClass = compObject.__module__ + '.' + compObject.__class__.__name__
temp = self.createWrapperParams(componentClass, "update")
params = {}
for k, v in temp.get("paramsName").items():
params[k] = compObject.properties.get(v, "")
params.update(propertiesDict)
ret = cliWrapper.runWrapper(temp.get("methodName"), params)
compObject.markDirty(propertiesDict.keys())
return parsedDict

for twInfoDict in self.wrapper_list:
wrapperObj = twInfoDict['wrapper']
propsNameList = propertiesDict.keys()
if wrapperObj.getDevice is None:
if isinstance(self, DeviceBase):
wrapperObj.setDevice(self)

className = compObject.__module__ + '.' + compObject.__class__.__name__
twPropertyDict = wrapperObj.createPropertyInfoHash(className, propsNameList)

methodDict = {}
for props in propsNameList:
if twPropertyDict.has_key(props) and twPropertyDict[props].has_key('setmethod'):
funcId = twPropertyDict[props]['setmethod']
if funcId not in methodDict:
methodDict[funcId] = dict()
methodDict[funcId]['method'] = funcId
if 'properties' not in methodDict[funcId]:
methodDict[funcId]['properties'] = list()
methodDict[funcId]['properties'].append(props)

for funcId in methodDict.keys():
method = methodDict[funcId]['method']
setPropsList = methodDict[funcId]['properties']
setParamDict = {'object': compObject}

for setProp in setPropsList:
setParamDict[setProp] = propertiesDict[setProp]

runWapperParamsDict = {}
if 'host' in twInfoDict and twInfoDict['host']:
runWapperParamsDict['host'] = twInfoDict['host']
runWapperParamsDict['wrapper'] = twInfoDict['wrapper']

retList = self.__callWrapper(runWapperParamsDict, method, setParamDict, 1)
del setParamDict['object']

compObject.markDirty(setParamDict.keys())

if (retList[0].has_key('parser')):
retDict = retList[0].values()

for key in retDict.keys():
parsedDict[key] = retDict[key]

cleanPropsDict = {}

for setProps in setParamDict.keys():
if retDict[setProp] is not None:
cleanPropsDict[setProp] = retDict[setProp]

compObject.markClean(cleanPropsDict)

for setProps in setPropsList:
del propertiesDict[setProps]

if len(propertiesDict) == 0:
break

if len(propertiesDict) > 0:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('The following properties for %s could not be '
'set via any of configured tool wrappers (%s): %s'
% (compObject.classFullName,
','.join(wrappers),
','.join(propertiesDict.keys())))

return parsedDict

def getDispatchInfo(self, methodName, wrapperParamsDict={}):
"""遍历Wrapper列表，根据Wrapper的方法名和Wrapper方法的参数得到相应的Wrapper对象

Args:
methodName(String): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
wrapperParamsDict(Dict): Wrapper方法的参数字典

Returns:
returnDict(Dict): 获得相应的Wrapper对象

"""
for wrapperDict in self.wrapper_list:
if hasattr(wrapperDict['wrapper'], methodName):
returnDict = {'wrapper': wrapperDict['wrapper']}
if 'host' in wrapperDict and wrapperDict['host']:
returnDict['host'] = wrapperDict['host']
returnDict['command'] = wrapperDict['host'].getCmdObj
return returnDict

def __dispatchCommon(self, methodName, interrupt, wrapperParamsDict={}):
"""该方法被用于调用wrapper dispatch方法，普通wrapper分发调用

Args:
methodName (String) : 工具Wrapper的方法名称
interrupt (Boolean) : 使Wrapper方法能被后台调用
wrapperParamsDict (Dict) : Wrapper方法的参数字典

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

Changes:
2015-06-01 y00292329 Created

"""

Dispatcher.validateParamsFlag = True
wrapperInfoDict = self.getDispatchInfo(methodName, wrapperParamsDict)
Dispatcher.validateParamsFlag = False

if wrapperInfoDict is None or 'wrapper' not in wrapperInfoDict:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' + wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise InvalidParamException('None of the configured wrappers (%s) provide '
'the requested method (%s) with your input parameters '
'(%s). Any errors will be shown in a debug meessage right'
' before this exception'
% (','.join(wrappers), methodName, getFormatString(wrapperParamsDict.keys())))

runWrapperParams = {}
if 'host' in wrapperInfoDict and wrapperInfoDict['host']:
runWrapperParams['host'] = wrapperInfoDict['host']
runWrapperParams['wrapper'] = wrapperInfoDict['wrapper']
if wrapperInfoDict['wrapper'].getDevice is None:
if isinstance(self, DeviceBase):
wrapperInfoDict['wrapper'].setDevice(self)

return self.__callWrapper(runWrapperParams, methodName, wrapperParamsDict, interrupt)

def activateCan(self, can, wrapperObj, wrapperParamsDict=None):
"""Activate Can method in wrapper object with the wrapper parameters

Args:
can (String) : 工具Wrapper的方法名称
wrapperObj (Wrapper Object) : 工具Wrapper的方法名称
wrapperParamsDict (Dict) : Wrapper方法的参数字典

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

"""

if re.search("instancemethod", str(type(can))):
if wrapperParamsDict:
ret = can(wrapperParamsDict)
else:
ret = can()
else:
ret = can(wrapperObj, wrapperParamsDict)

if isinstance(ret, dict):
ret = [ret]
return ret

def __callWrapper(self, runWrapperParamsDict, methodName, wrapperParamsDict={}, interrupt=0):
"""该方法被用于调用wrapper

Args:
runWrapperParamsDict (Dict) : wrapper参数字典
-包含以下key-values:
host (UniAutos.Device.Host) : 主机对象，能够调用执行wrapper方法
wrapper (UniAutos.Wrapper) : wrapper对象
methodName (String) : 工具Wrapper的方法名称
wrapperParamsDict (Dict) : Wrapper方法的参数字典
interrupt (Boolean) : 使Wrapper方法能被后台调用

Returns:
ret(List): 一个包含多个Dict的List，以下所对应的Key-Value
{
'rc' (Integer) : 命令执行后的范围值，通常情况下非零的rc表示命令有错
'stdout' (List) : 命令的标准输出，将每行作为一个数组的元素并且返回数组
'stderr' (List) : 命令的标准错误，将每行作为一个数组的元素并且返回数组
'parsed' (Dict) : 命令回显解析之后的字典格式
}

Raises:
UniAutos.Exception.UniAutosException

Examples:
None

"""

curWrapper = runWrapperParamsDict['wrapper']
if isinstance(curWrapper, WrapperHolder):
specifiedType = curWrapper['wrapper_type']
classNameList = specifiedType.split('.')
className = classNameList.pop()
module = ".".join(classNameList)
__import__(module)
moduleClass = getattr(sys.modules[specifiedType], className)
for wrapper in self.wrapper_list:
if isinstance(wrapper, moduleClass):
curWrapper = wrapper

ret = []
dispatching = None
if interrupt != 0:
dispatching = self.markAsDispatching()

try:
wrapperClassNm = '%s.%s' % (curWrapper.__module__, curWrapper.__class__.__name__)
self.logger.debug("Running: %s\nMethod: %s\nWith params: %s" %
(wrapperClassNm, methodName, getFormatString(wrapperParamsDict)))

if isinstance(curWrapper, ApiBase):
can = curWrapper.can(methodName)
if can is None:
raise CommandException(
"Invalid method name '%s' specified for wrapper '%s'" % (methodName, wrapperClassNm))

if isinstance(curWrapper, VmwareBase):
timeSpan = datetime.datetime.now() - curWrapper.connectedTime
if Units.compareTime(str(timeSpan.seconds) + 'S', '20M') >= 0:
curWrapper.disConnect()
curWrapper.connect()
curWrapper.connectedTime = datetime.datetime.now()

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, UniWebBase):
can = curWrapper.can(methodName)
if can is None:
raise CommandException(
"Invalid method name '%s' specified for wrapper '%s'" % (methodName, wrapperClassNm))

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, CliWrapper):
ret = [curWrapper.runWrapper(methodName, wrapperParamsDict)]
else:
newParams = {}
newParams['wrapper'] = curWrapper
newParams['method'] = methodName
newParams['params'] = wrapperParamsDict
ret = runWrapperParamsDict['host'].runToolWrapperMethod(newParams)

return ret
finally:
if dispatching:
dispatching()

def __getPropertyDispatchTw(self, componentClass, wrapperObj, compObject=None, propertiesList=None, hostObj=None):
"""调用Wrapper对象里面的方法获取所对应对象的属性

Args:
componentClass (String) : 所需要查询属性的类名
wrapperObj (UniAutos.Wrapper) : 指定哪一个wrapper对象来查询属性列表
compObject (UniAutos.Component) : 可选参数 ，限制wrapper只查询该对象的属性
propertiesList (List) : 可选参数， 需要查询的属性列表，默认值为None，表示查询所有属性
hostObj (UniAutos.Device.Host) : 指定哪一个主机调用执行Wrapper命令

Returns:
ret(Dict): 一个包含keys('propSets', 'properties')的字典

'propSets' (List) : 包含多个命令行回显的解析格式，例如
[{
idVar1 : {
'id' : idVar1
'prop' : val
}

idVar1 : {...}

}]

'properties' (List) : 返回一个List包含所有属性名称


Raises:
UniAutos.Exception.UniAutosException

Examples:
None

"""

allProps = False
if not propertiesList:
allProps = True
propertiesList = []

if not wrapperObj.getDevice():
if isinstance(self, DeviceBase):
wrapperObj.setDevice(self)

twPropertyDict = wrapperObj.createPropertyInfoHash(componentClass, propertiesList)

if (allProps):
propertiesList = twPropertyDict.keys()

methodDict = {}
handlePropsList = []

for prop in propertiesList:
if twPropertyDict.has_key(prop) and twPropertyDict[prop].has_key('getmethod'):
handlePropsList.append(prop)
funcId = twPropertyDict[prop]['getmethod']
if funcId not in methodDict:
methodDict[funcId] = dict()
methodDict[funcId]['method'] = twPropertyDict[prop]['getmethod']
if not methodDict[funcId].has_key('properties'):
methodDict[funcId]['properties'] = []

if not allProps:
methodDict[funcId]['properties'].append(prop)

propSetsList = []
for funcId in methodDict.keys():
method = methodDict[funcId]['method']
getPropsList = methodDict[funcId]['properties']
getParamDict = {'options': getPropsList}
if compObject:
getParamDict['object'] = compObject
runWapperParamsDict = {}
if hostObj is not None:
runWapperParamsDict['host'] = hostObj
runWapperParamsDict['wrapper'] = wrapperObj

retList = []

try:
retList = self.__callWrapper(runWapperParamsDict, method, getParamDict, 1)
except Exception, exe:
if isinstance(exe, ObjectNotFoundException) and 'object' in getParamDict:
if getParamDict.has_key('object'):
getParamDict['object'].getDevice.removeObject(getParamDict['object'])
getParamDict['object'].checkDead()
else:
raise exe

for ret in retList:
if ret.has_key('parser') and len(ret['parser'].keys()) > 0:
propSetsList.append(ret['parser'])

return {'propSets': propSetsList, 'properties': handlePropsList}

def isThisThreadDispatching(self):
"""判断当前线程是否在Dispatching处理中。

Examples:
host.isThisThreadDispatching

"""

dispatchingThreads = self._dispatchesInProgress
tid = threading.currentThread().ident
for thd in dispatchingThreads:
if thd == tid:
self.logger.debug('This thread [%d] is currently dispatching' % tid)
return True
return False

def isDispatching(self):
"""判断当前Dispatcher是否正在下发命令
Returns:
Boolean - True: it stands for the thread is dispatching
False: it means the thread is not dispatching
"""

dispatchingThreads = self._dispatchesInProgress

# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
if hasattr(self, 'vstoreControllers') and not isVstoreDevice:
# 如果当前控制器对象有Vstore在下发业务，则直接返回正在下发业务, 不必再判断unified的控制器对象
# 如果都没有下发业务，则再判断unified的控制器对象.

self.logger.debug("Current unified controller have vstore: %s" % self.vstoreControllers)
self.logger.debug("Check Current Unified Controller's Vstore Controllers is Dispatching.")
for name in self.vstoreControllers:
_dispatching = self.vstoreControllers[name].isDispatching()
if _dispatching:
return True

self.logger.debug("Current Host Object[%s] dispatchesInProgress :%s, Is Vstore Device: %s"
% (self, dispatchingThreads, isVstoreDevice))
if dispatchingThreads:
module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if isinstance(self, moduleClass):
self.logger.debug(
'The following threads are dispatching to this host %s: %s' % (self.localIP, dispatchingThreads))
else:
self.logger.debug('The following threads are dispatching to this Device: %s' % dispatchingThreads)
return True
return False

def markAsDispatching(self):
"""标记当前的Dispatcher正在下发命令

Changes:
2015-05-19 y00292329 Created

"""
# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
self.logger.debug("Current Host Object: %s, pauseDispatches: %s, Is VstoreDevice: %s"
% (self, self._pauseDispatches, isVstoreDevice))

# 如果是Vstore的设备还需要检查对应的unified设备有没有被pause
unifiedPaused = False
if isVstoreDevice and hasattr(self, 'unifiedController'):
self.logger.debug("This is a vstore controller, Unified controller[%s] pauseDispatches: %s" %
(self.unifiedController, self.unifiedController._pauseDispatches))
if self.unifiedController._pauseDispatches.get('until'):
unifiedPaused = True
# 如果unified pause了但是vstore未pause， 需要设置vstore pause
if self._pauseDispatches['until'] is None:
self._pauseDispatches['until'] = self.unifiedController._pauseDispatches.get('until')
# 如果vstore或者unified被pause了那么当前的控制器不管是unified还是vstore都不能下发命令
if self._pauseDispatches['until'] or unifiedPaused:

# 设置_allowTid一般为unified，如果不是unified必须进行pause
if (self.__allowTid == -1 and DeviceBase.globalDoesThreadHaveAnyLocks() and not isVstoreDevice) or \
self.__allowTid == threading.currentThread().ident:
self.logger.debug('Dispatches are paused on this device'
' but we can go because we are either in the middle of a dispatch already or '
'we have an active class lock（Tid:%d）' % self.__allowTid)
# 处于被标记状态的正在下发命令的dispatcher不能被pause
elif threading.currentThread().ident in self._dispatchesInProgress:
self.logger.debug('Dispatches are paused on this device '
'but we can go because we are in the middle of a dispatch already '
'(Tid:%d)' % threading.currentThread().ident)
else:

module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if isinstance(self, moduleClass):
self.logger.debug('Dispatches on this host (%s) have been '
'paused until %s, Current Object: %s, is Vstore Device: %s.'
% (self.localIP, self._pauseDispatches['until'], self, isVstoreDevice))
else:
self.logger.debug('Dispatches on this Device have been '
'paused until %s, Current Object: %s, is Vstore Device: %s '
% (self._pauseDispatches['until'], self, isVstoreDevice))
while self._pauseDispatches['until'] is not None and datetime.datetime.now() < \
self._pauseDispatches['until']:
sleep(1)
if not self._pauseDispatches['until']:
break

if isinstance(self, moduleClass):
self.logger.debug('Dispatches have resumed on host (%s)' % self.localIP)
else:
self.logger.debug('Dispatches have resumed on Device')
# 这里只需要设置自己设备为None， 其他设备进行下发命令是会自行判断并设置
self._pauseDispatches['until'] = None

origLockValue = Dispatcher.ignoreDispatchPauseLock
Dispatcher.ignoreDispatchPauseLock = True
tid = threading.currentThread().ident
if tid not in self._dispatchesInProgress:
self._dispatchesInProgress[tid] = 0
self._dispatchesInProgress[tid] += 1
self.logger.debug(' markAsDispatching in dispatchesInProgress %s' % str(self._dispatchesInProgress))

def dispatching():
self._dispatchesInProgress[tid] -= 1
if self._dispatchesInProgress[tid] == 0:
del self._dispatchesInProgress[tid]
Dispatcher.ignoreDispatchPauseLock = origLockValue

return dispatching

def pauseDispatches(self, duration):
"""暂停下发命令，设置暂停时间长短

Args:
duration (str): 暂停的时长，例如 30S

Examples:
#可以参照UniAutos.Component.Controller.Huawei.OceanStor.StorController的reboot方法
#并且结合pauseCommandsDispatch和unpauseCommandDispatch
controllerHost.pauseDispatches(pausingTime)

"""

matchObj = re.match(r'\d+$', duration)
if matchObj:
duration += 'S'
duration = Units.getNumber(Units.convert(duration, SECOND))
unit = datetime.datetime.now() + datetime.timedelta(seconds=duration)
self._pauseDispatches['until'] = unit

# 新增定位注释，用于定位Vstore的pause信息
isVstoreDevice = self.isVstoreDevice if hasattr(self, 'isVstoreDevice') else False
self.logger.debug("Current Controller Hosts Object: %s, _pauseDispatches: %s, Is Vstore Device: %s"
% (self, self._pauseDispatches, isVstoreDevice))

tid = threading.currentThread().ident
module = 'UniAutos.Device.Host.HostBase'
__import__(module)
moduleClass = getattr(sys.modules[module], "HostBase")
if duration == 0:
if isinstance(self, moduleClass):
self.logger.debug('Thread %d is unpausing dispatches to this host [%s]' % (tid, self.localIP))
else:
self.logger.debug('Thread %d is unpausing dispatches to this Device' % tid)
else:
if isinstance(self, moduleClass):
self.logger.debug('Thread %d is issuing a pause for dispatches to this host [%s], '
'pause: %s second' % (tid, self.localIP, duration))
else:
self.logger.debug('Thread %d is issuing a pause for dispatches to this Device, '
'pause: %s second.' % (tid, duration))
# TODO 这里的睡眠5秒是做什么的不知道，暂时注释掉
# sleep(5)

def createPropertyInfoHash(self, cls, properties=None):
if properties is None:
properties = list()
if not isinstance(cls, str):
cls = cls.__module__ + '.' + cls.__name__
return CmdMapping.MethodHash.get(cls)

def createWrapperParams(self, clsName, method, params=None):
methodDict = CmdMapping.MethodHash.get(clsName, {})
if method == "show":
result = methodDict.get(method, "")
params = {}
if isinstance(result, str):
methodName = result
elif isinstance(result, dict):
params = result["extra"]
methodName, params = Adapter.__dict__.get(result["method"])(params)
return {"methodName": methodName, "params": params}
elif method == "detail":
result = methodDict.get("show", "")
params = {}
if isinstance(result, str):
methodName = result
elif isinstance(result, dict):
if result.get("method").startswith("adapter"):
params = result.get("extra", {})
methodName, params = Adapter.__dict__.get(result["method"])(params)
else:
methodName = result.get("method")
paramName = methodDict.get("detail", {}).get("param")
extraparams = methodDict.get("detail", {}).get("extra", {})
propertiesName = methodDict.get("detail", {}).get("properties", "id")
return {"methodName": methodName, "params": extraparams, "paramsName": {paramName: propertiesName}}
elif method == "update":
methodName = methodDict.get("update", "")
paramName = methodDict.get("detail", {}).get("param")
propertiesName = methodDict.get("detail", {}).get("properties", "id")
return {"methodName": methodName, "paramsName": {paramName: propertiesName}}
return {}

def setHighPriorityView(self, wrapperName, params=None):
"""
设置高优先级的VIEW，命令会有限在该视图下发
Args:
wrapperName: 视图名 (vstore, admincli)
params: 切换到该视图的参数

Returns:

"""
self.highPriorityView['name'] = wrapperName
self.highPriorityView['view_params'] = params
if wrapperName == "vstore" and not self.highPriorityView.get("cmdTemplate", ""):
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C00").__dict__
self.highPriorityView['cmdTemplate'] = cmdTemplate

def selectHighPriorityView(self, cmdSpace, version):
"""
根据设置的HighPriorityView， 选择命令下发的模式，在HostBase.run 方法中调用
Args:
cmdSpace:

Returns:

"""
if self.highPriorityView.get('name') == "vstore":
cmd = " ".join(cmdSpace['command'])
if "|filter" in cmd:
awname = cmd.split('|')[0].strip().replace(" ", "_")
cmdSpace['waitstr'] = None
else:
awname = re.split(r"\s*\S+\s*=\s*\S*\s*", cmd)[0].replace(" ", "_")
if version in ['V300R006C00']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C00").__dict__
elif version in ['V500R007C00', 'V500R007C10', 'V300R006C10', 'V300R006C20']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V500R007C00").__dict__
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
elif version in ['V500R007C20', 'V300R006C21', 'V300R006C30', 'V500R007C30', 'V300R006C50',
'V500R007C50', 'V300R006C60', 'V500R008C00', "V500R007C60 Kunpeng", "V500R007C60"]:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V500R007C20").__dict__
elif version in ['V300R006C01']:
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "V300R006C01").__dict__
else:
cmdTemplate = self.highPriorityView['cmdTemplate']
if awname in cmdTemplate:
if 'vstore' in cmdTemplate[awname]['view']:
cmdSpace['sessionType'] = self.highPriorityView['name']
cmdSpace['view_params'] = self.highPriorityView['view_params']
return cmdSpace
# if self.highPriorityView.get('name') == "vstore":
# cmd = " ".join(cmdSpace['command'])
# awname = re.split(r"\s*\S+\s*=\s*\S*\s*", cmd)[0].replace(" ", "_")
# if awname in self.highPriorityView['cmdTemplate']:
# if self.highPriorityView['name'] in self.highPriorityView['cmdTemplate'][awname]['view']:
# cmdSpace['sessionType'] = self.highPriorityView['name']
# cmdSpace['view_params'] = self.highPriorityView['view_params']
# return cmdSpace

def setHighPriorityWrapper(self, *wrappers):
"""
设置wrapper优先级
Args:
*wrappers: wrapper名例如"admincli", "developer", "upgrade"

Returns:

"""

def getkey(e):
try:
wrapper_type = e['wrapper_type']
wrapperName = wrapper_type.split('.')[-1].lower()
lens = len(wrappers)
for idx, val in enumerate(wrappers):
if wrapperName.startswith(val.lower()):
return idx
return lens
except Exception as e:
self.logger.warn(e)
return 999

self.original_wrapper_list = self.wrapper_list
self.wrapper_list = sorted(self.wrapper_list, key=getkey)

# @classmethod
def setAllowDispatchThread(self, tid=None):
"""
设置dispatch全局锁，可以锁住全局dispatch并且只允许当前线程下发命令
Args:
tid (int): (optional)线程id，默认将全局dispatch锁住，设置只允许当前线程下发命令

Returns:
None

Raises:
None

Examples:
设置全局dispatch锁
allControllers[0].getHostObject().setAllowDispatchThread()
恢复全局dispatch锁
allControllers[0].getHostObject().setAllowDispatchThread(-1)
"""
if tid is None:
tid = threading.currentThread().ident
self.__allDispatchLock.acquire()
self.__allowTid = tid
# unified设置了vstore也需要设置
if (hasattr(self, 'isVstoreDevice') and not getattr(self, 'isVstoreDevice')
and hasattr(self, 'vstoreControllers')):
for name in getattr(self, 'vstoreControllers', {}):
getattr(self, 'vstoreControllers')[name].setAllowDispatchThread(tid=tid)
self.__allDispatchLock.release()

=====================================================================================

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2016

修改记录: wangaiguo 00251499 created

"""
from SSHConnection import SSHConnection
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.CommandException import CommandException


class SQLConnection(SSHConnection):
"""普通SQL连接

Args:
hostname (str): ip地址
username (str): 用户名
password (str): 密码
dbUser (str): 数据库用户
dbPasswd (str): 数据库用户密码
publickey (str): 密钥
port (str): 端口

Returns:


Raises:


Examples:


Changes:

"""
def __init__(self, hostname, username, password=None, dbUser='sysdba', dbPasswd=None, directory=None, privateKey=None, port=22):
super(SQLConnection, self).__init__(hostname, username, password=password, privateKey=privateKey, port=port)
self.hostUser = username
self.dbUser = dbUser
self.dbPasswd = dbPasswd
self.directory = directory
self.login()

def __del__(self):
self.close()

def login(self):
"""登陆设备

Args:
None

Returns:
None

Raises:
UniAutosException

Examples:


Changes:
2015-12-29 y00292329 Created

"""
if self.transport is None or not self.transport.is_active():
t = self.createClient()
self.transport = t
self.authentication(self.transport)
channel = self.transport.open_session()
channel.get_pty(width=200, height=200)
channel.invoke_shell()
channel.settimeout(10)
self.channel = channel
defaultWaitStr = 'SQL>'
self.waitstrDict = {'normal': defaultWaitStr}
self.status = 'normal'

if self.directory:
self.cmd({"command": ["cd", self.directory], "timeout": 3})

# 如果用户只指定数据库用户名，如：sysasm，使用用户名直接登录直接登录
if self.dbUser == "sysasm":
rsp = self.execCommand('sqlplus / as %s' % self.dbUser, waitstr='SQL>', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % [0])
raise UniAutosException("Connect to database failed!\n%s" % [0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")

# 如果用户未指定数据库用户名或密码，使用默认sysdba直接登录
elif not self.dbPasswd or not self.dbUser:
rsp = self.execCommand('sqlplus / as %s' % "sysdba", waitstr='SQL>', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % [0])
raise UniAutosException("Connect to database failed!\n%s" % [0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")
#add by dwx461793 for longevity 20181225
elif self.dbUser == "root":
self.execCommand('mysql -u root -P 3306 -p ',waitstr='Enter password:', timeout=5)
self.execCommand(self.dbPasswd,waitstr=defaultWaitStr, timeout=5)
# 根据用户指定的用户名密码登录数据库
else:
rsp = self.execCommand('sqlplus', waitstr='Enter user-name', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

rsp = self.execCommand(self.dbUser, waitstr='Enter password:', timeout=5)
rsp = self.execCommand(self.dbPasswd, waitstr=defaultWaitStr, timeout=5)

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % rsp[0])
raise UniAutosException("Connect to database failed!\n%s" % rsp[0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")

def cmd(self, cmdSpec):
"""主机上执行SQL命令。added by wangaiguo
Args：
params (dict): cmdSpec = {
"command" : ["","",""],
"waitstr" : "",
"timeout" : 600,
"checkrc" : "",
}

params中具体键-值说明：
command (list): 待执行命令
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
timeout (int): 命令执行超时时间，默认600S，不会很精确
checkrc (int): 是否检查回显，默认值0，不检查
Returns:
result: 交互式命令的整个执行过程的输出

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {
"command": ["help"],
"timeout": 600,
}
result = self.runSQL(cmdSpec)

"""

defaultWaitstr = self.waitstrDict.get('normal', 'SQL>')
result = {"rc": None, "stderr": None, "stdout": ""}
# 2017.5.30:修改SQL命令执行的超时时间，避免SQL命令未执行完就继续后续动作，暂定2H，基本满足SLOB测试需求
# 这里只是在用户遗漏timeout参数的一个容错手段
timeout = cmdSpec.get('timeout', 5)#modified by dwx461793 for longevity 20181225
waitstr = cmdSpec.get('waitstr', defaultWaitstr)
checkrc = cmdSpec.get("checkrc", 0)

# 获取交互输入列表
cmdstr = " ".join(cmdSpec["command"])

# 用户输入命令做格式检查，如果未包含";"，补齐后下发命令
if cmdstr[-1] != ";":
cmdstr += ";"

cmdList = []
cmdList.append([cmdstr, waitstr])
if cmdSpec.get('input'):
inputLen = len(cmdSpec['input'])
for i in range(0, inputLen, 2):
wStr = cmdSpec['input'][i + 1] if (i + 1) != inputLen else defaultWaitstr
cmdList.append([cmdSpec['input'][i], wStr])
errorCmd = False
# 是否默认输入y
confirm = cmdSpec.get('confirm', False)
if confirm is True:
confirm = 'y'

recv_return = cmdSpec.get("recv_return", True)
if recv_return:
# 正常下发命令并接收回显
for cmd in cmdList:
tmpresult, isMatch, matchStr = self.execCommand(cmd[0], cmd[1] + r'|y/n|' + waitstr, timeout)

while matchStr == 'y/n' and confirm:
result["stdout"] += tmpresult
tmpresult, isMatch, matchStr = self.execCommand(confirm, cmd[1] + r'|y/n|' + waitstr,
timeout)
if tmpresult:
result["stdout"] += tmpresult

if not checkrc and isMatch and matchStr and ("SP2-" in tmpresult or "ORA-" in tmpresult):
errorCmd = True

if errorCmd:
result["stdout"] += tmpresult
result["rc"] = 1
self.logger.warn("Wrong command:\n[command:%s][error:%s]" % (cmd[0], tmpresult))
# 2017.5.31:取消命令执行失败抛异常，由用户自行判断命令执行是否异常。避免工具脚本使用异常。
# raise CommandException("Wrong command:\n[command:%s][error:%s]" % (cmd[0], tmpresult))

else:
# 只发命令，不接收回显
for cmd in cmdList:
self.send(cmd[0], timeout)
result["stdout"] = ""

return result
=====================================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 用于字符的编解码，如包含中文字符的输出等.

"""
import pprint
import json
import collections
import datetime
import re
from UniAutos import Log
from UniAutos.Util.Threads import Threads
from UniAutos.Util.Time import sleep
from UniAutos.TestEngine.ParameterType.IpAddress import IpAddress
from UniAutos.Exception.UniAutosException import UniAutosException

logger = Log.getLogger("Codec")


def wwnConvert(wwn):
"""转换不带:的wwn为带:的wwn"""
wwnList = []

length = len(wwn)
for n in range(length):
if n % 2 == 0:
wwnList.append(wwn[n:n + 2])
return ':'.join(wwnList)


def getCnFormatString(value):
"""打印包含中文的字典或列表

python 2.x中包含中文的字典输出到控制台时会输出为乱码.

Args:
value (dict|list): 包含中文的字典或列表.

"""
return json.dumps(value, encoding="utf-8", ensure_ascii=False)


def getFormatString(value):
"""安装格式打印字典或列表，中文无法打印

Args:
value (dict|list): 字典或列表.

"""
return pprint.pformat(value)


def convertBooleanToYesorNo(value):
"""转换Boolean Value为Yes或者No

Args:
value (bool): 需要被转换的值

Returns:
if value is True, return 'yes'.
if value is False, return 'no'.

"""
if value is True:
return 'yes'
elif value is False:
return 'no'
else:
raise UniAutosException("Cannot convert the value %s to Yes or No" % value)


def convertToUtf8(data):
"""转换包含unicode的字符串、字典、list为UTF-8编码格式

Args:
data (str|list|dict): 包含unicode的字符串、字典、list数据.

Returns:
data (str|list|dict): 转码为utf-8的字符串、字典、list数据.

Examples:
data = {'name': 'lun_name', 'value': u'\u4e2d\u6587'}
data = convertToUtf8(data)
>>
{'name': 'lun_name', 'value': '\xe4\xb8\xad\xe6\x96\x87'}
"""
if isinstance(data, basestring):
return data.encode('utf-8')

elif isinstance(data, collections.Mapping):
return dict(map(convertToUtf8, data.iteritems()))

elif isinstance(data, collections.Iterable):
return type(data)(map(convertToUtf8, data))

else:
return data


def trim(msg, trimMode=0):
"""
Remove all the blank space from string or unicode message,
Then return the new string

Args:
msg (object): message need remove the blank space.
trimMode (int) : remove mode， ranging from:
0 : remove all blank space.
1 : remove head blank space.
2 : remove tail blank space, if tail have \r\n, \n, this also be removed.
3 : remove head and tail blank space, if tail have \r\n, \n, this also be removed.

"""
if type(msg) in (str, unicode):
if trimMode == 0:
msg = str(msg)
msg = msg.replace(" ", "")
if trimMode == 1:
msg = re.sub(r'^\s+', "", msg)
if trimMode == 2:
msg = re.sub(r'\s+$', "", msg)
if trimMode == 3:
msg = re.sub(r'^\s+|\s+$', "", msg)
return msg


def split(msg):
"""将msg字符串的内容通过"\r\n", "\n", "\r"分段成一个list

Args：
msg (str): 待处理的字符串

Returns:
返回处理后的list

Examples:
result = self.split(msg)

"""
if not msg:
return []
return re.split("\x0d?\x0a|\x0d", msg)


def getCurrentDate():
"""
Get the current day with format

Returns:
timeStamp (str): the string for current date. 格式为: %Y-%m.
Examples:
timeStamp = self.getCurrentDate()

"""
return datetime.datetime.now().strftime("%Y-%m-%d")


def getCurrentTimeStr():
"""
Get the current time stamp with format

Returns:
timeStamp (str): the string for current time stamp. 格式为: %Y-%m-%d_%H:%M:%S.

Examples:
timeStamp = self.getCurrentTimeStr()

"""
return datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


def isIpAddress(ipAddress):
"""
Verify whether the ip address valid or not.

Args:
ipAddress Type(str): Ipv4 address

Returns:
Type(Boolean): If valid, return true; Else return false

Changes:
2015/10/22 y00305138 Created

"""
typeAndValidation = {"type": "ip_address"}
ipObject = IpAddress(typeAndValidation)

return ipObject.getValidInput(ipAddress)


def isIpv4Address(ip):
"""判断输入的ip是否为ipv4格式.

Args:
ip (str): 需要校验的ipv4地址字符串.

Returns:
True (bool): 是ipv4.
False(bool): 不是ipv4.

Examples:
IpAddress.__isIpv4Address("10.20.10.30")

"""
# ipv4正则表达式, 从0.0.0.0到255.255.255.255
ipv4Regex = r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|' \
r'2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|' \
r'[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

return re.match(ipv4Regex, ip) is not None


def isIpv6Address(ip):
"""判断输入的ip是否为ipv6格式.

Args:
ip (str): 需要校验的ipv6地址字符串.

Returns:
True (bool): 是ipv6.
False (bool)：不是ipv6.

Examples:
IpAddress.__isIpv6Address("2001:0DB8:02de::0e13")

"""
# 通常输入的格式，如：2001:0DB8:0000:0000:0000:0000:1428:0000
ipv6RegexNormal = r'^(((?=.*(::))(?!.*\3.+\3))\3?|[\dA-F]{1,4}:)([\dA-F]{1,4}(\3|:\b)' \
r'|\2){5}(([\dA-F]{1,4}(\3|:\b|$)|\2){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})\Z'

# 按组压缩格式，如：1763:0:0:0:0:b03:1:af18
ipv6RegexStandard = r'^(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}$'

# "." ，":"混合格式 ，如：1763:0:0:0:0:b03:127.32.67.15
ipv6RegexMixed = r'^(?:[a-fA-F0-9]{1,4}:){6}(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.)' \
r'{3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$'

# 最大化压缩格式，如：1762::B03:1:AF18
ipv6RegexCompressed = r'(?x)\A(?:(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}' \
r'|(?=(?:[a-fA-F0-9]{0,4}:){0,7}[a-fA-F0-9]{0,4}\Z)' \
r'(([0-9a-fA-F]{1,4}:){1,7}|:)((:[0-9a-fA-F]{1,4}){1,7}|:)' \
r'|(?:[a-fA-F0-9]{1,4}:){7}:|:(:[a-fA-F0-9]{1,4]){7})\Z'

return re.match(ipv6RegexNormal, ip) is not None \
or re.match(ipv6RegexStandard, ip) is not None \
or re.match(ipv6RegexCompressed, ip) is not None \
or re.match(ipv6RegexMixed, ip) is not None


def parallelExecute(functionName, instances, kwargs, timeOut=None):
"""Parallel execute the special function with parameters provided

Args:
functionName Type(function): The function will be call
instances Type(classobj): The class object list, which will call the function
kwargs Type(dict): Parameter key value list
timeOut Type(int): [Optional] Waiting seconds till thread killed. Used for thread.join().
By default: None

Changes:
2015/12/18 y00305138 Created

"""

i = 0
threads = []
errors = []

for inst in instances:
th = Threads(getattr(inst, str(functionName)), threadName="Thread: %d" % i, **kwargs)

threads.append(th)
i += 1

for th in threads:
th.start()

for th in threads:
if th.is_alive():
if timeOut is not None:
th.join(timeOut)
else:
th.join()
if th.errorMsg:
errors.append(th.errorMsg)

if len(errors) > 0:
raise UniAutosException("Failed to parallel execute all function, \n %s" % errors)


def jsonLoadByFile(fp):
return _unicodeToString(
json.load(fp, object_hook=_unicodeToString),
ignoreDicts=True
)


def jsonLoadByText(jsonText):
return _unicodeToString(
json.loads(jsonText, object_hook=_unicodeToString),
ignoreDicts=True
)


def _unicodeToString(data, ignoreDicts=False):
# if this is a unicode string, return its string representation
if isinstance(data, unicode):
return data.encode('utf-8')
# if this is a list of values, return list of byteified values
if isinstance(data, list):
return [_unicodeToString(item, ignoreDicts=True) for item in data]
# if this is a dictionary, return dictionary of byteified keys and values
# but only if we haven't already byteified it
if isinstance(data, dict) and not ignoreDicts:
return {
_unicodeToString(key, ignoreDicts=True): _unicodeToString(value, ignoreDicts=True)
for key, value in data.iteritems()
}
# if it's anything else, return it in its original form
return data
=====================================================================================================
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：提供所有通信的共有函数
"""

from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos import Log
import sys
import re
from UniAutos.Exception.UnImplementedException import UnImplementedException


class CommandBase(object):
"""所有通信类的基类

Args:
ip (str): ip地址
username (str): 用户名
passwd (str): 密码
port (int): 端口号

Attributes:
None

Returns:
None

Raises:
None

Examples:
None

"""

logger = Log.getLogger(__name__)

def __init__(self, ip, username, passwd, port):
super(CommandBase, self).__init__()
self.ip = ip
self.username = username
self.passwd = passwd
self.port = port
pass

def cmd(self, cmdSpec):
"""声明通用方法接口，给用户下发单独的命令

Args:
cmdSpec (dict): cmdSpec = {
"command": ["", "", ""],
"input": ["", "", "", ""],
"waitstr": "",
"directory": "",
"timeout": 600,
"username": "",
"passwd": ""
}
cmdSpec中具体键-值说明：
command (list): 具体要执行的命令，如show lun general封装成["show",
"lun", "general"]
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号
-元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参
-数执行后的期望结束符，第3号元素是2号参数的期望结束符
waitstr (str): 命令执行后的期望结束符，默认值"[>#]"
directory (str): 指定命令执行的目录
timeout (int): 命令执行超时时间，默认600S，不会很精确
username (str): 建立SSH连接时需要使用的用户名，当命令中出现username或者
passwd时会自动重新连接
passwd (str): 建立SSH连接时需要使用的密码，当命令中出现username或者
passwd时会自动重新连接

Returns:
None

Raises:
None

Examples:
None

"""
raise UnImplementedException("CommandBase's cmd method is unimplemented.")
pass

def connect(self):
"""声明通用方法接口，连接设备

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
raise UnImplementedException("CommandBase's connect method is unimplemented.")
pass

def disConnect(self):
"""声明通用方法接口，断开与设备的连接

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
raise UnImplementedException("CommandBase's disConnect method is unimplemented.")
pass


def discover(protocol=None, ip=None, username=None, password=None, newpassword=None,
ssh_public_key=None, ssh_private_key=None, port=None, max_session=1,
debug_username=None, debug_password=None, controlmsg=None, backwardip=None, waitstr=None,
docker_ip=None, docker_user=None, docker_password=None, docker_port=None, heartbeatIp=None,
vrf_inner_flag=None):
"""工厂方法，提供所有通信实例的统一初始化

Args:
protocol (str|None): 说明需要初始化的通信类型，取值范围["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
ip (str|None): 通信需要连接的ip地址，Local时不需要
username (str|None): 建立连接使用的用户名，Local时不需要
password (str|None): 建立连接使用的密码，Local时不需要
newpassword (str|None): 新密码(可能登录时需要输入新密码)
ssh_public_key (str|None): 公钥路径
ssh_private_key (str|None): 私钥路径
port (str|None): 端口
max_session (int|str) : 最大连接数
debug_username (str|None): debug模式的用户名
debug_password (str|None): debug模式的密码
controlmsg (str|None): 控制器信息(针对SVP设备)


Returns:
None

Raises:
Command子类的实例，根据type的值不同，返回不同对象

Examples:
from UniAutos.Command import Command
local = Command.discover("local")
result = local.cmd(["dir"])

"""
if protocol:
protocol = protocol.lower()
if ip is None or username is None:
raise InvalidParamException
args = [ip, username, password]
if port:
port = int(port)
args.append(port)
if waitstr:
args.append(waitstr)
if protocol in ['storssh', 'svpstorssh', 'standssh', 'nasssh', 'fusionssh', 'dswaressh', 'emustorssh',
'demostorssh', 'svpipmissh', 'rocssh', 'heartbeatssh', 'dockerssh', 'ipenclosuressh',
'ipenclosureheartbeatssh']:
from ConnectionPool import ConnectionPool
from HeartbeatConnectionPool import HeartbeatConnectionPool
from IPenclosureConnectionPool import IPenclosureConnectionPool
if not port:
port = 22
kwargs = dict()
kwargs['ip'] = ip
kwargs['username'] = username
kwargs['password'] = password
kwargs['key'] = ssh_private_key
kwargs['port'] = port
kwargs['maxSession'] = int(max_session)
if protocol == 'standssh':
return ConnectionPool.createStandSSHPool(**kwargs)

if protocol == 'rocssh':
kwargs['osConnectInfo'] = {
'dockerIp': docker_ip,
'dockerUser': docker_user,
'dockerPassword': docker_password,
'dockerPort': docker_port
}
return ConnectionPool.createRocSSHPool(**kwargs)

if protocol == 'svpipmissh':
return ConnectionPool.createSvpIpmiPool(**kwargs)

if protocol == 'nasssh':
kwargs['backwardip'] = backwardip
return ConnectionPool.createNasSSHPool(**kwargs)
if protocol == 'fusionssh':
kwargs['backwardip'] = backwardip
return ConnectionPool.createFusionSSHPool(**kwargs)
if protocol == 'dswaressh':
kwargs['backwardip'] = backwardip
return ConnectionPool.createDSwareSSHPool(**kwargs)
if protocol == 'dockerssh':
return ConnectionPool.createDockerSSHPool(**kwargs)
if protocol == 'ipenclosuressh':
return IPenclosureConnectionPool.createIPenclosureConnectionPool(**kwargs)
osConnectInfo = dict()
osConnectInfo['ip'] = ip
osConnectInfo['username'] = debug_username if debug_username else 'ibc_os_hs'
osConnectInfo['password'] = debug_password if debug_password else 'Storage@21st'
osConnectInfo['port'] = port
kwargs['osConnectInfo'] = osConnectInfo
if protocol == 'storssh':
kwargs['newpassword'] = newpassword
return ConnectionPool.createStorSSHPool(**kwargs)
if protocol == 'ipenclosureheartbeatssh':
kwargs['newpassword'] = newpassword
kwargs['heartbeatIp'] = heartbeatIp
kwargs['vrf_inner_flag'] = vrf_inner_flag
return ConnectionPool.createIpEnclosureHearBeatPool(**kwargs)
if protocol == 'emustorssh':
return ConnectionPool(ip=ip, username=username, password=password, protocol='emustorssh')
if protocol == 'demostorssh':
return ConnectionPool(ip=ip, username=username, password=password, protocol='demostorssh')
if protocol == 'heartbeatssh':
# 心跳控制器使用管理控制器的osConnectInfo登录
kwargs['protocol'] = 'heartbeatssh'
kwargs['heartbeatIp'] = heartbeatIp
kwargs['vrf_inner_flag'] = vrf_inner_flag
return HeartbeatConnectionPool(**kwargs)
kwargs['controlmsg'] = controlmsg
if protocol == 'svpstorssh':
return ConnectionPool.createSVPStorSSHPool(**kwargs)
elif protocol == 'local':
from UniAutos.Command.Advanced.Local import Local
return Local()
elif protocol == 'telnet':
from UniAutos.Command.Connection.TelnetConnection import TelnetConnection
if len(args) > 3 and not isinstance(args[-1], str):
args.insert(3, '>')
conn = TelnetConnection(*args)
conn.login()
return conn
elif protocol == 'xmlrpc':
from UniAutos.Command.Advanced.Rpc import Rpc
return Rpc(*args)
elif protocol == "emcstor":
from Connection.EMCConnection import EMCConnection
return EMCConnection(*args)
else:
for cmdClass in ["UniAutos.Command.Advanced.Rpc.Rpc",
"UniAutos.Command.StandSSH.StandSSH",
"UniAutos.Command.StorSSH.StorSSH",
"UniAutos.Command.Telnet.Telnet",
"UniAutos.Command.Advanced.Local.Local"]:
moduleName = cmdClass[0: cmdClass.rfind(".")]
className = cmdClass[cmdClass.rfind(".") + 1: len(cmdClass)]
try:
__import__(moduleName)
if className == "Local":
cmdObj = getattr(sys.modules[moduleName], className)()
else:
if ip is None or username is None or password is None:
raise InvalidParamException
else:
cmdObj = getattr(sys.modules[moduleName], className)(ip, username, password)
if className == "StorSSH":
cmdSpec = {"command": ["show", "system", "general"]}
else:
cmdSpec = {"command": ["ping"]}
cmdObj.cmd(cmdSpec)
return cmdObj
except Exception:
CommandBase.logger.error("To communicate with " + className + " Failed")
return None
=======================================================================================================
#!/usr/bin/env python
# -*- coding: utf8 -*
"""
功 能: Time, 时间相关的操作, 如延时等..

版权信息: 华为技术有限公司，版本所有(C) 2014-2015

"""

import threading
from UniAutos import Log
from UniAutos.Util.Threads import Threads
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.UniAutosException import UniAutosException
from time import time
logger = Log.getLogger('Time')


def _sleep(seconds):
"""线程睡眠操作接口

本接口用于替代线程自带的sleep函数， 系统自带sleep函数使用后, 无法调用kill函数杀死线程.

Args:
seconds (float): 睡眠时间, S为单位.

Examples:
from UniAutos.Util.Time import sleep
sleep(10)

"""
# 使用Event的timeout机制模拟睡眠.
if isinstance(seconds, int) or isinstance(seconds, float):

sleepTimer = threading.Event()
sleepTimer.wait(timeout=seconds)
sleepTimer = None
else:
raise InvalidParamException("timout value [%s], type is %s, type must be int or float."
% (seconds, type(seconds)))


def sleep(seconds, segment=60):
"""分段式的睡眠，用于监控睡眠过程，避免长时间睡眠过程中无打印，无法判断操作是否正常存活.
Args:
seconds (float): 总的睡眠时间.
segment (int): 分段的时间，即睡眠多长时间打印一次日志.
Notes:
如果总睡眠时间与分段的时间相除不为整数，需要向上取整.
"""
# if total sleep time 0:
logger.debug("(%s/%s)当前总共需要睡眠%sS, 开始睡眠%sS, 总共还需等待%sS."
% (count + 1, int(totalCount), seconds, lastTime, ((ceilCount - count) * segment + lastTime)))
_sleep(lastTime)


class Timeout(Exception):
"""function run timeout"""
pass


def timeout(seconds):
"""超时装饰器，指定超时时间
若被装饰的方法在指定的时间内未返回，则抛出Timeout异常"""

def timeout_decorator(func):
"""超时装饰器"""

def _new_func(oldFunc, result, oldFuncArgs, oldFuncKwargs):
result.append(oldFunc(*oldFuncArgs, **oldFuncKwargs))

def _(*args, **kwargs):
result = []
newKwargs = { # create new args for _new_func, because we want to get the func return val to result list
'oldFunc': func,
'result': result,
'oldFuncArgs': args,
'oldFuncKwargs': kwargs
}
thd = Threads(_new_func, 'timeout', **newKwargs)
thd.start()
thd.join(seconds)

if thd.errorMsg != '':
raise UniAutosException(thd.errorMsg)
if thd.isAlive():
thd.kill() # kill the child thread

if len(result) _timeout:
if raiseException:
raise ValueError('####TIMEOUT####%s timeout %sS' % (logMesg, _timeout))
else:
logger.info('####TIMEOUT####%s is finish' % logMesg)
return result
else:
cur_times = 0
logger.info('####TIMEOUT####[%sS/%sS][%s]%s is not up to expectations, wait %sS and run later'
% (timeSlot, _timeout, func.__name__, logMesg, _interval))
sleep(_interval)

return _wrapper

return decorated
==========================================================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 故障类

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2015/4/17 严旭光 y00292329 created

"""
import random
import re
import datetime
import traceback
import threading
from UniAutos.Util.Units import Units
from UniAutos import Log
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Util.Time import sleep


class Fault(object):
""" 定义设备故障

Args:
device (DeviceBase): 故障运行的设备
name (str): 故障名称
closureCodeRef (method): 故障执行代码
obj (object): 对象
parameters (dict): 故障执行代码所需要的参数
cleanupClosure (method): 故障执行完后恢复的代码

Examples:

Changes:
2015-4-17 严旭光 y00292329 Created

"""

def __init__(self, device, name, closureCodeRef, obj=None, parameters=None, cleanupClosure=None):
self.device = device
self.name = name
self.closureCodeRef = closureCodeRef
self.obj = obj
if parameters is None:
parameters ={}
self.parameters = parameters
self.cleanupClosure = cleanupClosure
self.__tiggerCount = 0
self.logger = Log.getLogger(self.__module__)
self.injectTime = None
try:
if "6.0." in self.device.controllers[0].host.softVersion:
self.injectTime = self.device.getCurrentTimeByDebug().split(' ')[0]
else:
self.injectTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("Get device current time fail, because system is not normal.")
self.recoverTime = None
self.faultType = self.device.getDeviceFault()

def inject(self, background=False, count=None, duration=None,
isRandom=False, randomInterval=None, fixedInterval='5M', registerCleanup=True):
"""

Args:
background (boolean): 是否后台运行，如果是就会另起线程执行故障注入代码
count (int): 执行次数，可选参数
duration (str): 执行时长，可选参数
isRandom (boolean): 执行间隔时间是随机的
randomInterval (dict): 执行间隔随机的范围，默认5分钟-60分钟{'lowerLimit':'20S', 'upperLimit':'40S'}
fixedInterval (str): 固定间隔时间，默认5分钟
registerCleanup (boolean): 是否注册

Returns:
None

Raises:
None

Examples:
1、后台注入故障代码20次
fault.inject(background=True,count=20)
2、后台注入故障5分钟，每次间隔1分钟
fault.inject(background=True,duration='5M',fixedInterval='1M')
3、注入故障5分钟，随机间隔，最小间隔1分钟，最大间隔2分钟
randomInterval = {'lowerLimit':'1M', 'upperLimit':'2M'}
fault.inject(duration='5M',isRandom=True,randomInterval=randomInterval)

Changes:
2015-04-17 y00292329 Created

"""
if randomInterval is None:
randomInterval = {}
kwargs = dict(count=count, duration=duration, isRandom=isRandom, randomInterval=randomInterval,
fixedInterval=fixedInterval)
if registerCleanup:
self.device.registerFault(self)
try:
if "6.0." in self.device.controllers[0].host.softVersion:
self.injectTime = self.device.getCurrentTimeByDebug().split(' ')[0]
else:
self.injectTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("Get device current time fail, because system is not normal.")
self.recoverTime = None
self.faultType.addFault(self)
# 临时加打印，定位注册Fault但未恢复的情况
self.logger.info('Register fault 【%s】 on device successfully' % self.name)
if background:
threading.Thread(target=self.__runFault, name=self.name, kwargs=kwargs)
else:
self.__runFault(**kwargs)

def __runFault(self, count=None, duration=None,
isRandom=False, randomInterval=None, fixedInterval='5M'):
"""执行故障命令

Args:
count (int): 执行次数，可选参数
duration (str): 执行时长，可选参数
isRandom (boolean): 执行间隔时间是随机的
randomInterval (dict): 执行间隔随机的范围，默认5分钟-60分钟
fixedInterval (str): 固定间隔时间，默认5分钟

Returns:
None

Raises:
InvalidParamException: 执行时长和执行次数其中一个必须被设置
InvalidParamException: 随机间隔时间有误，最小时间必须小于最大时间.

Examples:

Changes:
2015-04-17 y00292329 Created

"""
if randomInterval is None:
randomInterval = {}
if (not duration) and (not count):
raise InvalidParamException('duration or count must be set for this fault')
if duration:
matchObj = re.match(r'\d+$', duration)
if matchObj:
duration += 'S'
duration = int(Units.getNumber(Units.convert(duration, 'S')))
if isRandom:
if not randomInterval:
randomInterval['lowerLimit'] = '5M'
randomInterval['upperLimit'] = '60M'
lowerLimit, upperLimit = self.__getRandomIntervalSeconds(randomInterval)
else:
matchObj = re.match(r'\d+$', fixedInterval)
if matchObj:
fixedInterval += 'S'
fixedInterval = Units.getNumber(Units.convert(fixedInterval, 'S'))
stop = False
starttime = datetime.datetime.now()
while not stop:
self.closureCodeRef(self.parameters)
self.__tiggerCount += 1
self.logger.debug('Fault %s has been triggered %d times' % (self.name, self.__tiggerCount))
if isRandom:
sleepTime = random.randint(lowerLimit, upperLimit)
else:
sleepTime = fixedInterval
if count and self.tiggerCount >= count:
break
if duration:
current = datetime.datetime.now()
if (current - starttime).seconds >= duration:
break
if (current - starttime).seconds + sleepTime > duration:
sleepTime = duration - (current - starttime).seconds
sleep(sleepTime)

def __getRandomIntervalSeconds(self, randomInterval):
"""获取随机间隔时间的秒数

Args:
randomInterval (dict): 随机间隔的最小时间和最大时间

Returns:
lowerLimit: 最小间隔
upperLimit: 最大间隔

Raises:
InvalidParamException: 最小间隔时间大于最大间隔时间

Examples:


Changes:
2015-05-14 y00292329 Created

"""

matchObj = re.match(r'\d+$', randomInterval['lowerLimit'])
if matchObj:
randomInterval['lowerLimit'] += 'S'
lowerLimit = Units.getNumber(Units.convert(randomInterval['lowerLimit'], 'S'))
matchObj = re.match(r'\d+$', randomInterval['upperLimit'])
if matchObj:
randomInterval['upperLimit'] += 'S'
upperLimit = Units.getNumber(Units.convert(randomInterval['upperLimit'], 'S'))
if lowerLimit >= upperLimit:
raise InvalidParamException("The randomInterval values for upper and lower limits are incorrect."
"Lower limit must be less than the Upper Limit")
return lowerLimit, upperLimit

def recover(self):
"""恢复故障

Args:
None

Returns:
None

Raises:
None

Examples:
1、恢复故障
fault.recover()

Changes:
2015-04-17 y00292329 Created

"""
if self.getStatus() == 'running':
self.stop()
if self.cleanupClosure:
if self.recoverTime is None:
self.cleanupClosure(self.parameters)
try:
self.recoverTime = self.device.getCurrentTime().split(' ')[0]
except Exception:
self.logger.info("The Fault may be power down device, can not connect to device, detailt:"
"%s" % traceback.format_exc())
else:
self.logger.info('The Fault %s is already recovery at %s' % (self.name, self.recoverTime))
else:
self.logger.warn('There was no cleanup closure registered to the Fault %s' % self.name)
# 通过recoverTime来判断是否恢复
# self.device.unregisterFault(self)

def stop(self):
"""停止故障运行

Args:
None

Returns:
None

Raises:
None

Examples:

Changes:
2015-04-17 y00292329 Created

"""
pass

def getStatus(self):
"""获取故障运行的状态

Args:
None

Returns:
str: stopped/running

Raises:
None

Examples:

Changes:
2015-04-17 y00292329 Created

"""
return 'stopped'

@property
def tiggerCount(self):
"""故障执行的次数

Args:
None

Returns:
int: 故障执行次数

Raises:
None

Examples:
None

Changes:
2015-04-17 y00292329 Created

"""
return self.__tiggerCount

def getObject(self):
return self.obj
=============================================================================================
#!/usr/bin/env python
# -*- coding: utf8 -*

"""
功 能：当前模块为UniAutos.Wrapper所定义的一个place holder，不同于UniAuto.Wrapper对象直接实例化注册到主机，
WrapperHolder是在第一次被用的时候才会被注册

版权信息：华为技术有限公司，版本所有(C) 2014-2015

"""


class WrapperHolder(object):
""" 定义WrapperHolder类，用于保存UniAutos.wrapper类，
-直到wrapper对象的方法被调用才会实例化wrapper对象
"""

def __init__(self, requireCodRef, wrapperType, deviceObj ):
"""WrapperHolder构造函数，创建一个WrapperHolder对象

Args:
requireCodRef (func) : 创建Wrapper对象的回调函数
wrapperType (str) : wrapper类型
deviceObj (UniAutos.Device.HostBase) : 注册wrapper的主机对象

Attributes:
requireCodRef(func) - 创建Wrapper对象的回调函数
wrapperType(Str) - wrapper类型
deviceObj(HostObj) - 注册wrapper的主机对象
realWrapper(WrapperObj) - 实例化的wrapper对象

Returns:
wrapperHolder对象

Raises:
None

Examples:
def adminCliReq():
from UniAutos.Wrapper.Tool.AdminCli import AdminCli
return AdminCli()
hostObj.registerToolWrapper(hostObj, wrapper_type='UniAutos.Wrapper.Tool.AdminCli', require=adminCliReq)

"""
self.requireCodRef = requireCodRef
self.wrapperType = wrapperType
self.deviceObj = deviceObj
self.realWrapper = None

def __getattr__(self, item):
"""重写Object积累的__getattr__方法以保证对象初始化时自动化调用replaceWithRealWrapper方法

Input:
None

Returns:
None

Raises:
None

"""
replacedWapperObj = self.replaceWithRealWrapper()
return getattr(replacedWapperObj, item)

def replaceWithRealWrapper(self):
"""WrapperHolder构造函数，创建一个WrapperHolder对象

Input:
None

Returns:
None

Raises:
None

"""
if not self.realWrapper:
wrapperObj = self.requireCodRef()
wrappers = self.deviceObj.getWrapper()
flag = False
for wrapperDict in wrappers:
if 'wrapper_type' in wrapperDict and wrapperDict['wrapper_type'] == self.wrapperType:
wrapperDict['wrapper'] = wrapperObj
wrapperDict['require'] = 1
flag = True
break
if not flag:
raise Exception('Could not automatically invoke the wrapper class:%s' % self.wrapperType)
wrapperObj.setDevice(self.deviceObj)
self.realWrapper = wrapperObj
return wrapperObj
else:
return self.realWrapper
=============================================================================================
#!/usr/bin/python
# coding=utf-8

"""

Function: UniWebBase the base class for all web application interface.

Copyright @ Huawei Technologies Co., Ltd. 2014-2024
"""

from UniAutos.Wrapper.Tool.ToolBase import ToolBase
from UniAutos.Wrapper.Tool.Selenium.UniWebs.Common.BrowserType import BrowserType

class UniWebBase(ToolBase):
"""
Desc: UniWebBase the base class for all web application interface.

Import all the operations from ISM. We have added following operations in below:
UniAutos.Wrapper.Tool.Selenium.DeviceManager.Function.DiskDomain

"""

def __init__(self, ipAddress, port, userName, password, browserType=BrowserType.FIREFOX):
"""
Constructor: The base class for all web application factory.

Args:
ipAddress Type(str) : device ip address
port Type(str) : device connection port from web browser
userName Type(str) : user name for device
password Type(str) : password for device
browserType Type(BrowserType): web browser type

Return:
Type(UniWebBase)

Rises:
None

"""
super(UniWebBase, self).__init__()
=========================================================================================================
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能: wrapper中tool部分的基类
"""

from UniAutos.Wrapper.WrapperBase import WrapperBase
from UniAutos.Util.TypeCheck import validateParam
from UniAutos import Log
import re

class ToolBase(WrapperBase):
"""wrapper的tool基类

Args:
params (dict): 此处仅关注key: retry

Attributes:
logger (obj): 一个日志对象，用于记录日志
retry (dict): 命令执行失败后是否重试的重试信息
method_release_requirement (list): 释放时需要执行的方法列表
user_retry_codes (list): 用户自定义的需要重试的字符串列表

Returns:
None

Raises:
None

Examples:
None

"""
def __init__(self, params=None):
super(ToolBase, self).__init__(params)
self.logger = Log.getLogger(__name__)
def tmpmethod(param):
return 0
self.retry = {"criteria": tmpmethod, "count": 0, "interval": '10 S'}
if params and "retry" in params:
self.retry = params["retry"]
self.retry["user_criteria"] = tmpmethod
self.methodReleaseRequirement = []
self.userRetryCodes = []


def setRetry(self, userRetryCodes=[]):
"""设置用于检测是否需要重试的检测字符串

Args:
userRetryCodes (list): 检测字符串列表

Returns:
None

Raises:
None

Examples:
None

"""
if userRetryCodes:
self.userRetryCodes = userRetryCodes

def userCriteria(info):
"""通过回显信息info，检测执行是否成功，并能通过用户指定的检测字符串的检测

Args:
info (dict): {"rc": "", "stderr": "", "stdout": ""}

Returns:
0/1: 执行成功返回0，失败返回1

Raises:
None

Examples:
None

"""
retryCodes = self.userRetryCodes
result = 0
if info:
result = info.pop("rc")
if result != 0:
for key in info.keys():
output = info[key]
for line in output:
for retryError in retryCodes:
matcher = re.match(retryError, line)
if matcher:
self.logger.debug("the following error was returned:\n %s\nretrying command." %line)
return 1
return 0
return 0

if hasattr(self, "retry"):
self.retry["user_criteria"] = userCriteria
pass

def restoreRetry(self):
"""设置默认的重试方法

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
def retryCodes():
return 0
if hasattr(self, "retry") and hasattr(self.retry, "user_criteria"):
self.retry["user_criteria"] = retryCodes
pass

def deadObjectCheck(self, regexStr):
def check(info):
if "stderr" in info:
matcher = re.match(regexStr, info["stderr"])
if matcher:
return 1
if "stdout" in info:
matcher = re.match(regexStr, info["stdout"])
if matcher:
return 1
return 0

return check

def can(self, methodName):
"""检查方法methodName是否存在，存在就返回方法的引用

Args:
methodName (str): 方法的名称

Returns:
None/方法的引用: methodName对应的方法存在时返回方法的引用，不存在就返回None

"""
dev = self.getDevice()
if not dev:
if hasattr(self, methodName):
return eval("self."+methodName)

if methodName not in self.methodReleaseRequirement:
if hasattr(self, methodName):
return eval("self."+methodName)

if hasattr(self, methodName):
return eval("self."+methodName)
==============================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 执行CLI命令下发相关操作

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/3 严旭光 y00292329 created

"""
import re
import copy
import importlib
import pprint
from TemplateCLIObj import CLIObj
from UniAutos.Exception.CommandException import CommandException
from Dryrun import Dryrun
from UniAutos import Log



class CliWrapper(CLIObj):
logger = Log.getLogger(__name__)
defaultVersion = "V300R003C00"
dryrun = Dryrun()

def __init__(self, productModel=None, version=None, patchVersion=None):
"""OceanStor CLI wrapper object

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str) : 补丁版本号

Changes:
2016-06-06 y00292329 Created

"""
super(CliWrapper, self).__init__(productModel, version, patchVersion)


def runWrapper(self, methodName, params, interactRule=None, option=None):
"""执行wrapper命令

Args:
methodName (str): 方法名
params (dict): 方法参数
interactRule (dict): 交互输入规则
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""
isTimeout = True
if option is None:
option = dict()
elif 'time_out' in option:
isTimeout = False
if interactRule is None:
interactRule = dict()
cmdTemplate, retTemplate = self.getTemplate(methodName)

comperList = [i for i in params.keys() if i not in cmdTemplate["params"].keys()]
if len(comperList) > 0:
self.logger.info("find some param not in cmdTemplate's params %s !" % comperList)

if cmdTemplate:
cmdTemplate = copy.deepcopy(cmdTemplate)
self.logger.debug("[WrapperName] %s [params] %s" % (methodName, params))
option = {k.lower():v for k, v in option.items() if True}
option = dict(self.conf, **option)
option = dict(cmdTemplate.get("opt", {}), **option)
self.adaptParams(methodName, params, option)
cmdSpace = self.generator.generator(cmdTemplate, params, interactRule, option)

# add view method to option, used to ignore some return code.
option['sessionType'] = cmdSpace['sessionType']
option['method'] = methodName

# 如果是非用户传入并且没有修改timeout
if 'timeout' in cmdSpace and isTimeout and self.device.getTimeout:
del cmdSpace['timeout']

if not option.get("debug", False):
if self.device:
result = self.device.run(cmdSpace)
stdout = result.get("stdout", None)
if stdout:
result["stdout"] = re.split("\x0d?\x0a|\x0d", stdout)
validateResult = self.validate(result, option)
if validateResult:
result = self.paserResult(retTemplate, result, option)
else:
msg = 'Failed to execute the command ' + methodName
msg = msg + "\nResult of the wrapper call:\n" + pprint.pformat(result)
raise CommandException(msg, result)
else:
response = self.dryrun.dryrun(methodName, cmdTemplate, params)
result = dict()
if response is None:
result = self.device.run(cmdSpace)
self.dryrun.insertData(methodName,cmdTemplate,params,result["stdout"])
else:
result["stdout"] = response
result["rc"] = None
result["stderr"] = None
validateResult = self.validate(result, option)
if validateResult:
result = self.paserResult(retTemplate, result, option)
else:
result["parser"] = {}

return result
else:
raise Exception("not find cli cmd")

def choseCMDTemplate(self, productModel, version, patchVersion):
"""选择命令模板module

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Returns:
cmdTemplate (Module): 命令行模板模块

Exceptions:
None

Changes:
2016-06-06 c00305140 Created

"""
cmdTemplate = None
if re.search('Dorado', productModel, re.I) or re.search('D', productModel):
if re.search('V300R001C20', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C00")
self.logger.info("load Dorado cmd template")
elif re.search('V600R002C00', version, re.I):
#TODO：C30暂时加载无OMRP，继承C20的。待独立OMRP后修改
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R002C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C00")
elif re.search('V300R002C10', version, re.I) and "NAS" not in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C10")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C10")
elif re.search('V300R002C20', version, re.I) and "NAS" not in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R002C20")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R002C20")
elif re.search('V100R005C10', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C20")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C21', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C21")
self.logger.info("load Dorado cmd template")
elif re.search('V300R001C30', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV300R001C30")
self.logger.info("load Dorado cmd template: %s" % "DoradoV300R001C30")
elif re.search('6.0.', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV600R003C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV600R003C00")
elif re.search('V100R001C00', version, re.I):
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "DoradoV100R001C00")
self.logger.info("load Dorado cmd template: %s" % "DoradoV100R001C00")
elif re.search('V500R007C30|V300R002C10|V300R002C20', version, re.I) and "NAS" in productModel:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "OceanStorDoradoNAS")
self.logger.info("load Dorado cmd template: %s" % "OceanStorCOMMONDoradoNAS")
else:
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % "Dorado")
self.logger.info("load Dorado cmd template")
elif productModel=="EMC":
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.EMC.cmd.%s" % version)
else:
try:
if patchVersion:
spcVersion = version + patchVersion
if spcVersion == 'V300R003C20SPC200' or spcVersion == 'V300R003C20SPC100':
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.V300R003C20SPC200")
self.logger.info("version is %s, load V300R003C20SPC200 cmd template" % spcVersion)
if not cmdTemplate:
if 'V300R006C10' in version or 'V500R007C00' in version:
version = 'V500R007C00'
if 'V300R006C20' in version or 'V500R007C10' in version:
version = 'V500R007C10'
# 2018-08-07 wwx271515 新增V300R006C50&V500R007C30,继承V300R006C21
if 'V500R007C20' in version or 'V300R006C21' in version or 'V300R006C30' in version:
version = 'V500R007C20'
if 'V500R007C30' in version or 'V300R006C50' in version:
version = 'V500R007C30'
if ('V500R007C50' in version or 'V300R006C60' in version) and re.search("18\d{3}", productModel):
version = 'V500R007C5018000'
if ('V500R007C50' in version or 'V300R006C60' in version) and not re.search("18\d{3}", productModel):
version = 'V500R007C50'
if 'V500R008C00' in version:
version = 'V500R008C00'
if 'V500R007C60' in version:
version = 'V500R008C00'
if 'V300R001' in version:
version = 'V300R001C00'
if 'V300R002C10' in version or 'V300R002C20' in version:
version = 'V300R002C10'
if 'V300R005C00' in version:
version = 'V300R005C00'
cmdTemplate = importlib.import_module(
"UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % version)
self.logger.info("load %s cmd template" % version)
except Exception:
self.logger.warn("load %s cmd template failed" % version)
cmdTemplate = importlib.import_module("UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd.%s" % self.defaultVersion)
self.logger.warn("load default cmd template %s" % self.defaultVersion)
return cmdTemplate
=========================================================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 执行CLI命令下发相关操作

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/3 严旭光 y00292329 created

"""
import re
from UniAutos.Wrapper import conf
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import Adapter
from Generator import Generator
from UniAutos.Wrapper.Template.ProductModel.OceanStor.ret import Parser
from UniAutos.Wrapper.Template.ProductModel.OceanStor.ret import Common
from UniAutos.Wrapper.Template import Convert
from Dryrun import Dryrun
from UniAutos import Log
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import CmdMapping
from UniAutos.Exception.UnImplementedException import UnImplementedException


class CLIObj(object):
logger = Log.getLogger(__name__)
defaultVersion = "V300R003C00"
dryrun = Dryrun()

def __init__(self, productModel=None, version=None, patchVersion=None):
"""执行CLI命令下发相关操作

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Changes:
2016-06-06 y00292329 Created

"""

self.conf = {k.lower(): v for (k, v) in conf.__dict__.items() if not k.startswith("__")}
self.generator = Generator()
self.device = None
self.productModel = productModel
self.version = version
self.patchVersion = patchVersion
self.cmdTemplates = self.choseCMDTemplate(productModel, version, patchVersion)

def runWrapper(self, methodName, params, interactRule=None, option=None):
"""执行wrapper命令

Args:
methodName (str): 方法名
params (dict): 方法参数
interactRule (dict): 交互输入规则
option (dict): 控制参数

Returns:
None

Exceptions:
UnImplementedException (exception): 未实现抽象方法异常

Changes:
2016-06-06 y00292329 Created

"""
raise UnImplementedException("This is an abstracted method, please implemented via inherited class")

def adaptParams(self,methodName, params, option):
"""适配新老wrapper的adapter方法

Args:
methodName (str): 新方法名
params (dict): 方法参数
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""
adapter_cmd_params = option.get("adapter_cmd_params", True)
if adapter_cmd_params:
adapter = Adapter.__dict__.get("adapter_"+ methodName, None)
Adapter.version = self.version + self.patchVersion
Adapter.productModel = self.productModel
if adapter:
params = adapter(params)
return params

def validate(self, result, option):
"""验证回显结果

Args:
result (str): 回显结果
option (dict): 控制参数

Returns:
result (bool): 验证是否通过

Changes:
2016-06-06 y00292329 Created

"""

validata_result = option.get("validate_result", True)
ignore_codes = self.device.ignore_codes
wrapper_ignores = self.device.wrapper_ignores

def validateFunc(info):
lineRaw = info["stdout"]

# 如果当前设备设置了ignore_codes, For ##Retry Frame##
__lineForIgnore = ''.join(lineRaw)

# 首先判断wrapper_ignores中是否有指定对应的wrapper method忽略指定的关键字.
for ignore_code in wrapper_ignores.iterkeys():
if option['method'] in wrapper_ignores[ignore_code]:
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for ignore_code in ignore_codes.get(option['sessionType'], []):
# 如果ignore_code在wrapper_ignores中出现过，则以wrapper_ignores为判断依据，这里不再继续处理.
if ignore_code in wrapper_ignores.iterkeys():
continue
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for line in lineRaw:
matcher = re.search(
"\^(\n|\n\r|\r)?|Get wwn failed:sdId|Error:|Command failed|command not found|Try \'help\' for more information", line,
re.IGNORECASE)
if matcher:
return False
return True
if validata_result:
validationResult = validateFunc(result)
return validationResult
return True

def paserResult(self,retTemplate, result, option):
"""解析回显结果

Args:
retTemplate (dict): 回显模板
result (dict): 回显信息
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""

parser_result = option.get("parser_ret", True)
if parser_result:
params = retTemplate.get("params", {})
parser = retTemplate.get("parser", None)

if result.pop('ignored_error', None):
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Error But Ignored. "
"The parser will be null.")
result['parser'] = {}
return result

elif not parser:
parser = Parser.Parser()
convertDict =dict()
parser.primary = "id"
for x in params:
if isinstance(x, dict):
srcCol = x.get("srcCol", "").lower().replace(" ","_")
dstCol = x.get("dstCol", srcCol).lower().replace(" ","_")
primary = x.get("primary", None)
alter = x.get("alter", None)
if srcCol =="" and dstCol:
srcCol = dstCol
if srcCol != dstCol:
convertDict[srcCol] = {"converted_key": dstCol}
if alter:
if srcCol not in convertDict:
convertDict[srcCol] = dict()
convertDict[srcCol]["converted_value"] = getattr(Convert, alter)
if isinstance(primary, str) and primary == "true":
parser.primary = srcCol
parser.convertDict = convertDict
result['parser'] = parser.standardParser(self, result['stdout'])
else:
result['parser'] = Parser.__dict__.get(parser)(result['stdout'])
return result

def setDevice(self, device):
"""设置Wrapper所属的设备

Changes:
2016-06-06 y00292329 Created

"""

self.device = device

def getDevice(self):
"""获取设备

Changes:
2016-06-06 y00292329 Created

"""

return self.device

def setOption(self, option):
"""设置全局配置信息

Changes:
2016-06-06 y00292329 Created

"""

option = {k.lower():v for k, v in option.items() if True}
self.conf = dict(self.conf, **option)

def getTemplate(self, methodName):
"""获取命令模板

Args:
methodName (str): 方法名

Changes:
2016-06-06 y00292329 Created

"""

cmdTemplate = self.cmdTemplates.__dict__.get(methodName, None)
retTemplate = getattr(Common, methodName, {})
return cmdTemplate, retTemplate

def choseCMDTemplate(self, productModel, version, patchVersion):
"""执行wrapper命令

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Returns:
None

Exceptions:
UnImplementedException (exception): 未实现抽象方法异常

Changes:
2016-06-06 y00292329 Created

"""
raise UnImplementedException("This is an abstracted method, please implemented via inherited class")

def createPropertyInfoHash(self, componentClass, propertiesList):
if not isinstance(componentClass, str):
componentClass = componentClass.__module__ + '.' + componentClass.__name__
methodHash = CmdMapping.MethodHash.get(componentClass, None)
if methodHash is None:
return {}
temp = {}
for prop in propertiesList:
temp[prop] = {"getmethod":methodHash.get("show"),
"setmethod":methodHash.get("update", "")}
return temp

def getCommonPropertyInfo(self, getMethod, properties=None):
objs = []
for k,v in CmdMapping.MethodHash.items():
if getMethod == v.get("show", ""):
objs.append(k)
return objs
return objs

def hasMethod(self, methodName):
if self.cmdTemplates:
if self.cmdTemplates.__dict__.get(methodName, None):
return True
return False
===================================================================================================
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/17 严旭光 y00292329 created

"""
try:
import pymongo
UniAutosDB = pymongo.MongoClient(host="10.183.100.106").UniAutos
except:
pass


class Dryrun(object):
def __init__(self):
pass

def dryrun(self, methodName, cmdTemplate, params, option=None):
view = cmdTemplate.get("view", ["admincli"])[0]
for item in UniAutosDB[view].find({"cmd": methodName}):
flag = True
for key in params.keys():
if key in item["params"]:
continue
flag = False
break
if flag:
return item["response"]
return None

def insertData(self, methodName, cmdTemplate, params,response):
view = cmdTemplate.get("view", ["admincli"])[0]
UniAutosDB[view].insert({"cmd": methodName, "params": params.keys(), "response": response})
========================================================================================================