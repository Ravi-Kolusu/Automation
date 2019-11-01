OceanStor ::

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

from UniAutos.Device.Host.Controller.ControllerBase import ControllerBase, IgnoreLogCommands
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos import Log
from UniAutos.Util.Time import sleep
from UniAutos.Util.Sql import Sql
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.ConnectionException import ConnectionException
from paramiko.ssh_exception import AuthenticationException


class OceanStor(ControllerBase):
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
super(OceanStor, self).__init__(username, password, params)
self.productModel = ""
self.softVersion = ""
self.SN = ""
self.systemRunningStatus = ""
self.systemHealthStatus = ""
self.totalCapacity = ""
self.location = ""
self.systemName = ""
self.systemHighWaterLevel = ""
self.systemLowWaterLevel = ""
self.component = None
self.wwn = ""
self.patchVersion = ""
self.__ctrl_id = None
self.__nodeId = None
self.isVstoreDevice = False
self.__vstoreControllers = {}
self.isDeviceError = False
self.resetProcessInfo = {}
self.resetProcessInfoLock = threading.Lock()

log = Log.getLogger(__name__)

@property
def vstoreControllers(self):
return self.__vstoreControllers

def addVstoreController(self, name, controller):
self.__vstoreControllers[name] = controller

def removeVstoreController(self, name):
self.__vstoreControllers.pop(name, None)

@property
def ctrl_id(self):
"""返回控制器的ID, 与Device的ID不同与component的id相同."""
return self.__ctrl_id

def setControllerId(self, ctrl_id):
"""设置控制器的ID.
Args:
ctrl_id (str): 设置控制器的ID属性.
"""
self.__ctrl_id = ctrl_id

