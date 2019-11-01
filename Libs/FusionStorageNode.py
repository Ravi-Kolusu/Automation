
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能: FusionStorage类
版权信息: 华为技术有限公司, 版本所有(C) 2014-2015
"""

import re
import time
from copy import deepcopy

from UniAutos.Device.Host.Linux import Linux
from UniAutos.Device.Host.NasNode.OceanStor import OceanStor
from UniAutos import Log
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Util.Ping import quiet_ping

log = Log.getLogger(__name__)

class FusionStorageNode(OceanStor, Linux):
"""FusionStorage初始化

功能说明: FusionStorage初始化

Args:
username (str) : 与FusionStorage连接时需要使用的用户名
password (str) : 与FusionStorage连接时需要使用的密码
params (dict) : params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"type": (str)
}
params键值对说明
protocol (str): 通信协议, key可选, 取值范围：["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口, key可选
ipv4_address (str): 主机的ipv4地址, key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址, key与ipv4_address必选其一
type (str): 连接的类型
Returns:
返回FusionStorage实例

Examples:
node = OceanStor.discover(params)

"""

def __init__(self, username, password, params):
super(FusionStorageNode, self).__init__(username, password, params)
self.nodeId = params.get('id')
if self.detail:
self.rack_id = self.detail.get('rack_id')
self.tools_path = self.detail.get('tools_path', '')
self.ipmi_ip = self.detail.get('ipmi_ip')
self.rawService = re.split('\s*,\s*', self.detail.get('service', ''))
self.storage_disk_type = self.detail.get('storage_disk_type', '')
self.zk_type = self.detail.get('zk_type', '')
self.cache_type = self.detail.get('cache_type', '')
self.ipmi_username = self.detail.get('ipmi_username', '')
self.ipmi_password = self.detail.get('ipmi_password', '')
self.float_ip = self.detail.get('float_ip', '')
self.__available_zone = None

def setAvailableZone(self, available_zone):
"""获取当前节点归属的AvailableZone对象"""
self.__available_zone = available_zone

def getAvailableZone(self):
"""设置当前节点归属的AvailableZone对象"""
return self.__available_zone

@classmethod
def discover(cls, params):
"""获取FusionStorage对象

Args：
params (dict): params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"type": (str)
}
params键值对说明:
protocol (str): 通信协议, key可选, 取值范围["standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口, key可选
ipv4_address (str): 主机的ipv4地址, key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址, key与ipv4_address必选其一
type (str): 连接的类型

Returns:
obj控制器对象

Raises:
None

Examples:
controller = OceanStor.discover(params)

Changes:
None

"""
wrappers = []
if 'tool_wrappers' in params:
wrappers = params.pop("tool_wrappers")

obj = super(FusionStorageNode, cls).discover(params)
obj.wrapper_list = wrappers
obj.original_wrapper_list = wrappers
return obj

@classmethod
def discoverClass(cls, command):
"""根据Command对象查询操作系统类型, 返回对应类名

Args:
command : command对象实例, 根据配置不同而不同

Returns:
class名

"""
return cls.__module__ + "." + cls.__name__

def _insight(self, nodeType, destId, destIp, destPort, destMid, commandType, parameter=None, timeout=None,
useDIcmd=None):
"""在FusionStorageNode系统中, 可维测工具(FusionStorageNode Insight)实现

Args:
nodeType (str): FusionStorage系统中, 用来标识节点类型. 具体取值使用dsware_insight -help查看. 该参数为数字
destId (str): 目的节点ID, MDC和VBS,VFS的ID分别通过各自的配置文件获取；OSD的ID通过查看MDC内集群拓扑,
该参数项为数字
destIp (str): 目的节点的IP地址, MDC与VBS,VFS的IP分别通过各自的配置文件获取；OSD的IP通过查看MDC内集群拓扑获取
该参数项均为数字,以’.’分割
destPort (str): 目的节点的端口号, MDC与VBS,VFS的PORT分别通过各自的配置文件获取；
OSD的PORT通过查看MDC内集群拓扑获取, CACHE|RSM|OM模块目的端口号是OSD监听端口加3.
该参数为数字.
destMid (str): 目的模块号, 具体取值使用dsware_insight -help查看. 该参数为数字
commandType (str): 命令类型, 每个类型对应一个查询/设置功能
parameter (str): 命令子参数(可选项)
timeout (int): 超时时间

Return:
dict: self.run()返回值
"""
# if self.doesPathExist({'path':'/opt/dsware/IPC_CI/BUILD_ENV/bin'}):
# directory = '/opt/dsware/IPC_CI/BUILD_ENV/bin'
# else:
directory = '/opt/dsware/agent/tool'
if useDIcmd:
cmdSpec = {
'command': ["./dsware_insight_cmd.sh dsware_insight", nodeType, destId, destIp, destPort, destMid,
commandType],
"directory": directory,
"timeout": timeout if timeout else 600
}
else:
cmdSpec = {
'command': ["./dsware_insight", nodeType, destId, destIp, destPort, destMid, commandType],
"directory": directory,
"timeout": timeout if timeout else 60
}
if parameter:
cmdSpec['command'].append(parameter)

result = self.run(cmdSpec)
sure_cmdSpec = {
'command': ["Yes"],
"timeout": timeout if timeout else 60
}
if 'This is a high-risk operation. Are you sure you want to continue? [Yes/No]' in result['stdout']:
result = self.run(sure_cmdSpec)
return result

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

Examples:
None

Changes:
None

"""
return Linux.doesPathExist(self, params)

def getPlogManagerMasterInfo(self, deploy=None):
"""获取plogmanager进程主节点信息

Args:
deploy (str) : deploy 配置文件包含路径的名称

Returns:
result (dict): plogmanager进程主节点信息, result键值对说明:

{
"identity": ,
"ip": ,
"port":
}
identity (str): plogmanager进程主节点id.
ip (str): plogmanager进程主节点ip.
port (str): plogmanager进程主节点port.
Raise:
CommandException: 查询失败

Example:
result = self.getPlogManagerMasterInfo()
Output:{'identity': '1', 'ip': '100.112.112.33', 'port': '6699'}

"""

result = {}

nodes = self.getAvailableZone().getRegion().getFusionStorageNode()

for node in nodes:

filePath = '/opt/dsware/mdc/conf/mdc_conf.cfg'
filePath2 = '/opt/dfv/persistence_layer/mdc/conf/mdc_conf.cfg'

if not quiet_ping(node.localIP) or not node.doesPathExist({'path': filePath}) or not node.doesPathExist({'path': filePath2}):
self.logger.info(
'ping %s timeout or mdc_conf.cfg file does not exist in getPlogManagerMasterInfo Function' % node.localIP)
continue

else:
self.logger.info(
'ping %s timeout or mdc_conf.cfg file does not exist in getPlogManagerMasterInfo Function' % node.localIP)

identity = None
port = None
mdcIP = None


cmdSpec = {'command': ['ps -ef | grep -e dsware_mdc -e plog_manager | egrep -v grep']}
try:
info = node.run(cmdSpec)
if "mdc_conf.cfg" not in str(info['stdout']):
continue

except Exception as e:
self.logger.error(e.message)
continue


ret = node.readFile(filePath='/opt/dsware/mdc/conf/mdc_conf.cfg')

for item in ret:
if re.search('mdc_id=(\d+)', item):
identity = re.search('mdc_id=(\d+)', item).group(1)
if re.search('mdc_port=(\d+)', item):
port = re.search('mdc_port=(\d+)', item).group(1)
if re.search('mdc_ip_2=(\d+)', item):
mdcIP = re.search('mdc_ip_2=(\d+.\d+.\d+.\d+)', item).group(1)

if not identity or not port or not mdcIP:
continue

i = 1
while i #]"
directory (str): 指定命令执行的目录
timeout (int): 命令执行超时时间，默认600S，不会很精确
username (str): 建立SSH连接时需要使用的用户名，当命令中出现username或者password时会自动重新连接
password (str): 建立SSH连接时需要使用的密码，当命令中出现username或者password时会自动重新连接
sessionType (str): 命令下发的视图, 默认为debug, 还可填写 diagnose和admincli
attach (str): 进入diagnose后attach的进程名
checkrc (int): 是否检查回显，默认值0，不检查
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
if 'wrapper' in params:
params['sessionType'] = params["wrapper"].sessionType
return Linux.run(self, params)

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

Examples:
None

"""
syncParams = deepcopy(syncParamsDict)
return Linux.syncClassDispatch(self, componentClass, criteriaDict, syncParams, device)

def getPlogManagerNodesInfo(self, destId=None, destIp=None, destPort=None, destMid='8', commandType='181'):
"""获取plogmanager进程节点信息

Args:
destId (str) : destination id
destPort (str) : destination port
destIp (str) : destination ip

Returns:
result (dict): plogmanager进程主节点信息, result键值对说明:

: {"identity": ,
"ip": ,
"port":
'status': ,
'role': }
identity (str): plogmanager进程节点id.
ip (str): plogmanager进程节点ip.
port (str): plogmanager进程节点port.
status (str): plogmanager进程节点status.
role (str): plogmanager进程节点role.
Raise:
CommandException: 查询失败

Example:
result = self.getPlogManagerMasterInfo()
Output:{
'100.112.112.33': {
'identity': '1', 'ip': '100.112.112.33', 'port': '6699', 'status': '0', 'role': 'master'},
'100.112.112.33': {
'identity': '2', 'ip': '100.112.112.32', 'port': '6699', 'status': '0', 'role': 'slave'}
}

"""
info = None
if not destId or not destIp or not destPort:
info = self.getPlogManagerMasterInfo()

def get_specified_node_role(identity, ip, port, mid='8', commandType='149'):
"""查询节点的角色
"""
tmp = self._insight(nodeType='0', destId=identity, destIp=ip, destPort=port, destMid=mid,
commandType=commandType)
if not tmp['stderr'] and tmp['stdout']:
tmp['stdout'] = tmp['stdout'].lower()
if 'slave' in tmp['stdout']:
return 'slave'
elif 'master' in tmp['stdout']:
return 'master'
else:
self.log.warn('Failed to get the role of node:[%s].' % ip)

info = self._insight(
nodeType='0',
destId=destId if destId else info['identity'],
destIp=destIp if destIp else info['ip'],
destPort=destPort if destPort else info['port'],
destMid=destMid,
commandType=commandType
)
result = {}
if not info['stderr'] and info['stdout']:
info = self.split(info['stdout'])
for line in info:
# 当前行中如果有ip地址，则当前航中有目标节点的id，ip，status等值
if re.search('(\d{1,3}\.){3}\d{1,3}', line):
line = re.split('\s*\|\s*', line)
result[line[2]] = {
'identity': line[1],
'ip': line[2],
'port': line[4],
'status': line[5],
'role': get_specified_node_role(line[1], line[2], line[4])
}

if result:
return result
else:
raise CommandException('Failed to get all the plog manager nodes info.')

def getPlogClientNodesInfo(self, destId=None, destIp=None, destPort=None, destMid='8', commandType='110'):
"""获取plogclientmanager进程节点信息
Args:
destId (str) : destination id
destPort (str) : destination port
destIp (str) : destination ip
destMid (str) : destination mid
commandType (str) : destination type

Returns:
result (dict): plogclientmanager进程主节点信息, result键值对说明:

: {"identity": ,
"ip": ,
"port": ,
"status":
}
identity (str): plogclientmanager进程节点id.
ip (str): plogclientmanager进程节点ip.
port (str): plogclientmanager进程节点port.
status (str): plogclientmanager进程节点status.
Raise:
CommandException: 查询失败

Example:
result = self.getPlogClientNodesInfo()
Output:{
'100.112.112.33': {
'identity': '1', 'ip': '100.112.112.33', 'port': '6699', 'status': '0'},
'100.112.112.33': {
'identity': '2', 'ip': '100.112.112.32', 'port': '6699', 'status': '0'}
}

"""
info = None
if not destId or not destIp or not destPort:
info = self.getPlogManagerMasterInfo()
info = self._insight(
nodeType='0',
destId=destId if destId else info['identity'],
destIp=destIp if destIp else info['ip'],
destPort=destPort if destPort else info['port'],
destMid=destMid,
commandType=commandType,
parameter=" |sed '1d'|sed 's/|/ /g'|tr -s ' '|awk '{print and(0xffff, $2), $0}'"
)
result = {}
if not info['stderr'] and info['stdout']:
info = self.split(info['stdout'])
for line in info:
# 当前行中如果有ip地址，则当前行中有目标节点的id，ip，status等值
if re.search('(\d{1,3}\.){3}\d{1,3}', line):
line = re.split('\s*', line)
result[line[5]] = {
'identity': line[0],
'ip': line[5],
'port': line[6],
'status': line[3]
}
if result:
return result
else:
raise CommandException('Failed to get all the plog client nodes info.')
