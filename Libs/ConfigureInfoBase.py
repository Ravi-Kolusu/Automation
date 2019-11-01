#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: ConfigurationBase, Configuration基类.

"""
import re

from UniAutos.Requirement.RequirementBase import RequirementBase
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.PropertyException import PropertyException
from UniAutos.Device.Storage.StorageBase import StorageBase


class ConfigureInfoBase(RequirementBase):
"""Configuration基类定义，

Args:
testCase (instance): Requirement所属的测试用例的对象，必选参数.
deviceId (str): 需要创建Requirement配置业务的设备ID，必选参数.
deviceType (str): 需要创建Component的设备的类型, 取值范围为: block|file|unified|any, 必选参数.
componentDict (dict): 为需要配置的Component的参数，key为component的别名，value为多个相同类型的
-component的参数列表, 必选参数.
validateAndHel (bool): True为Heal, False为创建新的Configuration, 默认为False.
configId (str): 唯一标识符，这将有助于测试脚本查找、选择来应用此配置, 可选参数，默认为None.
device (instance): UniAutos.Device.Storage.StorageBase, 用于创建配置的设备, 默认为None, 可使用
-setDevice方法设置.

Attributes:
self.testCase (instance): Requirement所属的测试用例的对象.
self.deviceId (str): 需要创建Requirement配置业务的设备ID
self.deviceType (str): 与参数的deviceType相同.
self.validateAndHeal (bool): 与参数的validateAndHel相同.
self.device (instance): 与参数的device相同.
self.configId (str): 与参数的configId相同.
其他变量：
由componentDict进行创建, 使用componentDict的key作为变量名， value为变量的值.

Returns:
ConfigureInfoBase (instance): ConfigureInfoBase实例.

Raises：
InvalidParamException: 参数传入错误.

Examples:
None.
"""

def __init__(self, testCase, deviceType, deviceId, componentDict,validateAndHeal=False,
device=None, configId=None):
super(ConfigureInfoBase, self).__init__()
self.deviceType = deviceType
self.deviceId = deviceId
self.testCase = testCase
if self.deviceType is None and not re.match(r'^block|file|unified|any$', self.deviceType):
raise InvalidParamException("The device type must be specify, "
"and must be one of 'block|file|unified|any' ")

self.validateAndHeal = validateAndHeal
self.device = None
self.setDevice(device)
self.configId = configId

for componentName in componentDict:
setattr(self, componentName.lower(), componentDict[componentName])

def setDevice(self, device):
"""给Configuration设置设备对象

Args:
device (instance): 需要设置给Configuration的设备对象.

Returns:
None.

Raises:
InvalidParamException: 传入的参数错误.

Examples:
None.
"""
if isinstance(device, StorageBase):
self.device = device
elif self.deviceId and self.deviceType:
self.device = self.testCase.getDevice(self.deviceType, self.deviceId)
else:
raise InvalidParamException("The Parameter device[%s] is not a Storage Device, Please Check." % device)

def getDevice(self):
"""获取Configuration的设备对象

获取Configuration的设备对象时必须使用该方法.

Args:
None.

Returns:
device (instance): 获取的Configuration设备对象.

Raises:
PropertyException: 设备不是UniAutos.Device.Storage.StorageBase类型时.

Examples:
None.
"""
if isinstance(self.device, StorageBase):
return self.device
else:
raise PropertyException("The storage device is not defined for this %s" % self.__module__)

if __name__ == "__main__":
pass