def updateRunningVersion(self):
"""从阵列上查询ProductModel和ProductVersion

Examples:
controller = OceanStor.discover(params)
controller.updateRunningVersion()

"""
status = self.getCmdObj().status
oldProductModel = self.productModel
outputVer = None
catOutput = None
uname_output = None
if status == 'normal':
output = self.run({"command": ["show", "system", "general"]}, sessionType='admincli')
elif status == 'upgrade':
output = self.run({"command": ["show", "system", "general"]}, sessionType='ignore')
if re.search("Dorado", oldProductModel) or re.match(r'\d+10\s+V\d', oldProductModel):
self.logger.info("通过ibc刷新")
# 升级到release包，无法ibc登陆
try:
# 获取["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]
catOutput = self.run({"command": ["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]},
sessionType="debug")
# V6R3和V5R7C60版本配置文件versions.conf变更为manifest.yml
if re.search('SpcVersion=(\w+)', catOutput["stdout"]).group(1) in ["V600R003C00", "V500R007C60"]:
catOutput = self.run({"command": ["cat", "/OSM/conf/manifest.yml", "|", "grep", "SpcVersion"]},
sessionType="debug")
# 通过uname -r回显中的内核版本号来判断是否为ARM或者X86
uname_output = self.run({"command": ["uname", "-r"]}, sessionType="debug")
except Exception:
self.logger.warn('cat /OSM/conf/versions.conf failed, detail: %s' % traceback.format_exc())
return
else:
outputVer = self.run({"command": ["show", "upgrade", "package"]}, sessionType='ignore')
elif status in ['debug', 'os_only']:
self.logger.info("refresh by ibc")
try:
# 获取["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]
catOutput = self.run({"command": ["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]},
sessionType="ignore")
except:
self.logger.warn('cat /OSM/conf/versions.conf failed, detail: %s' % traceback.format_exc())
return

elif status is None:
try:
if self.command.protocol == 'emustorssh':
output = self.run({"command": ["show", "system", "general"]}, sessionType='admincli')
else:
output = self.run({"command": ["show", "system", "general"]}, sessionType='ignore')
except Exception:
if self.isDeviceError:
raise UniAutosException("DoradoV6R3C00 or Simulation system is error")
self.logger.error('login faild, user: admin, faild info: %s' % traceback.format_exc())
self.logger.info("通过ibc刷新")
# 升级到release包，无法ibc登陆
try:
try:
self.command.setConnectInfo(username="ibc_os_hs", password='Storage@21st')
except AuthenticationException:
self.restoreCmdObj()
# 获取["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]
catOutput = self.run({"command": ["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]},
sessionType="ignore")
output = {"stdout":'some massage'}
except Exception:
self.logger.warn('cat /OSM/conf/versions.conf failed, detail: %s' % traceback.format_exc())
return
else:
return None

if output["stdout"] is None or "The system is being upgraded" in output["stdout"]:
self.log.warn("No version was shown,wripper not update")
return
output = self.split(output["stdout"])
infoRegex = {
"system_name": 'System Name\s*:\s*(.+)',
"health_status": 'Health Status\s*:\s*(.+)',
"running_status": 'Running Status\s*:\s*(.+)',
"totalcapacity": 'Total Capacity\s*:\s*(.+)',
"product_model": 'Product Model\s*:\s*(.+)',
"product_version": 'Product Version\s*:\s*(.{,19})',
"patch_version": 'Patch Version\s*:\s*(.+)',
"sn": 'SN\s*:\s*(.+)',
"location": 'Location\s*:\s*(.+)',
"high_water_level": 'High Water Level...\s*:\s*(.+)',
"low_water_level": 'Low Water Level...\s*:\s*(.+)',
'wwn': 'WWN\s*:\s*(.+)'
}
productInfo = {}
for line in output:
line = re.sub("(^\s+|\s+$)", "", line)
for key in infoRegex.keys():
matcher = re.match(infoRegex[key], line)
if matcher:
value = matcher.groups()[0]
productInfo[key] = value.strip()
break
if outputVer is not None:
ctrlId = self.ctrl_id
outputVer = self.split(outputVer["stdout"])[5:]
result = []
controllerVerssion = {}
for line in outputVer:
if 'HotPatch' in line:
break
pattern = "\s+(\w+)\s+(\w+)\s+(\S+)\s+(\w+)\s+(\S+)\s+(\w+)"
match = re.match(pattern, line, re.I)
if match:
VersionLine = {"SN": match.group(1),
"Name": match.group(2),
"IP": match.group(3),
"CurrentVersion": match.group(4),
"HistoryVersion": match.group(5),
"Type": match.group(6)}
result.append(VersionLine)
for i in result:
if i['Name'] == ctrlId:
controllerVerssion['name'] = i['Name']
# 如果版本号中含有"SPC"字段，则仅保留SPC作为patchversion字段
if 'SPC' in i['CurrentVersion']:
id = i['CurrentVersion'].find('SP')
controllerVerssion['product_version'] = i['CurrentVersion'][:id].strip()
match = re.findall('SPC\d\d\d', i['CurrentVersion'])
if match:
controllerVerssion['patch_version'] = match[0]
productInfo["patch_version"] = controllerVerssion['patch_version']
# 如果版本号中只含有"SPH"字段，则当成普通版本处理，剔除patchversion字段
elif 'SPH' in i['CurrentVersion']:
id = i['CurrentVersion'].find('SP')
controllerVerssion['product_version'] = i['CurrentVersion'][:id].strip()
if "patch_version" in productInfo:
del productInfo["patch_version"]
else:
controllerVerssion['product_version'] = i['CurrentVersion']
if "patch_version" in productInfo:
del productInfo["patch_version"]
productInfo["product_version"] = controllerVerssion['product_version']
break
# dorado版本 解析["cat", "/OSM/conf/versions.conf", "|", "grep", "SpcVersion"]来获取版本信息
if catOutput is not None:
catOutput = catOutput["stdout"]
controllerVerssion = {}
matcher = re.search('SpcVersion(=|:)\s{,2}(\S+)', catOutput)
if matcher is not None:
SpcVersion = re.sub('T', '', matcher.group(2))
if 'SPC' in SpcVersion:
id = SpcVersion.find('SP')
controllerVerssion['product_version'] = SpcVersion[:id].strip()
match = re.findall('SPC\d\d\d', SpcVersion)
if match:
controllerVerssion['patch_version'] = match[0]
productInfo["patch_version"] = controllerVerssion['patch_version']
# 如果版本号中只含有"SPH"字段，则当成普通版本处理，剔除patchversion字段
elif 'SPH' in SpcVersion:
id = SpcVersion.find('SP')
controllerVerssion['product_version'] = SpcVersion[:id].strip()
if "patch_version" in productInfo:
del productInfo["patch_version"]
else:
# V5R7C60内核版本包含4.19则将版本号加上Kunpeng
if SpcVersion == "V500R007C60" and "4.19" in uname_output["stdout"]:
SpcVersion = "V500R007C60 Kunpeng"
controllerVerssion['product_version'] = SpcVersion
if "patch_version" in productInfo:
del productInfo["patch_version"]
productInfo["product_version"] = controllerVerssion['product_version']
self.patchVersion = ""
self.productModel = productInfo.get("product_model", "")
# Dorado C30 技术项目版本，继承V300R001C20，待正式版本后适配
self.softVersion = productInfo.get("product_version", "") \
if productInfo.get('product_version', '') != 'FrontEndAAV' else 'V600R002C00'
if "patch_version" in productInfo:
if 'SPC' in productInfo["patch_version"]:
match = re.findall('SPC\d\d\d', productInfo["patch_version"])
if match:
self.patchVersion = match[0]
# 如果版本号中未含有"SPC"字段，则当成普通版本处理，剔除patchversion字段
else:
del productInfo["patch_version"]
self.SN = productInfo.get("sn", "")
self.systemName = productInfo.get("system_name", "")
self.location = productInfo.get("location", "")
self.systemHealthStatus = productInfo.get("health_status", "")
self.systemRunningStatus = productInfo.get("running_status", "")
self.totalCapacity = productInfo.get("totalcapacity", "")
self.systemHighWaterLevel = productInfo.get("high_water_level", "")
self.systemLowWaterLevel = productInfo.get("low_water_level", "")
self.wwn = productInfo.get("wwn", "")

def getSystemName(self):
"""返回系统名称
Returns:
systemName (str): 控制器的名称

Examples:
controller = OceanStor.discover(params)
controller.getSystemName()

"""
return self.systemName

def getLocation(self):
"""返回设备位置
Returns:
location (str): 控制器的位置

Examples:
controller = OceanStor.discover(params)
controller.getLocation()
"""
return self.location

def getWWN(self):
"""返回WWN

Returns:
wwn (str): WWN 信息
Examples:
controller = OceanStor.discover(params)
controller.getWWN()

"""
return self.wwn

def getSN(self):
"""返回SN

Returns:
SN (str): 控制器的SN

Examples:
controller = OceanStor.discover(params)
controller.getSN()

"""
return self.SN

def getRunningVersion(self):
"""返回ProductVersion
Examples:
controller = OceanStor.discover(params)
controller.getRunningVersion()
"""
return self.softVersion

def getPatchVersion(self):
"""返回ProductVersion
Examples:
controller = OceanStor.discover(params)
controller.getRunningVersion()

"""
return self.patchVersion

def getRunningModel(self):
"""返回ProductModel
Examples:
controller = OceanStor.discover(params)
controller.getRunningModel()
"""
return self.productModel

def getTotalCapacity(self):
"""返回totalCapacity

Examples:
controller = OceanStor.discover(params)
controller.getTotalCapacity()

"""
return self.totalCapacity

def getHealthStatus(self):
"""返回Health_Status

Examples:
controller = OceanStor.discover(params)
controller.getHealthStatus()

"""
return self.systemHealthStatus

def getRunningStatus(self):
"""返回Running_Status
Examples:
controller = OceanStor.discover(params)
controller.getRunningStatus()

"""
return self.systemRunningStatus

def getHighWaterLevel(self):
"""返回HighWaterLevel

Examples:
controller = OceanStor.discover(params)
controller.getHighWaterLevel()

"""
return self.systemHighWaterLevel

def getLowWaterLevel(self):
"""返回LowWaterLevele

Examples:
controller = OceanStor.discover(params)
controller.getLowWaterLevel()

"""
return self.systemLowWaterLevel

@classmethod
def discover(cls, params):
"""获取 控制器对象

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

obj = super(OceanStor, cls).discover(params)
obj.updateRunningVersion()
version = obj.getRunningVersion()
hasVersion = 0
if version is not None:
hasVersion = 1
obj.release = version
obj.wrapper_list = wrappers
obj.original_wrapper_list = wrappers
# def tmpMethod():
# module = "UniAutos.Wrapper.Tool.AdminCli"
# __import__(module)
# moduleClass = getattr(sys.modules[module], "AdminCli")
# return moduleClass()
# adminCliReq = tmpMethod

# module = "UniAutos.Wrapper.Tool.AdminCli.AdminCli"
# __import__(module)
# moduleClass = getattr(sys.modules[module], "AdminCli")
# wrapperObj = moduleClass(params)
# obj.registerToolWrapper(host=obj, wrapper=wrapperObj)
return obj

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
'sn': self.SN,
'ip': self.localIP}
result = super(OceanStor, self).run(params)
end = time()
cmdStatus["execute_time"] = end - start
cmdStatus['end_time'] = strftime('%Y/%m/%d %H:%M:%S', localtime(end))
cmdStatus['end_time_stamp'] = end

# 判断是否需要记录到数据库
flag = False
for _c in IgnoreLogCommands:
if not re.match(_c, command):
flag = True
break
self.writeCommandLog(cmdStatus, logCommand=flag)
return result

def runLinux(self, params):
"""
运行命令
Args：
params (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"view_params" : ""
"sessionType" : "admincli" "diagnose" "debug"(linux命令行) 三选一，默认是debug
}

params中具体键-值说明：
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
waitstr (str): 命令执行后的期望结束符，如果不写会有默认的结束符，如下
viewDict['admincli'] = 'admin:/>'
viewDict['debug'] = '@#>\s*$'
viewDict['diagnose'] = ':/diagnose>'
directory (str): 指定命令执行的目录
timeout (int): 命令执行超时时间，默认180S，不会很精确
sessionType (str): 命令下发的视图, 默认为debug, 还可填写 diagnose和admincli
attach (str): 进入diagnose后attach的进程名
view_params (dict): 视图切换需要的参数

Returns:
result: 交互式命令的整个执行过程的输出

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {"command": ["sftp", "admin@100.148.115.39"], "waitstr":
"password", "input": ["123456", "[>#]", "ls", "[>#]"],
"directory": "/home/"
'sessionType': 'debug'}
result = self.run(cmdSpec)

"""
if 'wrapper' in params and hasattr(params['wrapper'], 'sessionType'):
params['sessionType'] = params["wrapper"].sessionType
if 'timeout' not in params:
params['timeout'] = 480 # 默认的命令超时时间 8 分钟
return self.run(params, sessionType="ignore")

def sftpGet(self, ip, port, user, password, files, target, timeout=1200):
"""
获取指定sftp服务器上的文件到主机

Args:
ip (str): 目前IP
port (str): 目前port
user (str): 用户名
password (str): 密码
files (str): 包含正则的字符串
target (str): 目标路径
timeout (int): (optional) 超时时间，默认1200S

Examples:
self.dockerNode.sftpGet(ip='10.183.196.235', port='22', user='root', password='huawei@123',
files=['/home/roc_pipeline_alpha/10lun_32th_8k_seq.xml'], target='/home/permitdir')

"""

cmd = "sudo sftp -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -P {0} {1}@{2}".format(port, user, ip)
params = {
"command": [cmd],
"input": [password, "sftp>"],
"waitstr": "assword:",
"timeout": timeout,
}
result = self.runLinux(params)

for f in files:
cmd = "get %s %s" % (f, target)
params = {
"command": [cmd],
"waitstr": 'sftp>',
"timeout": timeout,
}
self.runLinux(params)
params = {
"command": ['quit'],
}
self.runLinux(params)

def nodeFlowStatus(self):
"""get current node flow status

Returns:
True, if cluster status and current node flow status is Normal.
False, if cluster status or current node flow status is not Normal.
"""
return True

def canCommunicate(self):
"""Checks to see if we can communicate with remote host by attempting to
send a test command

Returns:
True|False: True- Able to communicate
False - Unable to communicate
"""
if hasattr(self, "command") and self.getCmdObj():
if self.command.status in ["upgrade", "os_only"]:
return True
elif self.command.status == "normal":
# 目前不清楚当前那些型号和版本支持sys showflowstatus, 故仅支持dorado相关版本.
if 'dorado' in self.productModel.lower():
return self.nodeFlowStatus()
return True
try:
response = self.run({"command": ['show system general'], "timeout": 10})
except Exception:
self.log.debug("Cannot communicate with this host")
return False
if re.search(r'Health Status\s*:\s*(.+)', response["stdout"]):
if 'dorado' in self.productModel.lower():
return self.nodeFlowStatus()
else:
return True
return False

def getNodeId(self):
"""get current nodeid

Changes:
2016-03-16 y00292329 Created

"""

output = self.dispatch("sysShowCls")
stdout = output[0]['stdout']
for line in stdout:
match = re.search('local node id\s+:\s*(\d)', line)
if match:
self.__nodeId = match.group(1)
return self.__nodeId

@property
def nodeId(self):
"""Current controller node id."""
if self.__nodeId is None:
self.getNodeId()
return self.__nodeId

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
if targetStatus == 'minisystem':
break
if self.canCommunicate():
if targetStatus is None or self.command.status == targetStatus:
#仿真环境能切换admin模式代表系统正常
if self.command.protocol == "emustorssh":
result = self.command.cmd({"command": ["/ISM/cli/start.sh -u admin"],
"sessionType":"debug",
"waitstr":"admin:/>"})
if "Product Model" in result["stdout"] and "Product Version" in result["stdout"]:
self.logger.info("System is ready")
break
else:
self.logger.info("System is not ready, Please wait")
else:
break
except Exception as ex:
self.log.warn(ex)
message = ex.message
if targetStatus is None or self.command.status == targetStatus:
if "Reset password success" in message or "initialization cli error" in message:
defaultInfo["password"] = defaultInfo["newpassword"]
# 烧盘到V300R002C10版本之后,重启修改密码,修改密码成功但是无法正常进入admincli,
# 导致无法重置self.command.status == targetStatus，进不了if分支
else:
if "Reset password success" in message:
defaultInfo["password"] = defaultInfo["newpassword"]

sleep(10)
if time() > endTime:
raise UniAutosException("Timed out waiting for reboot [ip: %s]"
"\n(Timed out while waiting for the system to come up" % self.localIP)
pass

def getBootMode(self):
"""获取当前系统的启动模式

Returns:
normal|rescue： normal mode or rescue mode.

"""

# 如果能正常下发admin cli命令证明是normal模式， 否则为rescue模式.
try:
self.run({"command": ["show", "system", "general"]}, sessionType='admincli')
except Exception:
# todo minisystem如何判断
return "rescue"

return "normal"

def doesPathExist(self, params):
"""判断路径是否存在

Args:
params (dict): 需要查询的文件或目录信息，键值对说明如下：
path (str): 文件或目录路径.
username (str): 用户名.
password (str): 密码.

Returns:
result (bool): 存在返回True，否则返回False

Raises:
InvalidParamException: 未指定参数或文件路径.

"""
if "path" not in params:
raise InvalidParamException("Have not define dir or file path.")

response = self.run({"command": ["ls", params["path"]], "sessionType": "debug"})
result = True
if response["rc"] != 0:
if re.search("No such file or directory", response["stdout"], re.IGNORECASE):
result = False

return result

def copyFile(self, source, destination):
"""删除指定的文件

Args:
source (str): 源文件路径，包含文件名，若存在特殊字符需要加转义字符.
destination (str): 目的文件目录或文件的全路径，若存在特殊字符需要加转义字符.

Raises:
CommandException: 拷贝文件失败.

Examples:
hostObj.copyFile("/root/1.txt", "/root/Desktop/2.txt")
or
hostObj.copyFile("/root/1.txt", "/root/Desktop")

"""
if source == destination:
return

response = self.run({"command": ["cp", "-f", source, destination], "sessionType": "debug"})

def deleteFile(self, filePath):
"""删除指定的文件

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.

Returns:
None.

Raises:
InvalidParamException: 输入的文件为"/"目录.
CommandException: 删除文件失败.

Examples:
hostObj.deleteFile("/root/1.txt")

"""
if filePath == "/":
raise InvalidParamException("Attempting to delete root is not allowed.")
response = self.run({"command": ['sudo', "rm", "-rf", filePath], 'sessionType': 'debug'})
if response["rc"] != 0\
and re.search('not found|No such file or directory|-bash:|: cannot', response["stdout"], re.IGNORECASE):
raise CommandException("Unable to delete %s" % filePath)

def setFileAccessPermissions(self, permission, path):
response = self.run({"command": ['sudo', "chmod", permission, path], 'sessionType': 'debug'})

if response["rc"] != 0\
and re.search('not found|No such file or directory|-bash:|: cannot', response["stdout"], re.IGNORECASE):
raise CommandException("Problem chmod file: %s \n Error: %s"
% (path, response["stderr"]))

def createFile(self, filePath, username=None, password=None):
"""创建指定的文件

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.

Returns:
None.

Raises:
CommandException: 创建文件失败.

Examples:
hostObj.createFile("/root/1.txt")

"""
userOptions = {}
param = {"command": ["touch", filePath], 'sessionType': 'debug'}
if username and password:
userOptions = {"username": username,
"password": password}
param.update(userOptions)
response = self.run(param)
if response["rc"] != 0:
if re.search('not found|No such file or directory|-bash:|: cannot', response["stdout"], re.IGNORECASE):
raise CommandException("Problem creating file: %s\n Error: %s" % (filePath, response["stderr"]))

def writeToFile(self, filePath, contents, append=True):
"""向文件中写类容

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.
contents (str): 向文件写的类容
append (bool): (可选参数)是否向文件中追加，默认True

Returns:
None.

Raises:
CommandException: 创建文件失败.

Examples:
hostObj.writeToFile(filePath="/root/1.txt",contents="aaaa")

"""
userOptions = {}
type = ">"
if append:
type = ">>"
param = {"command": ['sudo', "echo", "\'%s\'" % contents, type, filePath], 'sessionType': 'debug'}
response = self.run(param)
if response["rc"] != 0:
if re.search('not found|No such file or directory|-bash:|: cannot', response["stdout"], re.IGNORECASE):
raise CommandException("Problem write contents to file: %s\n Error: %s" % (filePath, response["stderr"]))

def compareData(self, srcobj, dstobj, srcoffset=None, dstoffset=None, srclength=None, dstlength=None):
"""
对两个文件进行数据比较,数据不一致会保留当前环境，以便定位

Args:
src (obj/str): 比较源数据对象,文件系统路径
dst (obj/str): 比较目标数据对象,文件系统路径
srcoffset (str): 偏移量 与 dstoffset，否则无效
dstoffset (str): 偏移量 与 srcoffset，否则无效
srclength (str): 长度
dstlength (str): 长度
Return:
None
Example：
# 验证不传入偏移量
self.hostDevice.compareData(lunlist[0], lunlist[1])
# 验证只传入一个偏移量
self.hostDevice.compareData(lunlist[0] ,lunlist[1], srcoffset=1)
self.hostDevice.compareData(lunlist[0], lunlist[1], dstoffset=1)
# 验证传入两个偏移量，不传入偏移长度
self.hostDevice.compareData(lunlist[0], lunlist[1], srcoffset=1, dstoffset=2)
# 验证传入两个偏移量，一个偏移长度
self.hostDevice.compareData(lunlist[0], lunlist[1], srcoffset=1, dstoffset=2, srclength=3)
self.hostDevice.compareData(lunlist[0], lunlist[1], srcoffset=1, dstoffset=2, dstlength=4)
# 验证传入两个偏移量，两个偏移长度
self.hostDevice.compareData(lunlist[0], lunlist[1], srcoffset=1, dstoffset=2, srclength=3, dstlength=4)
# 验证传入传入的LUN为list的情况
self.hostDevice.compareData(lunlist[0:2], lunlist[2:4])
# 验证传入的对象为lun快照
self.hostDevice.compareData(lunlist[2], lunlist[3], srcoffset=1, dstoffset=2, srclength=3, dstlength=4)
# 验证传入的是文件系统地址
self.hostDevice.compareData("/root/autoinst.xml", "/root/autoinst.xml")
# 验证传入不同类型的对象，一个LUN，一个文件系统
self.hostDevice.compareData("/root/autoinst.xml", lunlist[0])
"""
if isinstance(srcobj, list):
srcobjlen = len(srcobj)
else:
srcobjlen = 1
srcobj = [srcobj]
if isinstance(dstobj, list):
dstobjlen = len(dstobj)
else:
dstobjlen = 1
dstobj = [dstobj]
if srcobjlen == dstobjlen:
for src, dst in zip(srcobj, dstobj):
if srcoffset is not None and dstoffset is not None:
if srclength is not None and dstlength is not None:
command = ["cmp", src, dst, "-i", str(srcoffset), "-n",
str(srclength)]
else:
command = ["cmp", "-i", str(srcoffset) + ":" + str(dstoffset), src, dst]
else:
command = ["cmp", src, dst]
result = self.run({"command": command, 'sessionType': 'debug'})
if result['stderr']:
raise CommandException(str(result['stderr']))
else:
# 当stdout不为None且differ显示的数量不为0，数据不一致
matcher = re.search('differ:\s?char\s?(\d+)', result['stdout']) if result['stdout'] else None
if matcher and matcher.group(1) != '0':
self.logger.error("Data consistent compare failed between source: %s and target: %s" %
(src, dst))
raise UniAutosException('It\'s data inconsistent between the specified files.')
self.logger.info("Data consistent compare passed between source: %s and target: %s" % (src, dst))
else:
raise InvalidParamException

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

def refreshCmdObj(self, ip=None, username=None, password=None, controlmsg={}):
"""更新底层ssh连接使用的ip地址、用户名、密码

Args:
ip (str): ip地址
username (str): 用户名
password (str): 密码
controlmsg (dict): 存放控制器的连接信息，包含key：ip, username, password

"""
self.component.pauseCommandsDispatch("20M")
controllerId = self.component.getProperty("id")
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% controllerId)
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
controllerId = self.ctrl_id
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% controllerId)
loggedOnce = True
sleep(1)
cmdObj = self.getCmdObj()
cmdObj.restoreConnectInfo()

def showDbData(self, dbPath, dbFile, sqlStr):
"""query data of unified device database

Args:
dbPath (str): remote db file path.
dbFile (str): remote db file name.
sqlStr (str): sql statement string.

Returns:
list of execute sqlStr.

Examples:
self.getPrimaryController().getHostObject().showDbData('/OSM/coffer_data/omdb/',
'om_db.dat',
"select name from sqlite_master where type = 'table'")

"""
# copy remote sql to local host.
desDir = Log.LogFileDir
dbPath = re.sub(r'(/|\\)$', "", dbPath)
dbFilePath = '/'.join([dbPath, dbFile])
desFilePath = os.path.join(desDir, dbFile)
self.run({'command': ['cp %s %s' % (dbFilePath, '/home/permitdir/%s' % dbFile)]}, sessionType='debug')
self.run({'command': ['chmod', '777', '/home/permitdir/%s' % dbFile]}, sessionType='debug')
self.getFile({"source_file": '/home/permitdir/%s' % dbFile,
"destination_file": desFilePath})

# 尝试拷贝-shm 和 -wal文件，如果存在这两个文件则拷贝.
try:
self.run({'command': ['cp %s %s' % (dbFilePath + '-shm', '/home/permitdir/%s-shm' % dbFile)]},
sessionType='debug')
self.run({'command': ['cp %s %s' % (dbFilePath + '-wal', '/home/permitdir/%s-wal' % dbFile)]},
sessionType='debug')
self.getFile({"source_file": '/home/permitdir/%s-shm' % dbFile,
"destination_file": desFilePath + '-shm'})
self.getFile({"source_file": '/home/permitdir/%s-wal' % dbFile,
"destination_file": desFilePath + '-wal'})
except Exception:
self.logger.info('There is not %s-shm and %s-wal files.' % (dbFile, dbFile))

sql = Sql(desFilePath)
sqlData = sql.query(sqlStr)
sql.close()

# delete tmp file
os.remove(desFilePath)
self.run({'command': ['rm /home/permitdir/%s' % dbFile]}, sessionType='debug')
return sqlData

def changeLoginUser(self, username, password):
"""change controller login user.

Args:
username (str): username.
password (str): password.

Examples:
controller.changeLoginUser('admin', 'admin@storage')

"""
conn = self.getCmdObj()
conn.setConnectInfo(username=username, password=password)

def restoreLoginUser(self):
"""restore controller login user with test bed specified.

Examples:
controller.restoreLoginUser()

"""
conn = self.getCmdObj()
conn.restoreConnectInfo()

def get_package_compile_time(self, tgz_path, target_path):
"""获取指定升级包的编译时间.
Args:
tgz_path (string): tgz file path.
target_path (string): the extract target directory, do not end with '/'.
Returns:
compile_time (string): package compile time.
"""
ret = self.run({'command': ['tar -tf %s' % tgz_path]}, sessionType='debug')
for line in self.split(ret["stdout"]):
if line.startswith('product_versions.'):
self.extract_file(tgz_path, line, target_path)
file_context = self.run({'command': ['cat %s/%s' % (target_path, line)]}, sessionType='debug')
compile_regex = re.search(r'(Time=.*)', file_context['stdout'])
if compile_regex:
return self.trim(compile_regex.groups()[0])
return None

def extract_file(self, tgz_path, filename, target_path):
"""解压tgz文件中的指定文件到指定的目录.
Args:
tgz_path (string): tgz file path.
target_path (string): the extract target directory, do not end with '/'.
filename (string): need to extract filename.
Returns:
compile_time (string): package compile time.
"""
self.run({'command': ['tar -zxvf %s -C %s %s' % (tgz_path, target_path, filename)]}, sessionType='debug')

def get_current_compile_time(self):
"""获取阵列当前软件包的编译时间.
Returns:
compile_time (string): package compile time."""
file_context = self.run({'command': ['cat /OSM/conf/versions.conf']}, sessionType='debug')
compile_regex = re.search(r'(Time=.*)', file_context['stdout'])
if compile_regex:
return self.trim(compile_regex.groups()[0])

def getArrayFile(self, remoteFile):
"""query data of unified device database

Args:
dbPath (str): remote db file path.
dbFile (str): remote db file name.
sqlStr (str): sql statement string.

Returns:
list of execute sqlStr.

Examples:
self.getPrimaryController().getHostObject().getFile('/OSM/coffer_data/omdb/om_db.dat')

"""
# copy remote sql to local host.
fileName = os.path.split(remoteFile)[-1]
desDir = Log.LogFileDir
desFilePath = os.path.join(desDir, fileName)
self.run({'command': ['cp %s %s' % (remoteFile, '/home/permitdir/%s' % fileName)]}, sessionType='debug')
self.getFile({"source_file": '/home/permitdir/%s' % fileName,
"destination_file": desFilePath})
return desFilePath

def getProcessId(self, processName):
"""获取指定进程名称的进程ID

Args:
processName (str): 进程名称.

Returns:
reArr (list): 指定进程名称的所有进程id.

Raises:
UniAutosException: 命令执行失败.

Examples:
pids = ctrl.getProcessId("sshd")
Output:
>['22912', '23430', '27333', '29117', '30581']

"""
response = self.run({"command": ["ps", "-C", processName, "-o", "pid"]}, sessionType='debug')
if response["rc"] != 0:
raise UniAutosException("Unable to find any processes with given process name: %s" % processName)

retArr = []
for line in self.split(response["stdout"]):
tmpMatch = re.match(r'\d+', self.trim(line))
if tmpMatch:
retArr.append(tmpMatch.group())
return retArr

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
