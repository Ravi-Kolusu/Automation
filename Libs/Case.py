#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: Case为RatsCase测试用例基类，用于区分Configuration

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

"""


from UniAutos.Util.Time import sleep
from UniAutos.TestEngine.Base import Base
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.Units import *
import time
import re


class Case(Base):
"""用例基类, 用于区别Configuration

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
None.

Returns:
Case (instance): 用例对象实例.

Raises:
None.

Examples:
CaseObject = Case(caseValidation)

"""

def __init__(self, parameters):
super(Case, self).__init__(parameters)

def preTestCase(self):
"""用户自定义, 主要在TestCase中调用addParameter()设置Case的parameter.

Args:
None

Returns:
None

Raises:
None

Examples:
1、子类继承时重写.
from UniAutos.TestController.Base import Base
class Case(Base):
def preTestCase(self):
self.addParameter(name='fs_type',
display_name='filesystem type',
description='ext3 or ext2 or mixed',
default_value='ext3',
validation={'valid_values': ['ext3', 'ext2']},
type='select',
identity='id1',
assigned_value='ext2',
optional=True)
"""
return

def postTestCase(self):
"""用户自定义，主要在TestCase执行完成后的清理.

默认的postTestCase 首先进行故障恢复，然后执行在用例中定义的清理堆栈.

Args:
None.

Returns:
None.

Raises:
UniAutosException: 当执行清理堆栈失败时抛出异常.

Examples:
self.postTestCase()

"""

sleep(1)
self.logger.info("This is Post Test Case~ ")

# todo recoverFault

try:
self.performCleanUp()
except Exception, error:
raise UniAutosException("An Exception Occurred during The Post-TestCase:\n%s" % error)
return

def checkCmd(self, callBack, checkType="success", express=None, **kwargs):
"""检查用例步骤执行结果是否符合预期

Args:
callBack (str): 用例步骤所使用的函数
checkType (str): (可选参数)执行的预期结果
express (str): (可选参数)执行失败的预期回显信息
kwargs (str): (可选参数)函数所需的参数

Returns:
None

Raises:
UniAutosException

Examples:
self.checkCmd(self.storageDevice.createDiskDomain, checkType="fail", express = "Error: The number of free hard",
name="diskdomain1",
diskDomainID="1",
sasNumber="1")

"""
runningStatus = "success"
try:
callBack(**kwargs)
except Exception, error:
runningStatus = "fail"
if checkType != runningStatus:
raise UniAutosException("Expect Running Status:%s Actually Status:%s\n" % (checkType, runningStatus))
if express and runningStatus == "fail":
if re.search(express, str(error), re.IGNORECASE):
self.logger.info("The Error Info is Correct ")
else:
raise UniAutosException("Expect Error Info:%s Actually Error Info:%s\n" % (express, error))

def check(self, objects, criteria, duration=0, interval=1, raiseException=True, changeByte=False, device=None, **args):

"""检查对象指定的状态是否达到指定值

Args:
objects (str|list) : 要检查的对象，或对象列表
(instancemethod): 实例方法，具体AW
criteria (dict|str) : 判断条件，例如:
当objects为componentBase, controller, Unified或list时, criteria为dict:
criteria = {'capacity': {'not less': '10GB'}}
criteria = {'name': 'Lun001', 'capacity': {'gt': '10GB', 'le': '20GB'}}
比较类型: 'eq', 'ne', 'gt', 'le', 'lt', 'ge', 'mt', 'nm', 'err'.
eq: equal to, ne: not equal to, gt: greater than, le: less than and equal to,
lt: less than, ge: greater than and equal to, mt: match, nm: not match,
err: 指定属性达到某个值直接报错
mt(match)为正则匹配(re.search); nm(not match).
当objects为instancemethod时，criteria为需要匹配到的正则表达式:


