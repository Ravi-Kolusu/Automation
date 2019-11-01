
#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 提供海量存储设备对象的封装
"""
import os
from UniAutos.Device.Storage.StorageBase import StorageBase
from UniAutos import Log
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Component.Directory.Huawei.OceanStor import Directory
from UniAutos.Component.DirectoryShare.Huawei.DirectoryCifsShare import DirectoryCifsShare

import sys

class NasCluster(StorageBase):
"""海量存储设备

Args:
**kwargs (dict): 可变参数，用于初始化
kwargs字典中可以包含一下key:
hosts (list): 与阵列相连的主机对象列表
resource (UniAutos.Resource): Resource对象
raw_resource_data(dict): 单个NAS集群设备在测试床中配置的原始数据字典
username (str): 连接NAS集群节点使用的用户名
password (str): 连接NAS集群使用的密码
ipv4_address (str): 连接NAS集群使用IPV4的地址
ipv6_address (str): 连接NAS集群使用IPV6的地址
environment_info (dict): NAS集群环境信息，如端口、网卡等
nodes (dict): NAS集群节点对象字典, key为控制器在测试床中配置的name，value为name对应的控制器对象

Returns:
None

Raises:
None

Examples:
1、**kwargs参数说明
kwargs = {'hosts': nas集群关联的主机
'resource': resource对象
'raw_resource_data': 原始资源信息
'username': 登陆的用户名
'password': 登陆密码
'ipv4_address': IPV4地址
'ipv6_address': IPV6地址
'environment_info': 整体环境信息
'nodes': {'1' : node} 节点信息}

"""

logger = Log.getLogger(__name__)

def __init__(self, **kwargs):
super(NasCluster, self).__init__()

self.hosts = kwargs.get('hosts')
self.resource = kwargs.get('resource')
self.rawResourceData = kwargs.get('raw_resource_data')
self.username = kwargs.get('username')
self.password = kwargs.get('password')
self.ipv4Address = kwargs.get('ipv4_address')
self.ipv6Address = kwargs.get('ipv6_address')
self.environmentInfo = kwargs.get('environment_info')
self.deviceId = kwargs.get("device_id", None)
self.type = kwargs.get("device_type")

for obj in self.classDict.itervalues():
self.markDirty(obj)

self.nodes = []
tmpNodes = kwargs.get('nodes')
for index in tmpNodes:
self.registerAllWrapper(tmpNodes[index])
self.nodes.append(tmpNodes[index])

self.systemInfo = dict()

filePath = os.path.split(os.path.realpath(__file__))[0]
pluginPath = os.path.join(filePath, 'NasFunction')
fileList = os.listdir(pluginPath)
for index in xrange(len(fileList) - 1, -1, -1):
if fileList[index].startswith("__"):
fileList.pop(index)
elif fileList[index].endswith(".pyc"):
fileList.pop(index)
else:
fileList[index] = 'UniAutos.Device.Storage.Huawei.NasFunction.' + \
fileList[index].replace('.py', "")
for m in fileList:
__import__(m)
for i in dir(sys.modules[m]):
if i.find("__") < 0:
method = getattr(sys.modules[m], i)
setattr(NasCluster, i, method)

def setupEnableComponents(self):
"""初始化设备允许创建的业务列表

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
self.addType('Directory', 'UniAutos.Component.Directory.Huawei.OceanStor.Directory')
self.addType('DirectoryCifsShare', 'UniAutos.Component.DirectoryShare.Huawei.DirectoryCifsShare.DirectoryCifsShare')
self.addType('DirectoryNfsShare', 'UniAutos.Component.DirectoryShare.Huawei.DirectoryNfsShare.DirectoryNfsShare')
pass

def getNode(self, nodeId=None, role=None):
"""获取指定id的nas node对象

Args:
nodeId (str): node ID， eg: "1".
role (str)：node role, eg: 'cifs'.

Returns:
node (UniAutos.Device.Host.NasNode.OceanStor.OceanStor)：
nas node Object, if specify id have not in nas cluster device return None.

Raises:
None.

Examples:
node = nasCluster.getNode("1")

"""
# 指定id和节点role.
if nodeId is not None and role is not None:
for node in self.nodes:
if node.nodeId == nodeId and node.role == role:
return node

