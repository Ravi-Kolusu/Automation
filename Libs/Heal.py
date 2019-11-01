Heal ::

#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: Heal, Configuration类, 该类定义self.validateAndHeal为False, 仅用于创建Configuration.

"""

from UniAutos.Requirement.ConfigureInfoBase import ConfigureInfoBase

class Heal(ConfigureInfoBase):
"""Heal, Configuration类, 该类定义self.validateAndHeal为False, 仅用于创建Configuration.

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

def __init__(self, testCase, deviceId, deviceType, componentDict, validateAndHeal=False,
device=None, configId=None):
super(Heal, self).__init__(testCase, deviceId, deviceType, componentDict, validateAndHeal=validateAndHeal,
device=device, configId=configId)
self.validateAndHeal = False

if __name__ == "__main__":
pass