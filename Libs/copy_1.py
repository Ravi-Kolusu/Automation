HOSTBASE.PY
"""

Function: host base class, providing host-side common operating interface (not distinguish between the operating system）

"""

import re
import thread
import threading
import os
import sys
from time import time, sleep, strftime
import traceback
import json
import codecs
from UniAutos.Util.Time import repeat_timeout

try:
import requests
except ImportError:
pass

from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.UnImplementedException import UnImplementedException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.DictKeyException import DictKeyException
from UniAutos.Command import CommandBase
from UniAutos.Dispatcher import Dispatcher
from UniAutos import Log
from UniAutos.Util.Ping import quiet_ping
from UniAutos.Util.Codec import getFormatString
from UniAutos.Util.DegradePermissionConfig import *
from UniAutos.Command.Connection.SQLConnection import SQLConnection
from copy import deepcopy

HAS_STAF = True
try:
from UniSTAF.STAFConnection import UniSTAF
except ImportError:
HAS_STAF = False

gCommandLogLock = thread.allocate_lock()
ginitToolsLock = thread.allocate_lock()


class Writer(object):
"""Log command execution"""
def __init__(self):
self.lock = threading.RLock()
self.filename = None
self.isFirst = True

def writeCmd(self, filename, **kwargs):
"""Execution result written commands.js files"""
self.filename = filename
self.lock.acquire()

# TODO 2017-08-03 h90006090 紧急合入，暂时解决reason中包含不可json化的字符串
try:
json.dumps(kwargs)
except TypeError:
if kwargs.get('reason'):
kwargs['reason'] = "fail reason is too large, please check case detail."
if kwargs.get('post'):
kwargs['post'] = "fail reason is too large, please check case detail."
try:
stream = self._open()
try:
if self.isFirst:
stream.write("[")
stream.write(json.dumps(kwargs))
stream.write(']')
self.isFirst = False
else:
stream.seek(-1, os.SEEK_END)
stream.truncate()
stream.write(',')
stream.write(json.dumps(kwargs))
stream.write(']')
finally:
self._flush(stream)
finally:
self.lock.release()

def _open(self):
stream = codecs.open(self.filename, mode='a', encoding='UTF-8')
return stream

def _flush(self, stream):
stream.flush()
stream.close()

# writer = Writer()


class HostBase(DeviceBase, Dispatcher):
"""Host base class

Args.:
username (str): account name
password (str): account password
params (dict): params = {
"type": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str)
}
params key-value pair description
type (str): communication protocol, key optional, range ["storSSH", "standSSH", "local", "telnet", " xmlrpc"]
port (int): communication port, key optional
ipv4_address (str): IPv4 address of the host, key and ipv6_address are required
ipv6_address (str): the host's ipv6 address, key and ipv4_address are required
os (str): host operating system type, key optional

Returns:
Host object

"""

log = Log.getLogger(__name__)

@validateParam(username=str, password=str, params=dict)
def __init__(self, username, password, params):
super(HostBase, self).__init__()
self.rawParams = params
self.localIP = "localhost"
self.detail = params.get('detail')
if "command" in params:
self.command = params["command"]
if params["ipv4_address"]:
self.localIP = params["ipv4_address"]
elif params["ipv6_address"]:
self.localIP = params["ipv6_address"]

self.stafConnection = None
if HAS_STAF:
if isinstance(self.localIP, list):
for ip in self.localIP:
self.stafConnection = UniSTAF(remoteIp=ip)
else:
self.stafConnection = UniSTAF(remoteIp=self.localIP)

self.port = None
if "port" in params:
self.port = params["port"]

self.connectionType = None
if "type" in params:
self.connectionType = params["type"]

self.monitorProgress = ["sshd"]
if "monitor_processes" in params:
self.monitorProgress = params["monitor_processes"]

self.deviceId = params.get("device_id", None)
self.type = params.get("device_type")
self.username = username
self.password = password
self.information = params
if Log.LogFileDir:
self.commandLogPath = Log.LogFileDir + os.sep + "Command_Execution_Time.txt"
else:
self.commandLogPath = os.path.curdir + os.sep + "Command_Execution_Time.txt"
self.architecture = ''
self.networkInfo = {}
self.ioTool = {'sdtester': None, 'vdbench': None, 'unifsio': None, 'uniblkio': None, 'xcloud': None,
'unifilestressor': None, 'doradoio': None, 'unmapbatch': None, 'scsiio': None, 'dynamo': None,
'iometer': None, 'simul':None}
self.controllerIoTool = {}
self.__timeout = None
self.__stopOnTimeOut = False
self.hasIOError = False
pass

def setTimeout(self, times, stopOnTimeOut=False):
"""Set the timeout period, you need to return to none at the end of the script

Args.:
welcome to our website!

Changes:
2015-11-13 y00292329 Created

"""
if isinstance(times, int):
self.__timeout = times
self.logger.debug('set host timeout: host[%s] timeout[%s].' % (self.localIP, times))
self.__stopOnTimeOut = stopOnTimeOut

def resetTimeout(self):
"""When the timeout is

Args.:
Time(int): IP address

Changes:
2015-11-13 y00292329 Created

"""

self.__timeout = None
self.logger.debug('reset host timeout: host[%s]' % self.localIP)
self.__stopOnTimeOut = False

@property
def getTimeout(self):
"""Get timeout

"""
return self.__timeout

@property
def getStopOnTimeout(self):
"""Get timeout interrupt


"""
return self.__stopOnTimeOut

