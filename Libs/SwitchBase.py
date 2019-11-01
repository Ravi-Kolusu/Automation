
SwitchBase ::

#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：SwitchBase作为UniAutos Switch设备类的抽象类，提供Switch的实例和抽象方法
包含了discover工厂方法、通信链接方法，命令run等方法

版权信息：华为技术有限公司，版本所有(C) 2014-2015

"""
import re
import sys
import thread

from UniAutos.Command import CommandBase
from UniAutos.Command.Connection.TelnetConnection import TelnetConnection
from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Dispatcher import Dispatcher
from UniAutos import Log
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.UnImplementedException import UnImplementedException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.Codec import getFormatString
from UniAutos.Util.Ping import quiet_ping

gCommandLogLock = thread.allocate_lock()

class SwitchBase(DeviceBase, Dispatcher):

"""Switch设备的抽象类，继承于DeviceBase和Dispatcher类

-构造函数参数:
Args:
username (str): Switch交换机的用户名.
password (str): Switch用户名的密码.
params (dict): 其他参数, 如下定义:
params = {"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"type": (str)}
params键值对说明:
port (int): 通信端口，可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
type (str): 连接的类型

Returns:
switchObject (instance): Swtich.

Raises:
None.

Examples:
None.

"""
log = Log.getLogger(__name__)

def __init__(self, username, password, params):
super(SwitchBase, self).__init__()

self.ip = None
if 'ipv4_address' in params and params['ipv4_address'] != '':
self.ip = params['ipv4_address']
elif 'ipv6_address' in params and params['ipv6_address'] != '':
self.ip = params['ipv6_address']

self.ports = []
if "ports" in params:
if not isinstance(params['ports'], list):
self.ports.extend([params["ports"]])
else:
self.ports.extend(params["ports"])


self.deviceId = params.get("device_id", None)
self.username = username
self.password = password
self.protocol = None
if 'type' in params:
self.protocol = params['type']
self.information = params
self.architecture = ''
self.networkInfo = {}
self.model = None
self.manufacturer = None
self.command = params['command']
self.portObjects = []


@classmethod
def discover(cls, params):
"""生成具体的Switch对象

Args:
params (dict): params = {
"type" : (str),
"port" : (str),
"ipv4_address" : (str),
"ipv6_address" : (str),
"model" : (str),
"username" : (str),
"password" : (str),
"manufacturer" : (str),
"ports" : (str)
}
params键值对说明
type (str): 通信协议，key必选，取值范围["storSSH", "standSSH", "local", "telnet", "xmlrpc"]
port (int): 通信端口，key必选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
model (str): 交换机类型
manufacturer (str): 交换机厂商
username (str): 交换机通信账号名
password (str): 交换机通信账号密码
ports (list): 交换机个端口配置信息

Returns:
Switch对象

Raises:
None

Examples:
None

"""
username = params["username"]
password = params["password"]
ip_address = None
if 'ipv4_address' in params and params['ipv4_address'] != '':
ip_address = params['ipv4_address']
elif 'ipv6_address' in params and params['ipv6_address'] != '':
ip_address = params['ipv6_address']
else:
raise UniAutosException("IP address doesn't be specified")

if 'type' in params:
waitstr = None
if 'manufacturer' in params and (params['manufacturer'] == 'HpXin' or 'pdu' in params['manufacturer'].lower()):
waitstr = '\[pdu\]'
params['command'] = CommandBase.discover(protocol=params['type'], ip=ip_address,
username=username, password=password, waitstr=waitstr)
else:
params['command'] = CommandBase.discover(ip=ip_address, username=username, password=password)

obj = None
if str(cls) == str(SwitchBase):
model = params.pop("model")
manufacturer = params.pop("manufacturer")
if re.match("fibreChannel", model, re.IGNORECASE):
if re.match("Brocade", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.FibreChannel.Brocade"
__import__(module)
moduleClass = getattr(sys.modules[module], "Brocade")
obj = moduleClass(username, password, params)
elif re.match("Huawei", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.FibreChannel.Huawei"
__import__(module)
moduleClass = getattr(sys.modules[module], "Huawei")
obj = moduleClass(username, password, params)
elif re.match("Ethernet", model, re.IGNORECASE):
if re.match("Brocade", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.Ethernet.Brocade"
__import__(module)
moduleClass = getattr(sys.modules[module], "Brocade")
obj = moduleClass(username, password, params)
elif re.match("Huawei", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.Ethernet.Huawei"
__import__(module)
moduleClass = getattr(sys.modules[module], "Huawei")
obj = moduleClass(username, password, params)
elif re.match("PowerBox", model, re.IGNORECASE):
if re.match("Raritan", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.PowerBox.Raritan"
__import__(module)
moduleClass = getattr(sys.modules[module], "Raritan")
obj = moduleClass(username, password, params)
if re.match("HpXin", manufacturer, re.IGNORECASE) or re.match("pdu", manufacturer, re.IGNORECASE):
module = "UniAutos.Device.Switch.PowerBox.HpXin"
__import__(module)
moduleClass = getattr(sys.modules[module], "HpXin")
obj = moduleClass(username, password, params)

if obj is None:
raise InvalidParamException("Unrecognized model parameter: %s \
\nYou can try again by using one of the following values: \
\n - PowerBox\n - Ethernet\n - fibreChannel")
else:
return obj

def setCmdObj(self, command):
"""设置命令下发对象

Args：
command (object): 已经完成连接的命令对象

Returns:
None

Raises:
None

Examples:
self.setCmdObj()

"""

self.command = command

def getCmdObj(self):
"""返回下发命令的对象

Args：
None

Returns:
具体可以下发命令的对象

Raises:
None

Examples:
self.getCmdObject()

"""
return self.command

def run(self, params):
"""
Args：
params (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}

params中具体键-值说明：
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
waitstr (str): 命令执行后的期望结束符，默认值"[>#]"
timeout (int): 命令执行超时时间，默认600S，不会很精确
username (str): 建立连接时需要使用的用户名，当命令中出现username或者password时会自动重新连接
password (str): 建立连接时需要使用的密码，当命令中出现username或者password时会自动重新连接
checkrc (int): 是否检查回显，默认值0，不检查
Returns:
result: 交互式命令的整个执行过程的输出

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {"command": ["sftp", "admin@100.148.115.39"], "waitstr":
"password", "input": ["123456", "[>#]", "ls", "[>#]"],
"directory": "/home/"}
result = self.run(cmdSpec)

"""

if "checkrc" not in params:
params["checkrc"] = 0
params['sessionType'] = 'ignore'

cmdMsg = "[Switch: %s] %s" % (self.ip, " ".join(params["command"]))
self.log.trace("Command: " + str(params["command"]))
self.log.cmd(cmdMsg)
if self.command is None:
self.command = self.getCmdObj()
if isinstance(self.command, TelnetConnection):
if not self.command.isActive():
self.command.reconnect()
result = self.command.cmd(params)

if params['checkrc'] == 1:
if (result["rc"] is not None and result["rc"] != 0) or not result["rc"] or not result['stdout']:
msg = 'Failed to execute the command ' + str(params["command"])
msg = msg + "\nResult of the wrapper call:\n" + getFormatString(result)
raise CommandException(msg)

self.log.cmdResponse(str(result["stdout"]))
return result

def runToolWrapperMethod(self, params):
"""执行wrapper

Args：
params (dict): params = {
"wrapper" : "",
"method" : "",
"params" : ""
}
params中具体键-值说明：
wrapper (object): wrapper对象
method (str): 具体的wrapper方法
params (dict): 测试脚本中传入的测试参数
Returns:
命令执行完成之后回显以及回显的解析结果

Raises:
CommandException
InvalidParamException

Examples:
result = self.runToolWrapperMethod(params)

"""

wrapper = params["wrapper"]
method = params["method"]
twParams = params["params"]

result = []
can = wrapper.can(method)
if can == None:
raise CommandException("Invalid method name '%s' specified for wrapper '%s'" % (method, wrapper))

cmds = self.activateCan(can, wrapper, twParams)

def validateFunc(info):
lineRaw = info["stdout"]
for line in lineRaw:
matcher = re.search("failed|Error|command not found|Try \'help\'", line, re.IGNORECASE)
if matcher:
return False
else:
return True

for cmd in cmds:
cmdInfo = cmd
if "validation" not in cmdInfo:
cmdInfo["validation"] = validateFunc
runParams = {"command": cmdInfo["cmdline"]}
if "waitstr" in cmdInfo:
runParams["waitstr"] = cmdInfo["waitstr"]
if "input" in cmdInfo:
runParams["input"] = cmdInfo["input"]

deadCheck = None
if "dead_check" in cmdInfo:
deadCheck = cmdInfo["dead_check"]


runParams["wrapper"] = wrapper
info = self.run(runParams)
if not info:
info = {}
if "stdout" in info and info["stdout"]:
pass
else:
info["stdout"] = []

if "stderr" in info and info["stderr"]:
pass
else:
info["stderr"] = []

if "teardown" in cmdInfo:
cmdInfo["teardown"](host_object=self, cmd_info=cmdInfo)

validationResult = cmdInfo["validation"](info)
if not validationResult:
if deadCheck:
if deadCheck(info):
raise UniAutosException("The requested object was not found on the device.")
msg = "validation result is't passed."
msg += "\n'%s' ran unsuccessfully." % " ".join(runParams["command"])
msg += "\nExit code: %s" % info["rc"]
msg += "\nOutput: %s" % info["stdout"]
msg += "\nError: %s" % info["stderr"]
raise CommandException(msg)

if "parser" in cmdInfo:
args = info["stdout"]
if result and "parser" in result[0]:
args.append(result[0]["parser"])
if re.search("instancemethod", str(type(can))):
info["parser"] = cmdInfo["parser"](args)
else:
info["parser"] = cmdInfo["parser"](wrapper, args)
result.insert(0, info)
return result

def isReachable(self):
"""Checks to see if we can reach the switch

Args:
None.

Returns:
True|False: True- able to reach.
False- unable to reach

Raises:
None.

Examples:
None.
"""
if quiet_ping(self.ip, 3, 3):
self.log.debug("Switch %s is reachable" % self.ip)
return True
self.log.debug("Switch %s is not reachable" % self.ip)
return False

def setupEnableComponents(self):
"""初始化设备允许创建的业务列表

Args:
None

Returns:
None

Raises:
None

Examples:

Changes:
None

"""

self.addType('Port', self.getPortClassStr())

def getPortClassStr(self):
"""返回component类名，子类重写

Args:

Returns:
class名

Raises:
None

Examples:
None

Changes:
None

"""
raise UnImplementedException("Method 'getPortClassStr' must be implemented from %s" % self.__class__)




def getPort(self, **param):
"""获取指定端口对象或对象列表

Args:

当Switch为PowerBox时:
id (str): 工具端口对象ID
group (str): 工具端口对象实际链接的环境位置，可能为框ID
device (str): 工具端口链接的环境对象
attachedType (str): 工具端口链接的对端环境部件类型，可能是'controller', 'enclosure'
attachedId (str): 工具端口链接的对端环境部件ID

当Switch为FibreChannel类型时:
#TODO

当Switch为FibreChannel类型时:
#TODO

当Switch为Pcie时:
id (str): 工具端口对象ID
attachedId (str): 工具端口链接的对端环境部件ID


Returns:
port对象列表

Raises:
UniAutosException: There is no object could meet the specified conditions

Examples:
self.getPort(group='DAE000', device=storage)

Changes:
None

"""
if len(self.portObjects) == 0:
module = self.getPortClassStr()
module = re.sub('\.Port$', '', module)
__import__(module)
moduleClass = getattr(sys.modules[module], "Port")
for port in self.ports:
self.portObjects.append(moduleClass(self, port))

portObj = []
portObj.extend(self.portObjects)
tempParam = {}

if re.match('PowerBox', self.model):
if 'device' in param and param['device']:
tempParam['array_id'] = param['device'].deviceId
if 'id' in param and param['id']:
tempParam['id'] = param['id']
if 'group' in param and param['group']:
tempParam['group'] = param['group']
if 'attachedType' in param and param['attachedType']:
tempParam['attached_type'] = param['attachedType']
if 'attachedId' in param and param['attachedId']:
tempParam['attached_id'] = param['attachedId']

elif re.match('Ethernet', self.model):
#TODO
pass
elif re.match('FibreChannel', self.model):
#TODO
pass

elif re.match('Pcie', self.model):
if 'id' in param and param['id']:
tempParam['id'] = param['id']
if 'attachedId' in param and param['attachedId']:
tempParam['attached_id'] = param['attachedId']
else:
raise UniAutosException("The model dose not supported.\nThe valid value like:\
\n - Ethernet\n - FibreChannel\n - Pcie\n - PowerBox")

for item in tempParam:
for port in self.portObjects:
if port.getProperty(item) != tempParam[item] and port in portObj:
portObj.remove(port)

if len(portObj)==0:
raise UniAutosException("There is no object could meet the specified conditions")

return portObj
