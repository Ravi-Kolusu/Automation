IPenclosure ::

#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：控制器类
版权信息：华为技术有限公司，版本所有(C) 2014-2015
"""
import traceback
import re
import os
import threading
from time import time, sleep, strftime, localtime

from UniAutos.Device.Host.IPenclosure.IPenclosureBase import IPenclosureBase
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos import Log
from UniAutos.Util.Time import sleep
from UniAutos.Util.Sql import Sql
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.ConnectionException import ConnectionException
from paramiko.ssh_exception import AuthenticationException


class IPenclosure(IPenclosureBase):
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
super(IPenclosure, self).__init__(username, password, params)
self.component = None
self.productModel = ""
self.softVersion = "ipenclosure"
self.patchVersion = ""
self.resetProcessInfo = {}
self.resetProcessInfoLock = threading.Lock()
self.__ipenclosure_id = None

log = Log.getLogger(__name__)

@property
def ipenclosure_id(self):
"""返回控制器的ID, 与Device的ID不同与component的id相同."""
return self.__ipenclosure_id

def setIpenclosureId(self, ipenclosure_id):
"""设置控制器的ID.
Args:
ctrl_id (str): 设置控制器的ID属性.
"""
self.__ipenclosure_id = ipenclosure_id

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
wrappers = []
if 'tool_wrappers' in params:
wrappers = params.pop("tool_wrappers")

obj = super(IPenclosureBase, cls).discover(params)
obj.createLink()
obj.wrapper_list = wrappers
obj.original_wrapper_list = wrappers
return obj

def createLink(self):
status = self.getCmdObj().status
if status == 'normal':
self.run({"command": [""]}, sessionType='clilite')
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
result = super(IPenclosureBase, self).run(params)
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
ipenclosureId = self.component.getProperty("id")
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% ipenclosureId)
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
ipenclosureId = self.ipenclosure_id
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% ipenclosureId)
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

def moveFile(self, source, destination):
"""

Args:
source (str): 源文件路径，包含文件名，若存在特殊字符需要加转义字符.
destination (str): 目的文件目录或文件的全路径，若存在特殊字符需要加转义字符.

Returns:
None

Raise:
移动文件失败

Examples:
host.moveFile('/tmp/eth0', '/tmp/etest0')

"""
if source == destination:
return

response = self.run({"command": ["sudo", "mv", source, destination], "sessionType": "debug"})

def waitForReboot(self, waitForShutdown=True, timeout=3600, targetStatus=None):
"""Waits for Controller to come back from a reboot

Args:
waitForShutdown (Boolean): (Optional) Set to true to wait for the Controller to shutdown first. (Default = True).
timeout (int) : (Optional) Amount of time to wait for reboot, unit is "S"
(Default: 3600).
targetStatus (str) : (Optional) Set reboot target status.

"""
self.log.debug("Waiting for the controller %s to finish rebooting" % self.localIP)
endTime = time() + timeout
ibcPwd = "Storage@21st"
defaultInfo = self.getCmdObj().rawConnectInfo

# If specified, wait for the system to shutdown
if waitForShutdown:
self.log.debug("Waiting for the controller %s to complete shutdown" % self.localIP)
self.waitForShutdown(timeout=timeout)
self.log.debug("controller %s is shutdown" % self.localIP)

self.log.debug("Waiting for the controller %s to come up" % self.localIP)
while True:
try:
if self.isReachable():
if targetStatus in ["os_only", "debug"]:
# Set login accout to be ibc_os_hs
# releaes包升级调用该方法时先尝试用ibc账户登陆，如果认证失败，就用admin登陆
try:
# 连接正常时，等待5秒再登录
sleep(5)
self.command.setConnectInfo(username="ibc_os_hs", password=ibcPwd)
except AuthenticationException:
self.restoreCmdObj()
else:
self.restoreCmdObj()
if self.canCommunicate():
if targetStatus is None or self.command.status == targetStatus:
break
except Exception as ex:
self.log.warn(ex)
message = ex.message
sleep(10)
if time() > endTime:
raise UniAutosException("Timed out waiting for reboot [ip: %s]"
"\n(Timed out while waiting for the system to come up" % self.localIP)

def canCommunicate(self):
"""Checks to see if we can communicate with remote host by attempting to
send a test command

Returns:
True|False: True- Able to communicate
False - Unable to communicate
"""
if hasattr(self, "command") and self.getCmdObj():
if self.command.status == "normal":
return self.nodeStatus()
return False

def nodeStatus(self):
return True

def addResetProcessInfo(self, processName=None, times=1):
"""指定进程的故障注入次数

Args:
processName(str):进程名
times(int):故障注入次数

Returns:
resetProcessInfo (dic): {"app_data":1,...}

Examples:
ctrl.host.addResetProcessInfo("app_data",1)

"""
self.resetProcessInfoLock.acquire()
if processName:
if self.resetProcessInfo.get(processName):
self.resetProcessInfo[processName] += times
else:
self.resetProcessInfo[processName] = times
self.resetProcessInfoLock.release()
