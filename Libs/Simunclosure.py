Simuenclosure ::

#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：仿真框类
版权信息：华为技术有限公司，版本所有(C) 2014-2015
"""
import traceback
import re
import os
from time import time, sleep, strftime, localtime

from UniAutos.Device.Host.Simuenclosure.SimuenclosureBase import SimuenclosureBase
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos import Log
from UniAutos.Util.Time import sleep
from UniAutos.Util.Sql import Sql
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.ConnectionException import ConnectionException
from paramiko.ssh_exception import AuthenticationException


class Simuenclosure(SimuenclosureBase):
"""控制器初始化

功能说明: 控制器初始化

Args:
username (str) : 与控制器连接时需要使用的用户名
password (str) : 与控制器连接时需要使用的密码
params (dict) : params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str),
"type": (str)
}
params键值对说明
protocol (str): 通信协议，key可选，取值范围：["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，key可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，key可选
type (str): 连接的类型

Returns:
返回控制器的实例

Examples:
controller = OceanStor.discover(params)

"""

def __init__(self, username, password, params):
super(SimuenclosureBase, self).__init__(username, password, params)
self.component = None
self.productModel = ""
self.softVersion = "simuenclosure"
self.patchVersion = ""
self.__simuenclosure_id = None

log = Log.getLogger(__name__)

@property
def simuenclosure_id(self):
"""返回控制器的ID, 与Device的ID不同与component的id相同."""
return self.__simuenclosure_id

def setSimuenclosureId(self, simuenclosure_id):
"""设置控制器的ID.
Args:
ctrl_id (str): 设置控制器的ID属性.
"""
self.__simuenclosure_id = simuenclosure_id

@classmethod
def discover(cls, params):
"""获取 ip框对象

Args：
params (dict): params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str),
"type": (str)
}
params键值对说明:
protocol (str): 通信协议，key可选，取值范围["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，key可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，key可选
type (str): 连接的类型

Returns:
obj控制器对象

Examples:
controller = OceanStor.discover(params)

"""

obj = super(SimuenclosureBase, cls).discover(params)
obj.createLink()
return obj

def createLink(self):
status = self.getCmdObj().status
if status == 'normal':
self.run({"command": [""]}, sessionType='ignore')
else:
self.run({"command": [""]}, sessionType='ignore')

def run(self, params, sessionType=None):
"""控制器指定模式运行命令

Args:
sessionType (str): 阵列命令下发到哪种模式下，取值范围：['admincli', 'debug', 'mml', 'developer', 'diagnose'],
-默认是 'admincli'

Examples:
controller.run(params, sessionType='developer')
"""
if sessionType:
params['sessionType'] = sessionType

start = time()
command = " ".join(params["command"])
cmdStatus = {"command": command,
"start_time": strftime('%Y/%m/%d %H:%M:%S', localtime(start)),
'start_time_stamp': start,
'ip': self.localIP}
result = super(SimuenclosureBase, self).run(params)
end = time()
cmdStatus["execute_time"] = end - start
cmdStatus['end_time'] = strftime('%Y/%m/%d %H:%M:%S', localtime(end))
cmdStatus['end_time_stamp'] = end
return result

def refreshCmdObj(self, ip=None, username=None, password=None, controlmsg={}):
"""更新底层ssh连接使用的ip地址、用户名、密码

Args:
ip (str): ip地址
username (str): 用户名
password (str): 密码
controlmsg (dict): 存放控制器的连接信息，包含key：ip, username, password

"""
self.component.pauseCommandsDispatch("20M")
simuenclosureId = self.component.getProperty("id")
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% simuenclosureId)
loggedOnce = True
sleep(1)
cmdObj = self.getCmdObj()
if controlmsg:
cmdObj.setConnectInfo(ip, username, password, controlmsg)
else:
cmdObj.setConnectInfo(ip, username, password)
self.component.unpauseCommandDispatch()

def restoreCmdObj(self):
"""恢复底层ssh连接使用的连接信息到初始状态

"""
simuenclosureId = self.simuenclosure_id
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% simuenclosureId)
loggedOnce = True
sleep(1)
cmdObj = self.getCmdObj()
cmdObj.restoreConnectInfo()

def restoreLoginUser(self):
"""restore controller login user with test bed specified.

Examples:
controller.restoreLoginUser()

"""
conn = self.getCmdObj()
conn.restoreConnectInfo()