duration (int) : (可选参数)状态检测总时长,默认为0,只检查一次,objects类型为list时，总时长不应过小
interval (int) : (可选参数)轮询的时间间隔,单位秒(s),默认为1，当duration>0时有效
raiseException (boolean) : (可选参数)对象未达到预期状态是否抛出异常，默认True
args (dict) : (可选参数)当objects为instancemethod时有效,为方法的具体参数值
changeByte (bool) : (可选参数），是否将容量转化为byte，默认False
device (storage) : (可选参数），设备对象，changeByte参数为True时需要传入设备对象，默认取第一个阵列转换

Returns:
True: 实际值达到预期
[False, details]: 实际值未达到预期，且raiseException为False
details记录每个属性比对的结果[True|False|Unavailable],Unavailable为不存在指定的属性名

Raises:
UniAutosException

Examples:
1.轮询diskDomains的running_status不为Online1
self.check(diskDomains, duration=5, criteria={'running_status': {'ne': 'Online1'}})
2.检查wrapper方法cloneDelete执行有错误吗返回
self.check(self.storage.dispatch, criteria='Error', methodName='cloneDelete', params={'object': clone})
3.轮询diskDomains的running_status不为Online，且状态值为Fault时停止轮询并报错
self.check(diskDomains, duration=5, criteria={'running_status': {'ne': 'Online1', 'err': 'Fault'}})

"""
if not isinstance(criteria, dict) and not criteria:
raise UniAutosException('The expected key-value must be assigned.')
if not objects:
raise UniAutosException('The objects is None or there is no element in objects.')
from UniAutos.Component.ComponentBase import ComponentBase
from UniAutos.Device.Storage.Huawei.Unified import Unified
from UniAutos.Device.Host.Controller.OceanStor import OceanStor

changeByteFlag = False

if duration > 0 and 'startTime' not in locals():
startTime = int(time.time())

if isinstance(objects, list):
if len(objects) == 1:
return self.check(objects[0], interval=interval, duration=duration, raiseException=raiseException, criteria=criteria, changeByte=changeByte, device=device)
result = {}
for obj in objects:
result[obj] = self.check(obj, interval=interval, duration=duration, raiseException=raiseException, criteria=criteria, changeByte=changeByte, device=device)
if 'startTime' in locals():
timeIndex = int(time.time())
duration = duration - (timeIndex - startTime) - interval
startTime = timeIndex
return result

elif isinstance(objects,(ComponentBase, Unified, OceanStor)):
if changeByte:
if device is None:
device = self.resource.getDevice(deviceType="unified", deviceId="1")
device.dispatch("change_cli", {"capacity_mode": "precise"})
changeByteFlag = True
cmpMacro = {
'eq': self.__isEqual,
'ne': self.__isNotEqual,
'lt': self.__isLess,
'ge': self.__isNotLess,
'gt': self.__isMore,
'le': self.__isNotMore,
'mt': self.__isMatch,
'nm': self.__isNotMatch,
'err': self.__isMatch
}
preKeys = criteria.keys()
def getInfo(keys):
result = {}
sign = True
if isinstance(objects, ComponentBase):
res = objects.getProperties(keys)
elif isinstance(objects, Unified):
res = objects.getSystemInfo()
elif isinstance(objects, OceanStor):
res = objects.getSystemInfo()
for key in keys:
if key not in res:
result[key] = 'Unavailable'
sign = False
else:
if isinstance(criteria[key], str):
criteria[key] = {'eq': criteria[key]}
if isinstance(criteria[key], dict):
result[key] = True
for cmp in criteria[key]:
cmp_result = cmpMacro[cmp](res[key], criteria[key][cmp])
if cmp == 'err':
if cmp_result:
raise UniAutosException(
'[%s] object got an error state value for [\'%s\' = \'%s\'], '
'specified by you.' % (objects.__module__, key, res[key]))
else:
continue
result[key] = result[key] and cmp_result

if not result[key]:
result[key] = [result[key], res[key], criteria[key]]
sign = False

if not sign:
return result
else:
return True
if duration = 0 else False
elif Units.isTime(a) and Units.isTime(b):
return True if Units.compareTime(a, b) >= 0 else False
elif Units.isPercentage(str(a)) and Units.isPercentage(str(b)):
return True if Units.comparePercentage(a, b) >= 0 else False
return True if a >= b else False

def __isMatch(self, a, b):
return True if re.search(a, b) else False

def __isNotMatch(self, a, b):
return True if re.search(a, b) else False

if __name__ == "__main__":
pass
