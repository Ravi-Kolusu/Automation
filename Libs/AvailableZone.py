
# -*- coding: UTF-8 -*-

"""
功 能: AvailableZone类, 提供AvailableZone相关接口.
"""

import re

from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Device.Storage.Fusion.FusionStorageNode import FusionStorageNode
from UniAutos.Dispatcher import Dispatcher
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.TypeCheck import validateParam


class AvailableZone(DeviceBase, Dispatcher):
"""Region类

提供Region接口

Args:
fusionStorageNodes (dict): key为fusionStorageNode对象id, value为fusionStorageNode对象的字典

Attributes:
self.fusion_storage_nodes (dict): 归属于此AvailableZone的fusion_storage_nodes

Returns:
AvailableZone (instance): AvailableZone对象实例.

"""

@validateParam(fusionStorageNodes=dict)
def __init__(self, fusionStorageNodes):
super(AvailableZone, self).__init__()
if fusionStorageNodes:
self.fusion_storage_nodes = fusionStorageNodes
for identity in self.fusion_storage_nodes:
self.fusion_storage_nodes[identity].setAvailableZone(self)
else:
raise UniAutosException('availableZones must be specifed and can not be empty.')

map(lambda x: self.markDirty(x), self.classDict.values())
self.__current_node = None
self.__region = None
self.setCurrentNode(self.fusion_storage_nodes.values()[0])

def setRegion(self, available_zone):
"""获取当前节点归属的Region对象"""
self.__region = available_zone

def getRegion(self):
"""设置当前节点归属的Region对象"""
return self.__region

def dispatch(self, methodName, params={}, interactRule=None, option=None):
"""下发命令

Args:
methodName (str): 命令名称
params (dict): 命令所需参数
interactRule (dict): 交互输入。如过匹配到字典的key值，就输入字典的value
option (dict): 命令收发控制参数，控制命令超时时间，sessionType等
Returns:
dict: 命令执行结果

"""
return self.__current_node.dispatch(methodName, params, interactRule, option)

@validateParam(node=FusionStorageNode)
def setCurrentNode(self, node):
"""设置当前做操作的FusionStorageNode
"""
self.__current_node = node

def getPrimaryNode(self):
"""获取当前做操作的FusionStorageNode
"""
return self.__current_node

def getFusionStorageNode(self, identity=None):
"""获取指定的节点对象

Args:
identity (str) : 节点的ID

Returns:
FusionStorageNode obj
Raise:
CommandException: 查询失败

Example:
node = self.getFusionStorageNode()

"""
# 如果存在identity就返回指定的fusionstorageNode,否则返回所有的fusionstorageNode对象
return self.fusion_storage_nodes[identity] if identity else self.fusion_storage_nodes.values()

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
return self.__current_node.getPlogManagerMasterInfo(deploy)

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
tmp = self.__current_node._insight(nodeType='0', destId=identity, destIp=ip, destPort=port, destMid=mid,
commandType=commandType)
if not tmp['stderr'] and tmp['stdout']:
tmp['stdout'] = tmp['stdout'].lower()
if 'slave' in tmp['stdout']:
return 'slave'
elif 'master' in tmp['stdout']:
return 'master'
else:
self.logger.warn('Failed to get the role of node:[%s].' % ip)

info = self.__current_node._insight(
nodeType='0',
destId=destId if destId else info['identity'],
destIp=destIp if destIp else info['ip'],
destPort=destPort if destPort else info['port'],
destMid=destMid,
commandType=commandType
)
result = {}
if not info['stderr'] and info['stdout']:
info = self.__current_node.split(info['stdout'])
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
self.node_info = result
return result
else:
raise CommandException('Failed to get all the plog manager nodes info.')

def syncClassDispatch(self, componentClass, criteriaDict=None, syncParamsDict=None, device=None, ):
"""使用Tool Wrappers同步更新这个类别里面所有对象实例的properties

Args:
componentClass (str) : Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
criteriaDict (dict): 根据同步的对象属性Dict和过滤的Dict进行匹配
syncParamsDict (dict): 需要同步的参数属性Dict
device(UniAUtos.Device): UniAutos Device 对象

Returns:
returnDict(Dict): 获得相应的Wrapper对象

Raises:
UniAutos.Exception.UniAutosException

"""
return self.getPrimaryNode().syncClassDispatch(componentClass, criteriaDict, syncParamsDict, device)