# 只指定id.
elif nodeId is not None:
for node in self.nodes:
if node.nodeId == nodeId:
return node

# 只指定role.
elif role is not None:
for node in self.nodes:
if node.role == role:
return node
else:
return None

def dispatch(self, methodName, params={}, nodeId=None, role=None):
"""下发命令

Args:
methodName (str): 命令名称
params (dict): 命令所需参数
nodeId (str): 指定id下发命令.
role (str): 指定node role 下发命令.
Returns:
dict: 命令执行结果

Raises:
None

Examples:
None

"""
node = self.getNode(nodeId, role)

if node:
node.dispatch(methodName, params)

# 如果不指定id和节点role.
elif self.nodes:
return self.getPrimaryNode().dispatch(methodName, params)

else:
raise UniAutosException('There is not node to execute command.')

def getPrimaryNode(self):
"""获取阵列在UniAutos框架的主控，用于发送命令
Notes：在集群节点故障时设置存活的节点为框架主节点，不需要等待切换，做到命令下发无缝衔接.

Args:
None

Returns:
node: 主节点.

Raises:
None

Examples:
None

"""
if self.nodes:
return self.nodes[0]

def syncClassDispatch(self, cls, criteria, synParams, device=None):
"""执行同步命令

Args:
cls (type): 要同步的业务的类

Returns:
dcit: 执行结果

Raises:
None

Examples:
None

"""
if self.nodes:
return self.getPrimaryNode().syncClassDispatch(
componentClass=cls, criteriaDict=criteria,
syncParamsDict=synParams, device=self)

def getClassPropertyDispatch(self, componentClass, propertiesList=None):
"""执行查找业务属性命令

Args:
componentClass (type): 业务类

Returns:
list: 执行结果
Examples: [{'capacity': '30.000GB', 'name': 'Lun01'}, {'capacity': '4.000GB', 'name': 'Lun02'}]

Raises:
None

Examples:
None

"""
if self.nodes:
return self.getPrimaryNode().\
getClassPropertyDispatch(componentClass, propertiesList)

def getNodes(self):
"""获取Nas Cluster的所有Node

Args:
None.

Returns:
self.nodes (list): Nas Cluster的所有Node列表.

Raises:
None.

Examples:
None.

"""
return self.nodes

def setPrimaryNode(self, nodeObj):
"""设置Nas Cluster在UniAutos框架发送命令的主节点

Args:
nodeObj (UniAutos.Device.Host.NasNode.OceanStor.OceanStor) nas node对象.

Returns:
None.

Raises:
None.

Examples:
None.
"""
self.logger.debug('Setting primary controller to %s' % nodeObj.nodeId)
for tmp in self.nodes:
if nodeObj.nodeId == tmp.nodeId:
self.nodes.remove(tmp)

self.nodes.insert(0, nodeObj)

def getAttachHost(self, interfaceType):
"""Gets all the objects that are attached to this Device

Args:
interfaceType (str): (可选参数)Type of host to look for, 'fc','nas' or 'iscsi'.
Leave this param unspecified if you don't care

Returns:
hosts (list): 主机对象列表.

Raises:
None.

Examples:
None.
"""
from UniAutos.Device.Host.HostBase import HostBase
hosts = []
if self.hosts:
for host in self.hosts:
if interfaceType:
if 'type' in host and host['type'] and host['type'] == interfaceType:
del host['type']
for key in host:
if isinstance(host[key], HostBase):
hosts.append(host[key])
else:
del host['type']
for key in host:
if isinstance(host[key], HostBase):
hosts.append(host[key])
if not hosts:
self.logger.warn("getAttachedHost() is returning nothing. "
"Please make sure your testbed is configured properly")

return hosts

def reboot(self, targetMode=None, wait=True):
"""This method is used to reboot unified device. It user specified wait => 1, which is
recommended, it will wait and verify the rebooted boot mode as well.

Args:
targetMode (str): (可选参数)target boot mode after reboot, normal or rescue
*Note* - If target_mode is specified UniAuto will call an engineering
reboot wrapper. If you want to use a customer facing 'reboot' then do
not specify this option

Returns:
None.

Raises:
CommandException: 重启设备出现异常.

Examples:
None.
"""
pass