@classmethod
def discover(cls, params):
"""Generate a concrete Host object

Args:
Params (dict): params = {
"type" : (str),
"port" : (str),
"ipv4_address" : (str),
"ipv6_address" : (str),
"os" : (str),
"username" : (str),
"password" : (str),
}
Params key-value pair description
Type (str): communication protocol, key optional, range of values ​​["storSSH", "standSSH", "local", "telnet", "xmlrpc"]
Port (int): communication port, key optional
Ipv4_address (str): The ipv4 address of the host, the key and ipv6_address must be selected
Ipv6_address (str): The ipv6 address of the host, the key and ipv4_address must be selected
Os (str): host operating system type

Returns:
Host对象
"""
username = params["username"]
password = params.get('password', '')
cls.setLocalHostIP(params)
command = cls.discoverCommandInstance(username, password, params)
params["command"] = command

obj = None
discoverErrors = ""
if str(cls) == str(HostBase):
for osType in ('Unix', 'Windows'):
try:
module = "UniAutos.Device.Host." + osType
__import__(module)
moduleClass = getattr(sys.modules[module], osType)
newClass = moduleClass.discoverClass(command)

moduleName = newClass[0: newClass.rfind(".")]
className = newClass[newClass.rfind(".") + 1: len(newClass)]

__import__(moduleName)

