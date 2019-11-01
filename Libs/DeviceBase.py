DeviceBase ::

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Device基类

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2015/4/17 严旭光 y00292329 created

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