def registerAllWrapper(self, node):
""" Register all the wrapper type to special controller device

Args:
node Type(NasNode): The nas node device object

Returns:
None

Raises:
None

"""
# Dictionary for all wrappers class
# version = node.softVersion
# productModel = node.productModel
moduleDict = {"UniAutos.Wrapper.NasCluster.Mml.MmlCli": "MmlCli",
"UniAutos.Wrapper.NasCluster.Debug.DebugCli": "DebugCli",
"UniAutos.Wrapper.NasCluster.AdminCli.AdminCli": "AdminCli",
"UniAutos.Wrapper.NasCluster.Diagnose.DiagnoseCli": "DiagnoseCli",
# "UniAutos.Wrapper.Tool.Developer.DeveloperCli": "DeveloperCli",
# "UniAutos.Wrapper.Tool.Minisystem.MinisystemCli": "MinisystemCli",
# "UniAutos.Wrapper.Tool.DevDiagnose.DevDiagnoseCli": "DevDiagnoseCli",
}
# if version == "V300R005C00":
# moduleDict = {"UniAutos.Wrapper.Tool.Mml.MmlCliV300R005C00": "MmlCliV300R005C00",
# "UniAutos.Wrapper.Tool.Debug.DebugCliV300R005C00": "DebugCliV300R005C00",
# "UniAutos.Wrapper.Tool.AdminCli.AdminCliV300R005C00": "AdminCliV300R005C00",
# "UniAutos.Wrapper.Tool.Upgrade.UpgradeCli": "UpgradeCli",
# "UniAutos.Wrapper.Tool.Diagnose.DiagnoseCliV300R005C00": "DiagnoseCliV300R005C00",
# "UniAutos.Wrapper.Tool.Developer.DeveloperCliV300R005C00": "DeveloperCliV300R005C00",
# "UniAutos.Wrapper.Tool.Minisystem.MinisystemCli": "MinisystemCli",
# "UniAutos.Wrapper.Tool.DevDiagnose.DevDiagnoseCli": "DevDiagnoseCli",
# }
# elif version == "V300R003C10":
# moduleDict = {"UniAutos.Wrapper.Tool.Mml.MmlCliV300R003C10": "MmlCliV300R003C10",
# "UniAutos.Wrapper.Tool.Debug.DebugCliV300R003C10": "DebugCliV300R003C10",
# "UniAutos.Wrapper.Tool.AdminCli.AdminCliV300R003C10": "AdminCliV300R003C10",
# "UniAutos.Wrapper.Tool.Upgrade.UpgradeCli": "UpgradeCli",
# "UniAutos.Wrapper.Tool.Diagnose.DiagnoseCliV300R003C10": "DiagnoseCliV300R003C10",
# "UniAutos.Wrapper.Tool.Developer.DeveloperCliV300R003C10": "DeveloperCliV300R003C10",
# "UniAutos.Wrapper.Tool.Minisystem.MinisystemCli": "MinisystemCli",
# "UniAutos.Wrapper.Tool.DevDiagnose.DevDiagnoseCli": "DevDiagnoseCli",
# }
# elif version == "V300R001C00" and (productModel == "Dorado6000 V3" or productModel == "Dorado5000 V3"):
# moduleDict = {"UniAutos.Wrapper.Tool.Mml.MmlCliDORADOV300R001C00": "MmlCliDORADOV300R001C00",
# "UniAutos.Wrapper.Tool.Debug.DebugCliDORADOV300R001C00": "DebugCliDORADOV300R001C00",
# "UniAutos.Wrapper.Tool.AdminCli.AdminCliDORADOV300R001C00": "AdminCliDORADOV300R001C00",
# "UniAutos.Wrapper.Tool.Upgrade.UpgradeCli": "UpgradeCli",
# "UniAutos.Wrapper.Tool.Diagnose.DiagnoseCliDORADOV300R001C00": "DiagnoseCliDORADOV300R001C00",
# "UniAutos.Wrapper.Tool.Developer.DeveloperCliDORADOV300R001C00": "DeveloperCliDORADOV300R001C00",
# "UniAutos.Wrapper.Tool.Minisystem.MinisystemCli": "MinisystemCli",
# "UniAutos.Wrapper.Tool.DevDiagnose.DevDiagnoseCli": "DevDiagnoseCli",
# }