obj = getattr(sys.modules[moduleName], className)(username, password, params)
return obj
except Exception, e:
cls.logger.debug('####HOST####%s' % traceback.format_exc())
discoverErrors += moduleClass.__module__ + "." + moduleClass.__class__.__name__ + ".__init__ exception:\n" + e.message + "\n"
if "os" in params:
os = params.pop("os")
if re.match("windows", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Windows"
__import__(module)
moduleClass = getattr(sys.modules[module], "Windows")
return moduleClass(username, password, params)
elif re.match("linux", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Linux"
__import__(module)
moduleClass = getattr(sys.modules[module], "Linux")
return moduleClass(username, password, params)
elif re.match("solaris|Sun", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Solaris"
__import__(module)
moduleClass = getattr(sys.modules[module], "Solaris")
return moduleClass(username, password, params)
elif re.match("esx", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Esx"
__import__(module)
moduleClass = getattr(sys.modules[module], "Esx")
return moduleClass(username, password, params)
elif re.match("hyperv", os, re.IGNORECASE):
raise UnImplementedException("HyperV functionality is not completed yet")
elif re.match("aix", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Aix"
__import__(module)
moduleClass = getattr(sys.modules[module], "Aix")
return moduleClass(username, password, params)
elif re.match("hpux", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Hpux"
__import__(module)
moduleClass = getattr(sys.modules[module], "Hpux")
return moduleClass(username, password, params)
elif re.match("Mac", os, re.IGNORECASE):
module = "UniAutos.Device.Host.Mac"
module = __import__(module)
moduleClass = getattr(sys.modules[module], "Mac")
return moduleClass(username, password, params)
elif re.match("OpenStack", os, re.IGNORECASE):
module = "UniAutos.Device.Host.OpenStack"
module = __import__(module)
moduleClass = getattr(sys.modules[module], "OpenStack")
return moduleClass(username, password, params)
else:
raise InvalidParamException("Unrecognized OS parameter: %s \
\nYou can try again by using one of the following values: \
\n - Windows\n - Linux\n - Solaris\n - ESX\n - Hpux\n - Aix\n - Mac\n - OpenStack")
else:
try:
newClass = cls.discoverClass(command)
moduleName = newClass[0: newClass.rfind(".")]
className = newClass[newClass.rfind(".") + 1: len(newClass)]

__import__(moduleName)
moduleClass = getattr(sys.modules[moduleName], className)
obj = moduleClass(username, password, params)
return obj
except UniAutosException, e:
raise e
if "ipv4_address" in params:
ip = params["ipv4_address"]
if "ipv6_address" in params:
ip = params["ipv6_address"]
else:
ip = ''
raise UniAutosException("Command and/or Host discovery failed. "
"Please ensure that:\n- The required Perl modules are installed\n- "
"The target host (%s) has the required services running\n- The "
"target host (%s) is online and ping'able\n- The username/password "
"(%s/%s) are correct\n- If %s is the SP of a OceanStor Block array, "
"that it has the 'RALabHosts' enabler installed and is active "
"(for SSH communication)\n\n%s" % (ip, ip, username, password, ip, discoverErrors))

@classmethod
def discoverClass(cls, command):
"""Query the operating system type according to the Command object, and return the corresponding class name.

Args:
Command : command object instance, depending on the configuration

Returns:
Class name
"""
return cls.__module__ + "." + cls.__name__

@classmethod
def discoverCommandInstance(cls, username, password, params):
"""
Generate a Command object

Args:
Username (str): account name
Password (str): account password
Params (dic): params = {
"port" : (str),
"ipv4_address" : (str),
"ipv6_address" : (str),
"svp" : {},
"command" : cmdobj,
"type" : (str)
}
Params key-value pair description
Type (str): communication protocol, key optional, range of values ​​["storSSH", "standSSH", "local", "telnet", "xmlrpc"]
Port (int): communication port, key optional
Ipv4_address (str): The ipv4 address of the host, the key and ipv6_address must be selected
Ipv6_address (str): The ipv6 address of the host, the key and ipv4_address must be selected
Svp (dict): information needed to pass in svp when creating the controller
Command (cmdobj): The actual connection object used to issue the command

Returns:
Command object

Raises:
DictKeyException
"""
if "command" in params:
return params["command"]
temp = dict()
if 'ipv4_address' in params:
temp['ip'] = params['ipv4_address']
elif 'ipv6_address' in params:
temp['ip'] = params['ipv6_address']
else:
raise DictKeyException('You need to provide an IP address either IPV4 or IPV6')
temp['protocol'] = params.get('type', 'storssh').lower()
for k in ['username', 'password', 'newpassword', 'key', 'docker_ip', 'docker_user', 'docker_password', 'docker_port',
'port', 'max_session', 'debug_username', 'debug_password', 'ssh_private_key', 'ssh_public_key', 'heartbeatIp',
"vrf_inner_flag"]:
v = params.get(k, None)
if v:
temp[k] = v
if "svp" in params:
controlmsg = dict()
svpInfo = params["svp"]
controlmsg['ip'] = temp['ip']
# 实际连接的IP为SVP的IP
if 'ipv4_address' in svpInfo:
temp['ip'] = svpInfo['ipv4_address']
elif 'ipv6_address' in svpInfo:
temp['ip'] = svpInfo['ipv6_address']
else:
raise DictKeyException('You need to provide an svp IP address either IPV4 or IPV6')
temp['controlmsg'] = controlmsg
temp['protocol'] = 'svpstorssh'
if temp['protocol'] == 'nasssh':
temp['backwardip'] = params['detail']['backwardip'].split(',')

return CommandBase.discover(**temp)

def runAsync(self, params):
"""Execute asynchronous commands

Args：
params ({}): params = {
"command" : ["", "", ""],
"waitstr" : "",
"input" : ["", "", ""],
"directory" : "",
"timeout" : 100,
"username" : "",
"password" : ""
}
Specific key-value descriptions in params:
Command (list): The specific command to be executed, such as show lun general packaged into ["show", "lun", "general"]
Input (list): The parameters of the interaction in the execution of the command and the expected result. If there are interactive parameters, the elements of 0, 1 are paired, the elements of 2 and 3 are paired, and so on, where the first element is 0. The expected end character after the parameter is executed, the third element is the expected terminator of the parameter No. 2
Waitstr (str): expected end of the command after execution, default value "[>#]"
Directory (str): specifies the directory where the command is executed
Timeout (int): command execution timeout, default 600S, not very accurate
Username (str): The username to be used when establishing an SSH connection. It will be automatically reconnected when username or passwd appears in the command.
Password (str): The password to be used when establishing an SSH connection. When the username or password appears in the command, it will automatically reconnect.

Returns:
Result: echo information output by the asynchronous command execution

Examples:
result = self.runAsync(params)

"""
result = self.command.asyncCmd(params)
return result
pass

@validateParam(params=dict)
def run(self, params):
"""
Args：
params (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}

params中具体键-值说明：
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
waitstr (str): 命令执行后的期望结束符，默认值"[>#]"
directory (str): 指定命令执行的目录
timeout (int): 命令执行超时时间，默认600S，不会很精确
username (str): 建立SSH连接时需要使用的用户名，当命令中出现username或者password时会自动重新连接
password (str): 建立SSH连接时需要使用的密码，当命令中出现username或者password时会自动重新连接
checkrc (int): 是否检查回显，默认值0，不检查
Returns:
result: 交互式命令的整个执行过程的输出
The output of the entire execution of the interactive command

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {"command": ["sftp", "admin@100.148.115.39"], "waitstr":
"password", "input": ["123456", "[>#]", "ls", "[>#]"],
"directory": "/home/"}
result = self.run(cmdSpec)

"""
workingDir = ''
if 'sessionType' not in params \
and ('UniAutos.Device.Host.Controller' in self.__class__.__module__ or
'UniAutos.Device.Host.IPenclosure' in self.__class__.__module__)\
and 'wrapper' in params:
params['sessionType'] = params["wrapper"].sessionType
sessionType = params.get('sessionType')
#适配版本升级过程中下发命令的需求，目前只涉及admin和developer的命令适配
if hasattr(self.command,'status'):
if self.command.status == "upgrade" and sessionType == "admincli":
params['sessionType'] = "developer"
else:
self.logger.debug("current command is %s" % self.command.version)
productVersion = None

try:
productVersion = self.softVersion
except Exception as e:
self.logger.debug("Current host device has no parameter: productVersion. \n %s" % str(e))

# 根据设置的优先级别，调整命令下发的模式
params = self.selectHighPriorityView(params, productVersion)
new_No_Degrade_Commands = deepcopy(No_Degrade_Commands)

def is_debug_degree(version):
if version is None:
return False
for item in Degrade_Permission_Versions:
if item in version:
return True
return False

if "V100R005C10" == productVersion and self.productModel in Dorado_Model:
if 'sftp' in new_No_Degrade_Commands:
new_No_Degrade_Commands.remove('sftp')
if 'ssh' in new_No_Degrade_Commands:
new_No_Degrade_Commands.remove('ssh')

if sessionType is not None and is_debug_degree(productVersion) and sessionType == 'debug':
if not ("V300R001C00" in productVersion and self.productModel not in Dorado_Model):
prefix = params["command"][0]
match = re.match(r'%s' % '|'.join(new_No_Degrade_Commands), prefix)
if match is None and not 'UniAutos.Device.Host.Controller.DockerControllerHost' in self.__class__.__module__:
params["command"].insert(0, "sudo")
if self.command.defaultConnectInfo.has_key('username'):
if match is None and self.command.defaultConnectInfo["username"] == "ibc_os_hs":
if params["command"][0] != "sudo":
params["command"].insert(0, "sudo")

if "checkrc" not in params:
params["checkrc"] = 0
if "directory" in params:
workingDir = '[WorkDir: ' + params["directory"] + '] '
if "timeout" not in params and self.__timeout is not None:
params['timeout'] = self.__timeout
params['isStop'] = self.__stopOnTimeOut

cmdMsg = "[Host: %s] %s %s" % (self.localIP, workingDir, " ".join(params["command"]))
self.log.trace("Command: " + str(params["command"]))
self.log.cmd(cmdMsg)
#针对AA版本，系统不正常只允许登陆一次，其他直接失败
result = None
if 'UniAutos.Device.Host.Controller' in self.__class__.__module__:
if ("6.0." in productVersion and "D" in self.productModel) \
or self.command.protocol == "emustorssh":
if not self.isDeviceError:
try:
result = self.command.cmd(params)
except UniAutosException as e:
self.logger.warn("determine whether DoradoV6R3C00 or Simulation system is error")
self.logger.warn(e)
if "system is error,login timeout" in e.message:
self.logger.warn("DoradoV6R3C00 or Simulation system is abnore, Terminate excution")
self.isDeviceError = True
else:
result = self.command.cmd(params)
if self.isDeviceError:
raise UniAutosException("DoradoV6R3C00 or Simulation system is error")
else:
result = self.command.cmd(params)
else:
result = self.command.cmd(params)
if result is None:
raise UniAutosException("current cmd:%s is not send" % params["command"])

retMsg = result["stdout"]
if retMsg is None:
retMsg = result["stderr"]
self.log.cmdResponse("[Host: %s]\n%s" % (self.localIP, str(retMsg)))

# For Array Command Retry
def validate_retry(result, count):
# 判断是否需要重试

# 重试的次数已经超过最大重试次数.
if count > self.retry_count:
return False

if 'stdout' in result and result['stdout'] is not None:
__lineForRetry = ''.join(result['stdout'])
else:
return False
# 对应的sessionType中是否存在需要重试的关键字, 如果存在，即重试.
for retry_code in self.retry_codes.get(params.get('sessionType', 'null'), []):
matcher = re.search(r'' + str(retry_code.lower()) + '', __lineForRetry.lower(), re.M)
if matcher:
return True
return False

retry = 1
while validate_retry(result, retry):

# 重试.
self.logger.info('###[UniAutos Retry]:### [Host: %s] %s, Command: %s, Retry Count: %s'
% (self.localIP, workingDir, " ".join(params["command"]), retry))
cmdMsg = "[Host: %s] %s %s" % (self.localIP, workingDir, " ".join(params["command"]))
self.log.trace("Command: " + str(params["command"]))
self.log.cmd(cmdMsg)
result = self.command.cmd(params)
retMsg = result["stdout"]
if retMsg is None:
retMsg = result["stderr"]
self.log.cmdResponse(str(retMsg))
retry += 1
self.logger.info("###[UniAutos Retry]:### Retry interval, wait %sS, Retry command: %s"
% (self.retry_interval, str(params["command"])))
# 等待.
sleep(self.retry_interval)

if params['checkrc'] == 1:
if (result["rc"] is not None and result["rc"] != 0) or result["rc"] or result['stderr']:
msg = 'Failed to execute the command ' + str(params["command"])
msg = msg + "\nResult of the wrapper call:\n" + getFormatString(result)
raise CommandException(msg, result)

return result

@classmethod
def setLocalHostIP(cls, params):
"""设置一个本地IP

Args：
params ({}): params = {
"type" : "",
"ipv4_address" : "",
"ipv6_address" : ""
}
params中具体键-值说明：
type (str): "local"
ipv4_address (str): 可以是具体的IP地址，或者localhost
ipv6_address (str): 可以是具体的IP地址，或者localhost

Examples:
HostBase.setLocalHostIP(params)

"""
if "type" in params and re.match("local", params["type"], re.IGNORECASE):
if "ipv4_address" not in params:
params["ipv4_address"] = "127.0.0.1"
if "ipv6_address" not in params:
params["ipv6_address"] = "::1"
# 心跳控制器传递的"ipv4_address"是一个列表, 这里暂不作处理
if "ipv4_address" in params and isinstance(params["ipv4_address"], list):
return
if "ipv4_address" in params and re.match("^localhost$", params["ipv4_address"], re.IGNORECASE):
params["ipv4_address"] = '127.0.0.1'
if "ipv6_address" in params and re.match("^localhost$", params["ipv6_address"], re.IGNORECASE):
params["ipv6_address"] = '::1'

def getCmdObj(self):
"""返回下发命令的对象

Returns:
具体可以下发命令的对象
"""
return self.command

def setCmdObj(self, cmdObject):
"""设置命令下发对象

Args：
cmdObject (object): 已经完成连接的命令对象

"""
self.command = cmdObject

def runToolWrapperMethod(self, params):
"""执行wrapper

Args：
params (dict): params = {
"wrapper" : "",
"method" : "",
"params" : "",
"directory" : "",
"run_async" : "",
"run_async_background" : "",
"retry_settings" : ""
}
params中具体键-值说明：
wrapper (object): wrapper对象
method (str): 具体的wrapper方法
params (dict): 测试脚本中传入的测试参数
directory (str): 命令执行的目录
run_async (int): 设置是否异步运行，默认值0不异步运行
run_async_background (int): 设置是否后台运行，默认值0不后台运行
retry_settings (dict): 一个hash，默认值{multiplier => 1}
Returns:
命令执行完成之后回显以及回显的解析结果

Raises:
CommandException
InvalidParamException

Examples:
result = self.runToolWrapperMethod(params)

"""
# template = {"wrapper": {"types": ToolBase, "optional": False},
# "method": {"types": str, "optional": False},
# "params": {"types": dict, "optional": False},
# "directory": {"types": str, "optional": True},
# "environment": {"types": dict, "optional": True},
# "run_async": {"types": bool, "optional": True},
# "run_async_background": {"types": bool, "optional": True},
# "retry_settings": {"types": dict, "optional": True},
# }
# validateDict(params, template)
wrapper = params["wrapper"]
method = params["method"]
twParams = params["params"]

result = []
can = wrapper.can(method)
if can == None:
raise CommandException("Invalid method name '%s' specified for wrapper '%s'" % (method, wrapper))

cmds = self.activateCan(can, wrapper, twParams)

if wrapper.can('generateNegativeCli'):
tempCmds = cmds
cmds = wrapper.generateNegativeCli(positive_cmd=tempCmds)

def validateFunc(info):
"""命令回显校验方法
Args:
info (dict): 包含回显的命令执行结果.

Returns:
True|False 成功为True，失败为False.
"""
lineRaw = info["stdout"]

# 如果当前设备设置了ignore_codes, For ##Retry Frame##
__lineForIgnore = ''.join(lineRaw)
sessionType = wrapper.sessionType if hasattr(wrapper, 'sessionType') else 'null'

# 首先判断wrapper_ignores中是否有指定对应的wrapper method忽略指定的关键字.
for ignore_code in self.wrapper_ignores.iterkeys():
if method in self.wrapper_ignores[ignore_code]:
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for ignore_code in self.ignore_codes.get(sessionType, []):
# 如果ignore_code在wrapper_ignores中出现过，则以wrapper_ignores为判断依据，这里不再继续处理.
if ignore_code in self.wrapper_ignores.iterkeys():
continue
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for line in lineRaw:
# As match followed situation, will return false:
# "^\n" : Wrong command string
# "Error:" : Execution Error
# "Get www failed:sdId" : wwn Error
# "Command failed" : Command execute failed
# "command not found" : command not found situation
# "Try 'help' for more information" : Catch help hint situation
matcher = re.search(
"\^(\n|\n\r|\r)?|Get wwn failed:sdId|Error:|Command failed|command not found|Try \'help\' for more information",
line,
re.IGNORECASE)
if matcher:
return False
return True

for cmd in cmds:
args = cmd
cmdInfo = cmd
if "partial" not in cmdInfo:
cmdInfo["partial"] = 0
if "validation" not in cmdInfo:
cmdInfo["validation"] = validateFunc
if "negative_cli" not in cmdInfo:
cmdInfo["negative_cli"] = 0
if "split_output" not in cmdInfo:
cmdInfo["split_output"] = 1
if "setup" in cmdInfo:
cmdInfo = cmd["setup"](host_object=self, cmd_info=cmdInfo)
runParams = {"command": cmdInfo["cmdline"]}
if "viewManagerParams" in cmdInfo:
runParams["view_params"] = cmdInfo["viewManagerParams"]
if "waitstr" in cmdInfo:
runParams["waitstr"] = cmdInfo["waitstr"]
if "cliUserInfo" in cmdInfo:
runParams['cliUserInfo'] = cmdInfo['cliUserInfo']
if "input" in cmdInfo:
runParams["input"] = cmdInfo["input"]
if "timeout" in cmdInfo:
runParams["timeout"] = cmdInfo["timeout"]
if "confirm" in cmdInfo:
runParams["confirm"] = cmdInfo["confirm"]
if "isauto" in cmdInfo:
runParams["isauto"] = cmdInfo["isauto"]
if "ssh_input_delay" in cmdInfo:
runParams["ssh_input_delay"] = cmdInfo["ssh_input_delay"]
if "ssh_create_pty" in cmdInfo and cmdInfo["ssh_create_pty"]:
runParams["ssh_create_pty"] = cmdInfo["ssh_create_pty"]
if "recv_return" in cmdInfo:
runParams["recv_return"] = cmdInfo["recv_return"]
if "ignore_error" in cmdInfo:
runParams["ignore_error"] = cmdInfo["ignore_error"]
if "directory" in params:
runParams["directory"] = params["directory"]
if "environment" in params:
runParams["environment"] = params["environment"]
if "run_async" in params and params["run_async"]:
if "run_async_background" in params and params["run_async_background"]:
runParams["background"] = 1
return self.runAsync(runParams)

def tmpmethod(param):
return 0

retry = {"criteria": tmpmethod,
"user_criteria": tmpmethod,
"interval": '1s',
"retry_codes": {},
"count": 0}
if "retry" in cmdInfo:
retry = cmdInfo["retry"]
elif hasattr(wrapper, "retry"):
retry = wrapper.retry
if "retry_settings" in params:
dispatcherRetrySettings = params["retry_settings"]
if "count" in dispatcherRetrySettings:
retry["count"] = dispatcherRetrySettings["count"]
if "interval" in dispatcherRetrySettings:
retry["interval"] = dispatcherRetrySettings["interval"]
if "retry_codes" in dispatcherRetrySettings:
retry["retry_codes"] = dispatcherRetrySettings["retry_codes"]
for wp in retry["retry_codes"]:
if re.match(wp, wrapper.__name__, re.IGNORECASE):
wrapper.setRetry(user_retry_codes=retry["retry_codes"][wp])
break
else:
wrapper.restoreRetry()
deadCheck = None
if "dead_check" in cmdInfo:
deadCheck = cmdInfo["dead_check"]
if "count" not in retry or retry["count"] < 0:
raise InvalidParamException("Retry count must be an integer >= 0.")
exception = {"command": cmdInfo["cmdline"]}
info = {}
tries = 0
while tries = 0:
tmp = path.split(os.altsep)
else:
tmp = path.split(os.sep)

result = [tmp.pop(0)]
filename = tmp.pop(len(tmp) - 1)
result.append(os.sep.join(tmp))
result.append(filename)
return result

def getFile(self, params):
"""文件下载

Args:
params (dict): {"source_file" : "",
"destination_file" : ""}
destination_file是可选的
"""
if "destination_file" not in params:
filestructure = self.splitpath(params["source_file"])
params["destination_file"] = filestructure[2]
cmdObj = self.getCmdObj()
self.log.trace("Beginning to retrieve the file %s from the host %s" % (params["source_file"], self.localIP))
cmdObj.getFile(params["source_file"], params["destination_file"])
self.log.trace('File transfer complete')
if not os.path.exists(params["destination_file"]):
raise UniAutosException("Failed to get file %s from host" % params["source_file"])

def putFile(self, params):
"""文件上传

Args:
params (dict): {"source_file" : "",
"destination_file" : ""}
destination_file是可选的
"""
if "destination_file" not in params:
filestructure = self.splitpath(params["source_file"])
params["destination_file"] = self.getPath() + os.sep + filestructure[2]
self.log.trace("Beginning to send the file %s to the host %s." % (params["source_file"], self.localIP))

cmdObj = self.getCmdObj()
if params.get('viewMap'):
cmdObj = self.getCmdObj().getConnection(view=params['viewMap'])
try:
cmdObj.putFile(params["source_file"], params["destination_file"])
self.log.trace('File transfer complete')
finally:
if params.get('viewMap'):
self.getCmdObj().connectionPool[cmdObj.username].put(cmdObj)
self.logger.debug("Thead %s get connection, user name: %s" % (threading.currentThread().ident, cmdObj.username))
if not self.doesPathExist({"path": params["destination_file"]}):
raise UniAutosException("Failed to put file %s to host" % params["source_file"])


def reboot(self, delay=None, wait=None, timeout=None):
"""重启主机
Args:

delay (int) : (可选参数)time to delay before reboot. Default: '5', units: "S"

wait (boolean) : (可选参数)boolean. If set to true, method blocks (via
until the host is back up and capable of communication. Default: False

timeout (int) : (可选参数) time to wait for the host to be back up. Uses 's
default if no value is given, depends on parameter "wait".
"""
raise UnImplementedException("HostBase's reboot method is not implements.")

def waitForPing(self, timeout=2400):
"""等待主机能够ping通

Args:
timeout (int): 等待时间，单位为S， 默认2400.

Raises:
UniAutosException : host can not reachable .

"""

waitUntil = time() + timeout
while time() < waitUntil:
if self.isReachable():
return
sleep(10)
raise UniAutosException('Host did not ping in %s secs!' % timeout)

def isReachable(self, pingTimeout=None):
"""Checks to see if we can reach remote host

Returns:
True|False: True- able to reach.
False- unable to reach

"""
if quiet_ping(self.information["ipv4_address"], timeout = pingTimeout):
self.log.debug("host %s is reachable" % self.localIP)
return True
self.log.debug("host %s is not reachable" % self.localIP)
return False

def isUnix(self):
"""Checks to see host is Unix or not.

Returns:
True|False: True- is Unix.
False- is not Unix
"""
from UniAutos.Device.Host.Unix import Unix

if isinstance(self, Unix):
return 1
return 0

def isWindows(self):
"""Checks to see host is windows or not.

Returns:
True|False: True- is Windows.
False- is not Windows

"""
from UniAutos.Device.Host.Windows import Windows

if isinstance(self, Windows):
return 1
return 0

def isController(self):
"""Checks to see host is Controller or not.

Returns:
True|False: True- is Windows.
False- is not Windows

"""
from UniAutos.Device.Host.Controller.ControllerBase import ControllerBase

if isinstance(self, ControllerBase):
return 1
return 0

@repeat_timeout('[check ip is reachable ]')
def wait_host_reachable(self,dest_addr, timeout=None, count=4, psize=64):
'''
循环等待主机网络可通
:param dest_addr:目标地址
:param timeout:每次ping的超时时间，默认1S
:param count:
:param psize:
:return:
'''
return [quiet_ping(dest_addr, timeout=None, count=4, psize=64)]

def canCommunicate(self):
"""Checks to see if we can communicate with remote host by attempting to
send a test command

Returns:
True|False: True- Able to communicate
False- Unable to communicate
"""
if hasattr(self, "command") and self.getCmdObj():
if self.isWindows():
try:
response = self.run({"command": ['cmd', '/c', 'exit'], "timeout": 60})
except Exception:
self.log.debug("Cannot communicate with this host")
return False
if response:
return True

elif self.isUnix():
try:
response = self.run({"command": ['sh', '-c', 'uname'], "timeout": 60})
except Exception:
self.log.debug("Cannot communicate with this host")
return False
if response:
return True

@classmethod
def trim(cls, trimStr):
"""去掉字符串中的头尾的空白字符

Args：
trimStr (str): string to be trimmed.

Returns:
trimStr (str): undef if trimmed word equals ""; otherwise, returns trimmed word.
"""
return re.sub(r'^\s+|\s+$', "", trimStr)

@classmethod
def normalizeWwn(cls, wwn):
"""Normalize the WWN.
It formats the WWN like '0x50060b000069b1d9' or '50060b000069b1d9' to '50:06:0b:00:00:69:b1:d9'.

Args:
wwn (str): wwn like: "0x50060b000069b1d9".

Returns:
wwn (str): wwn like: "50:06:0b:00:00:69:b1:d9"

"""
wwn = re.sub(r'0x', "", wwn)
wwn = re.sub(r'(\w{2})', r'\1:', wwn)
wwn = re.sub(r':$', "", wwn)
return wwn

def waitForReboot(self, waitForShutdown=True, timeout=3600):
"""Waits for host to come back from a reboot

Args:
waitForShutDown (Boolean): (Optional) Set to true to wait for the Host to shutdown first. (Default = True).
timeout (int) : (Optional) Amount of time to wait for reboot, unit is "S"
(Default: 3600).

"""
self.log.debug("Waiting for the host %s to finish rebooting" % self.localIP)
endTime = time() + timeout

# If specified, wait for the system to shutdown
if waitForShutdown:
self.log.debug("Waiting for the host %s to complete shutdown" % self.localIP)
self.waitForShutdown(timeout=timeout)
self.log.debug("Host %s is shutdown" % self.localIP)

self.log.debug("Waiting for the host %s to come up" % self.localIP)
while not self.isReachable() or not self.canCommunicate():
sleep(10)
if time() > endTime:
raise UniAutosException("Timed out waiting for reboot [ip: %s]"
"\n(Timed out while waiting for the system to come up" % self.localIP)
pass

def waitForShutdown(self, timeout=600, shutDownTimes=1, pingTimeout=None):
"""Waits for host to shutdown

Args:
timeout (int): (Optional) Amount of time to wait for shutdown , unit is "S".
(Default: 600).

Raises:
UniAutosException: shutdown timeout.

"""

endTime = time() + timeout
# Wait for (or check that) the system is down
# isReachable() just sends pings to the system rather than commands
# which is better suited to letting it shut down without interruption

shutDownTimes = shutDownTimes
index = 0

while time() < endTime:
pingFlag = True if self.isReachable(pingTimeout) else False

if pingFlag:
index = 0
else:
index += 1

if index >= shutDownTimes:
self.logger.info("The controller host cannot be reachable for four seconds.")
break

sleep(2)

if index < shutDownTimes:
raise UniAutosException("Timed out waiting for reboot [ip: %s] "
"\n(Timed out while waiting for the system to go down" % self.localIP)

def _setArchitecture(self, arch):
"""Set the architecture on the host。

Args:
arch （str）: The architecture string(x86 i686 etc.)

"""
self.architecture = arch
pass

def getMonitorProgress(self):
"""Get the running processes on this host to which need monitor memory usage.
Returns:
self.monitorProgress
"""
return self.monitorProgress

def catDir(self, baseDir, *args):
"""将base dir与 一个或多个字符串组成一个目录并返回

Args:
baseDir (str): 基础目录，Windows下baseDir如果是盘符需要在结尾输入输入"\\"，如："C:\\".
args (str): 一个或多个字符串.

Returns:
dirPath (str): baseDir和args组成的目录字符串.

Examples:
path = hostObject.catDir("c:\\", "Eclipse", "UniAutos")
>>"c:\Eclipse\UniAutos"
path = hostObject.catDir("/root", "Eclipse", "UniAutos")
>>"/root/Eclipse/UniAutos"
path = hostObject.catDir(os.path.realpath(__file__), "Eclipse", "UniAutos")
>>"D:\Download\UniAutos\Eclipse\UniAutos"

"""
baseDir = re.sub(r'(/|\\)$', "", baseDir)

tmpDir = [baseDir]
tmpDir.extend(args)
if self.isUnix() or self.isController():
return '/'.join(tmpDir)
elif self.isWindows():
return '\\'.join(tmpDir)

def catPath(self, baseDir, fileName):
"""将base dir与 一个或多个字符串组成一个目录并返回

Args:
baseDir (str): 基础目录，Windows下baseDir如果是盘符需要在结尾输入输入"\\"，如："C:\\".
fileName (str): 文件名.

Returns:
filePath (str): baseDir、args、fileName组成的目录字符串.

Raises:
None.

Examples:
path = hostObject.catPath("c:\\Eclipse\\UniAutos", "test.py")
>>"C:\Eclipse\UniAutos\test.py"
path = hostObject.catDir("/root/Eclipse/UniAUtos", "test.py")
>>"/root/Eclipse/UniAutos/test.py"

"""
baseDir = re.sub(r'(/|\\)$', "", baseDir)
if self.isUnix():
return '/'.join([baseDir, fileName])
elif self.isWindows():
return '\\'.join([baseDir, fileName])

def markCmdObjDirty(self):
"""标记CmdObj对象为dirty状态

"""
self.getCmdObj().markDirty()

def sendSerial(self, mode, user, pwd, cmd, *args, **kwargs):
"""往串口发送cmd
"""
raise UnImplementedException("HostBase's sendSerial method is not implements.")

def getControllerIOTool(self, id, toolName):
"""获取在阵列测的上的IO工具, 一个控制器上一个工具

Args:
toolName(str): 工具名称
id(str): 获取相应的控制器上的工具
Returns:
toolObj(obj): 返回工具的对象

"""
if id not in self.controllerIoTool:
self.controllerIoTool[id] = {}

if toolName not in self.controllerIoTool[id]:
if toolName == 'doradoio':
from UniAutos.Io.DoradoIo import DoradoIo
toolObj = DoradoIo(self)
self.controllerIoTool[id][toolName] = toolObj
elif toolName == 'fdsatesttool':
from UniAutos.Util.FdsaTestTool import FdsaTestTool
toolObj = FdsaTestTool(self)
self.controllerIoTool[id][toolName] = toolObj
else:
raise UniAutosException('unkown io tool name %s'%toolName)

obj = self.controllerIoTool[id][toolName]
return obj

def getIOTool(self, toolName):
"""获取在主机的上的IO工具

Args:
toolName(str): 工具名称

Returns:
toolObj(obj): 返回工具的对象

"""

def getToolObj(tool):
if self.ioTool[tool] == None:
if tool == 'vdbench':
from UniAutos.Io.File.Vdbench import Vdbench
toolObj = Vdbench(self)

elif tool == 'sdtester':
from UniAutos.Io.Block.SdTester import SdTester
toolObj = SdTester(self)

elif tool == 'unifsio':
from UniAutos.Io.File.UniFsIo import UniFsIo
toolObj = UniFsIo(self)

elif tool == 'uniblkio':
from UniAutos.Io.Block.UniBlkIo import UniBlkIo
toolObj = UniBlkIo(self)

elif tool == 'xcloud':
from UniAutos.Io.File.Xcloud import Xcloud
toolObj = Xcloud(self)

elif tool == 'doradoio':
from UniAutos.Io.DoradoIo import DoradoIo
toolObj = DoradoIo(self)

elif tool == 'unmapbatch':
from UniAutos.Io.UnmapBatch import UnmapBatch
toolObj = UnmapBatch(self)

elif tool == 'unifilestressor':
from UniAutos.Io.File.UniFileStressor import UniFileStressor
toolObj = UniFileStressor(self)

elif tool == 'scsiio':
from UniAutos.Io.Block.ScsiIo import ScsiIo
toolObj = ScsiIo(self)
elif tool == 'iometer':
from UniAutos.Io.iometer import Iometer
toolObj = Iometer(self)
elif tool == 'dynamo':
from UniAutos.Io.iometer import Dynamo
toolObj = Dynamo(self)
elif tool == 'simul':
from UniAutos.Io.File.Simul import Simul
toolObj = Simul(self)

self.ioTool[tool] = toolObj

else:
toolObj = self.ioTool[tool]

return toolObj

tool = None
toolName = toolName.lower()
if toolName not in list(self.ioTool):
raise CommandException("unkown IO tool in host.")

try:
ginitToolsLock.acquire()
tool = getToolObj(toolName)
finally:
ginitToolsLock.release()

return tool

def wipeIoTools(self, toolName):
"""释放在主机的上的IO工具

Args:
toolName(str): 工具名称

Returns:
toolObj(obj): 返回工具的对象

"""

def checkSdRuningStatus():
cmd = {"command": ['sh', '-c', 'ps', '-A', '|grep', 'sdtester']}
result = self.run(cmd)
if result['stdout']:
return True
else:
return False

if toolName not in list(self.ioTool):
raise CommandException("unkown IO tool in host.")

if toolName == 'sdtester' and self.ioTool[toolName] is not None:
if checkSdRuningStatus():
self.ioTool[toolName].stopIO()
self.ioTool[toolName].quitSdtester()

try:
gCommandLogLock.acquire()
self.ioTool[toolName] = None
finally:
gCommandLogLock.release()

def disConnect(self, username=None):
"""断开当期主机对象的某个用户的登陆.
Args:
username (str): 需要退出登陆的用户名.
Examples:
host.disConnect('admin')
"""
if not username:
username = self.username

connPool = self.getCmdObj()
conn = connPool.getConnection(username=username)
conn.close()

def getPathAndFile (self, path):
"""获取路径中的文件
Args:
path (str): 路径名称

Examples:
host.getPathAndFile('/opt/test/file')
host.getPathAndFile('C:\\test')
"""

def splitdrive(p):
if len(p) > 1:
normp = p.replace('/', os.sep)
if (normp[0:2] == os.sep*2) and (normp[2:3] != os.sep):
index = normp.find(os.sep, 2)
if index == -1:
return '', p
index2 = normp.find(os.sep, index + 1)
if index2 == index + 1:
return '', p
if index2 == -1:
index2 = len(p)
return p[:index2], p[index2:]
if normp[1] == ':':
return p[:2], p[2:]
return '', p

d, p = splitdrive(path)
i = len(p)
while i and p[i-1] not in '/\\':
i = i - 1
head, tail = p[:i], p[i:]
head2 = head
while head2 and head2[-1] in '/\\':
head2 = head2[:-1]
head = head2 or head

return d + head, tail

@validateParam(params=dict)
def runSQL(self, params):
"""主机上执行SQL命令。added by wangaiguo
Args：
params (dict): cmdSpec = {
"command" : ["","",""],
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : "",
"dbUser" : "dbUser",
"dbPasswd" : "dbPassword"
}

params中具体键-值说明：
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
waitstr (str): 命令执行后的期望结束符，默认值"[>#]"
directory (str): 指定命令执行的目录
timeout (int): 命令执行超时时间，默认600S，不会很精确
username (str): 建立SSH连接时需要使用的用户名，当命令中出现username或者password时会自动重新连接
password (str): 建立SSH连接时需要使用的密码，当命令中出现username或者password时会自动重新连接
checkrc (int): 是否检查回显，默认值0，不检查
dbUser (str): 链接数据库的用户，默认为sysdba；可以在测试床中配置或用户指定
dbPasswd （str): 链接数据库用户对应的密码；可以在测试床中配置或用户指定
Returns:
result: 交互式命令的整个执行过程的输出

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {
"command": ["ifconfig"],
"directory": "",
"timeout": 600,
"username": "oracle",
"password": "Huawei@123",
}
result = self.runSQL(cmdSpec)

"""
# 默认SQL链接参数，使用oracle主机用户和sysdba数据库用户建立链接
connectionParams = {"username": self.username,
"password": self.password,
"dbUser": "sysdba",
"dbPassword": None,
"directory": None
}

# 优先从测试床中取SQL链接的参数
if self.detail.has_key("dbUser"):
connectionParams["dbUser"] = self.detail["dbUser"]
if self.detail.has_key("dbPassword"):
connectionParams["dbPassword"] = self.detail["dbPassword"]

# 如果用户下发命令传入SQL链接参数，则覆盖测试床中的参数
if params.has_key("username"):
connectionParams["username"] = params["username"]
if params.has_key("password"):
connectionParams["password"] = params["password"]
if params.has_key("dbUser"):
connectionParams["dbUser"] = params["dbUser"]
if params.has_key("dbPassword"):
connectionParams["dbPassword"] = params["dbPassword"]
if params.has_key("directory"):
connectionParams["directory"] = params["directory"]

# 建立SQL链接
sql = SQLConnection(self.localIP, connectionParams["username"], connectionParams["password"],
connectionParams["dbUser"], connectionParams["dbPassword"], connectionParams["directory"])

result = sql.cmd(params)

cmdMsg = "[Host: %s] %s %s %s" % \
(self.localIP, connectionParams["username"], connectionParams["dbUser"], " ".join(params["command"]))
self.log.trace("Command: " + str(params["command"]))
self.log.cmd(cmdMsg)

self.log.cmdResponse(str(result["stdout"]))
return result