for module, value in moduleDict.iteritems():
__import__(module)
moduleClass = getattr(sys.modules[module], value)
wrapperObj = moduleClass()
node.registerToolWrapper(host=node, wrapper=wrapperObj)

def getAllDirectory(self, parentDir, fileType=None, reverseFlag=None):
"""获取当前传入的父目录下的所有目录或文件.
Args:
parentDir (str): 父目录.
fileType (str): 文件类型，取值范围为: file, directory.
reverseFlag (str): 翻转标志.

Returns:
res (dict): dir name 为key，目录属性为value的字典信息.

Raises:
None.

Examples:
nas.getAllDirectory('/')
"""
return Directory.getAllDirectory(self, parentDir, fileType, reverseFlag)

def createDirectory(self, dirName, parentDir, owner, group, domainType, unixMode=None, parallelStripeWidth=None):
"""创建目录.
Args:
dirName (str): 目录名称.
parentDir (str): 父目录名称.
owner (str): 归属用户.
group (str): 归属用户所属的组.
domainType (str): 域类型.
unixMode (str): 访问权限.
parallelStripeWidth (str): 并行因子.

Returns:
None.

Raises:
None.

Examples:
nas.createDirectory('D1', '/', 'username', 'Administrators', 'LOCAL')
"""
Directory.create(self, dirName, parentDir, owner, group, domainType, unixMode, parallelStripeWidth)

def deleteDirectory(self, dirName, parentDir):
"""delete directory.
Args:
dirName (str): need delete dir name.
parentDir (str): need delete dir name's parent dir name.

Returns:
None

Raises:
None.

Examples:
None.
"""
Directory.delete(self, dirName, parentDir)

def getEachDirectory(self, dirName, parentDir):
"""get each directory.
Args:
dirName (str): need delete dir name.
parentDir (str): need delete dir name's parent dir name.

Returns:
None

Raises:
None.

Examples:
None.
"""
params = {'dir_name': dirName,
'parent_dir': parentDir}
self.dispatch('directoryShowEach', params)

def createDirectoryCifsShare(self, shareName, sharePath, description=None, enableOpLock=None, enableEnotify=None,
enableFailover=None, offlineFileMode=None):
"""创建目录.
Args:
shareName (str): share name.
sharePath (str): share directory dir path.
description (str): description.
enableOpLock (str): op lock, enable or disable.
enableEnotify (str): enotify lock, enable or disable
enableFailover (str): failover lock, enable or disable
offlineFileMode (str): offline file cache mode , none, manual, documents, programe/

Returns:
None.

Raises:
None.

Examples:
nas.create('D1', '/D1', 'username', 'Administrators', 'LOCAL')
"""
DirectoryCifsShare.create(self, shareName, sharePath, description, enableOpLock, enableEnotify, enableFailover,
offlineFileMode)

def executeMml(self, cmdParams, parser=None, primary=None):
"""直接执行mml命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'mml'
node = self.getPrimaryNode()
return node.executeCmd(cmdParams, sessionType, parser, primary)

def executeDebug(self, cmdParams, parser=None, primary=None):
"""直接执行mml命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'debug'
node = self.getPrimaryNode()
return node.executeCmd(cmdParams, sessionType, parser, primary)

def executeCli(self, cmdParams, parser=None, primary=None):
"""直接执行cli命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'admincli'
node = self.getPrimaryNode()
return node.executeCmd(cmdParams, sessionType, parser, primary)

def executeDiagnose(self, cmdParams, parser=None, primary=None):
"""直接执行cli命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'diagnose'
node = self.getPrimaryNode()
return node.executeCmd(cmdParams, sessionType, parser, primary)