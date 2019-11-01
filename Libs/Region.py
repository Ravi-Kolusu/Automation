
# -*- coding: UTF-8 -*-

"""
功 能: Region类, 提供Region相关接口.
"""

import time
import os
import re
import platform


from UniAutos.Component.StoragePool.Huawei.FusionStorage import StoragePool
from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Device.Storage.Fusion.AvailableZone import AvailableZone
from UniAutos.Device.Storage.Fusion.FusionStorageNode import FusionStorageNode
from UniAutos.Dispatcher import Dispatcher
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Device.Host.Linux import Linux


class Region(DeviceBase, Dispatcher):
"""Region类

提供Region接口

Args:
AvailableZones (dict): key为AvailableZone对象id, value为AvailableZone对象的字典

Attributes:
self.available_zones (dict): 归属于此region的available_zone

Returns:
Region (instance):Region对象实例.

"""

@validateParam(availableZones=dict, environmentDict=dict)
def __init__(self, availableZones, environmentDict=None):
super(Region, self).__init__()
if environmentDict:
self.name = environmentDict.get('name', '')
if availableZones:
self.available_zones = availableZones
for identity in self.available_zones:
self.available_zones[identity].setRegion(self)
else:
raise UniAutosException('availableZones must be specifed and can not be empty.')

map(lambda x: self.markDirty(x), self.classDict.values())
self.__current_available_zone = None
self.setCurrentAvailableZone(self.available_zones.values()[0])
self.server = {}
# 初始化环境信息
if 'environment' in environmentDict and environmentDict['environment']:
self.__initialize(environmentDict['environment'])

def setupEnableComponents(self):
"""初始化设备允许创建的业务列表
"""
self.addType('StoragePool', 'UniAutos.Component.StoragePool.Huawei.FusionStorage.StoragePool')
self.addType('Disk', 'UniAutos.Component.Disk.Huawei.FusionStorage.Disk')

def dispatch(self, methodName, params={}, interactRule=None, option=None):
"""下发命令

Args:
methodName (str): 命令名称
params (dict): 命令所需参数
interactRule(dict): 交互输入。如过匹配到字典的key值，就输入字典的value
option (dict): 命令收发控制参数，控制命令超时时间，sessionType等
Returns:
dict: 命令执行结果
"""
return self.__current_available_zone.dispatch(methodName, params, interactRule, option)

def createStoragePool(self, pool_id):
"""创建StroagePool对象

Args:
"pool_id" (str) :pool的ID

Returns:
UniAutos.Component.StoragePool.Huawei.FusionStorage.StoragePool (instance): 返回StroagePool对象
"""
return StoragePool.create(self, pool_id)

@validateParam(availableZone=AvailableZone)
def setCurrentAvailableZone(self, availableZone):
"""设置一个当前做操作的AvailableZone
"""
self.__current_available_zone = availableZone

def getCurrentAvailableZone(self):
"""获取当前做操作的AvailableZone
"""
return self.__current_available_zone

def getAvailableZone(self, identity=None):
"""获取指定AvailableZone对象

Args:
identity (str): AvailableZone的ID
"""
return self.available_zones[identity] if identity else self.available_zones.values()

@validateParam(node=FusionStorageNode)
def setCurrentNode(self, node):
for az in self.available_zones.values():
if node in az.fusion_storage_nodes.values():
az.setCurrentNode(node)
self.setCurrentAvailableZone(az)
return
raise UniAutosException('There is no node witch ip is [%s] in this region.' % node.localIP)

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
return self.__current_available_zone.getPlogManagerMasterInfo(deploy)

def getFusionStorageNode(self, available_zone=None, identity=None):
"""获取指定的FusionStorageNode节点对象

Args:
available_zone (str|AvailableZone): FusionStorageNode所在的AvailableZone对象或ID
identity (str): FusionStorageNode的ID

Returns:
FusionStorageNode obj list
Raise:
CommandException: 查询失败

Example:
node = self.getFusionStorageNode()

"""
if not available_zone:
nodes = []
for az in self.available_zones:
new_nodes = self.available_zones[az].getFusionStorageNode(identity)
if isinstance(new_nodes, list):
nodes.extend(new_nodes)
else:
nodes.append(new_nodes)
return nodes

if isinstance(available_zone, AvailableZone):
return available_zone.getFusionStorageNode(identity)

return self.available_zones[available_zone].getFusionStorageNode(identity)

def syncClassDispatch(self, componentClass, criteriaDict=None, syncParamsDict=None, device=None):
"""使用Tool Wrappers同步更新这个类别里面所有对象实例的properties

Args:
componentClass (str): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
criteriaDict (dict): 根据同步的对象属性Dict和过滤的Dict进行匹配
syncParamsDict (dict): 需要同步的参数属性Dict
device(UniAUtos.Device): UniAutos Device 对象

Returns:
returnDict(Dict): 获得相应的Wrapper对象

Raises:
UniAutos.Exception.UniAutosException

"""
return self.getCurrentAvailableZone().syncClassDispatch(componentClass, criteriaDict, syncParamsDict, device)

def __initialize(self, params):
"""把环境信息实例化成对象
Args:
params (dict): environment包含信息的字典

Returns:
returnDict(Dict)

"""

if 'iam' in params:
self.server['iam'] ={}
if isinstance(params['iam'], list):
for iam in params['iam']:
self.server['iam'][iam['id']] = iam
else:
self.server['iam'][params['iam']['id']] = params['iam']
if 'nfs_agent' in params:
self.server['nfs_agent'] ={}
if isinstance(params['nfs_agent'], list):
for nfs_agent in params['nfs_agent']:
self.server['nfs_agent'][nfs_agent['id']] = nfs_agent
else:
self.server['nfs_agent'][params['nfs_agent']['id']] = params['nfs_agent']
if 'obs_client' in params:
self.server['obs_client'] ={}
if isinstance(params['obs_client'], list):
for obs_client in params['obs_client']:
self.server['obs_client'][obs_client['id']] = obs_client
else:
self.server['obs_client'][params['obs_client']['id']] = params['obs_client']
if 'lvs' in params:
self.server['lvs'] ={}
if isinstance(params['lvs'], list):
for lvs in params['lvs']:
self.server['lvs'][lvs['id']] = lvs
else:
self.server['lvs'][params['lvs']['id']] = params['lvs']
if 'lb' in params:
self.server['lb'] = params['lb']
if 'kms' in params:
self.server['kms'] = params['kms']
if 'smn' in params:
self.server['smn'] = params['smn']
if 'ntp' in params:
self.server['ntp'] = params['ntp']
if 'dns' in params:
self.server['dns'] ={}
if isinstance(params['dns'], list):
for dns in params['dns']:
self.server['dns'][dns['id']] = dns
else:
self.server['dns'][params['dns']['id']] = params['dns']
if 'sftp' in params:
self.server['sftp'] = params['sftp']

def getServer(self, alias):
"""获取环境对象
Args:
alias (string): environment中对象的别名
Returns:
return: specific environment object
Example:
self.getServer(alias='iam')

"""
if alias in ['iam', 'nfs_agent', 'dns', 'obs_client', 'lvs']:
if alias == 'iam':
return self.server[alias]["1"]
elif alias:
self.server[alias]['1'] = Linux.discover(self.server[alias]['1'])
return self.server[alias]['1']

if alias and alias in self.server:
if isinstance(self.server[alias], dict):
if alias == 'sftp':
return self.server[alias]
else:
self.server[alias] = Linux.discover(self.server[alias])
return self.server[alias]

def getServerDict(self, alias):
"""获取环境dict
Args:
alias (string): environment中对象的别名
Returns:
return: specific environment dictionary
Example:
self.getServerDict(alias='iam')

"""
return self.server[alias] if alias in self.server else None

def find(self, alias, forceSync=False, onlyNew=False, criteria=None,createByConfigureEnv=False, onlyConfigureEnv=False, validatedByConfigureEnv=False, node=None):
"""查找当前设备的业务

Args:
alias (string): 业务别名, 如: "Lun", "pool".
forceSync (boolean): 是否强制同步，默认否
onlyNew (boolean): 只返回新发现的对象， 默认否
criteria (dict): 业务的查询条件, key为业务的Property, value为property值的字符串或正则表达式.
onlyConfigureEnv (bool): 查找标记为createByConfigureEnv和validatedByConfigureEnv的component,
-可选参数，默认为False.
createByConfigureEnv (bool): 只查找标记为createByConfigureEnv的component, 可选参数，默认为False.
validatedByConfigureEnv (bool): 只查找标记为validatedByConfigureEnv的component, 可选参数，默认为False.
node(obj): 节点对象

Returns:
list: 业务对象列表

Raises:
InvalidParamException: 业务的查询条件有误 或 业务别名不存在

Examples:
# example1: 属性值name等于来查找
lunList = storageDevice.find('Lun', criteria={'name': params["lun_oldName"]})

# example2: 属性值name匹配正则表达式查找
namRegx = re.compile(r'^frank')
lunList = storageDevice.find('Lun', criteria={'name': namRegx})

# example3: 查找lun的capacity大于200GB的Lun对象
lunList = storageDevice.find("Lun", criteria={'capacity': {">": '200GB'}})

# example4: 演示调用自定义的回调函数来进行过滤查找
def test(param):
if param == "Online":
return True
else:
return False
lunList = storageDevice.find("Lun", criteria={'capacity': {">": '200GB'}, "running_status": test})

Changes:
2017-06-13 mwx408390 Created

"""
if node:
cur_node = self.getCurrentAvailableZone().getPrimaryNode()
self.setCurrentNode(node)
objs = DeviceBase.find(self, alias, forceSync, onlyNew, criteria,
createByConfigureEnv, onlyConfigureEnv, validatedByConfigureEnv)
self.setCurrentNode(cur_node)
return objs
else:
return DeviceBase.find(self, alias, forceSync, onlyNew, criteria,
createByConfigureEnv, onlyConfigureEnv, validatedByConfigureEnv)

def collect_device_log(self, log_path, case_name):
"""收集节点日志到本地
Args:
log_path (str): 产品日志路径,可传list
case_name (str): 用例名称
Example:
self.collection_log_to_local(log_path=[/var/log/dsware/],
case_name='tc_p9000001_deploy')

"""
sys_str = platform.system()
clock = time.strftime("%Y%m%d %H%M", time.localtime())
day, minuit = clock.split()
for az_id, az in self.available_zones.iteritems():
nodes = az.getFusionStorageNode()
local_path = ''
if sys_str.lower() == 'windows':
local_path = os.path.abspath('D:/log/%s/%s_%s/available_zone_%s/' % (day, minuit, case_name, az_id))
elif sys_str.lower() == 'linux':
local_path = os.path.abspath('/var/log/%s/%s_%s/available_zone_%s/' % (day, minuit, case_name, az_id))
# 本地创建文件夹
if not os.path.exists(local_path):
os.makedirs(local_path)
if not isinstance(log_path, (tuple, list)):
log_path = (log_path,)

def collect_node_log(node):
"""收集节点日志，打包到本地
Args:
node (FusionStorage): FusionStorage object
Example:
collect_node_log(node=node)
"""
#若前面存在该文件，再向该文件拷贝文件，回提示是否要覆盖，有可能失败，提前清除该目录
node.deleteFile('/var/backup/')
log_name = '%s%s_%s.tar.gz' % (day, minuit, node.localIP.strip())
back_path = "/var/backup/backup_log/"

for directory in log_path:
sub_back_path = '%s%s/' % (back_path, directory.strip('/'))
node.createDirectory(path=sub_back_path)
if node.doesPathExist({'path': directory}):
node.copyDirectory(source='%s/' % directory.rstrip('/'), destination=sub_back_path)
else:
self.logger.error(u'There is no log directory [%s] in node [%s]' % (node.localIP, directory))
# 重定向dmesg运行命令到指定文件，以便定位问题
dmesg_path = '%sdmesg' % back_path
# 创建文件
node.createFile(filePath=dmesg_path)
node.executeCmd(cmdParams={'command': ['dmesg', '>', dmesg_path]})
# 打包
response = node.run({'command': ['tar', '-zcvf',
log_name,
'./*'],
"directory": "/var/backup/backup_log"})
if response["rc"] != 0:
raise CommandException("Problem tar File. Error: %s" % response['stderr'])
# 上传到执行机上
node.command.getFile(src='/var/backup/backup_log/%s' % log_name, dst=os.path.join(local_path, log_name))
# 回到root目录
node.run({'command': ["cd /root"]})
# 删除节点上的打包日志
node.deleteFile('/var/backup/')

# 收集节点日志
for node in nodes:
collect_node_log(node=node)

def delete_device_log(self, log_path):
"""
删除节点上的指定路径上的日志

"""
for az_id, az in self.available_zones.iteritems():
nodes = az.getFusionStorageNode()
for node in nodes:
# 回到root目录
node.run({'command': ["cd /root"]})
for path in log_path:
if not node.doesPathExist({"path": path}):
continue
if path == "/":
raise UniAutosException("Attempting to delete root is not allowed.")
num = 0
while num < 5:
response = node.run({"command": ["sh", "-c", "rm", "-rf", path]})
if response["rc"] != 0:
time.sleep(5)
num += 1
continue
else:
break
# for node in nodes:
# # 回到root目录
# node.run({'command': ["cd /root"]})
# node.deleteFile('%s/*' % log_path.rstrip('/'))

def check_core_ifexists(self, core_path, case_name):
"""检查是否存在core文件，并且将core上传到服务器
Args:
core_path (str): 查询core的路径
case_name (str): 用例名称
Example:
check_core_ifexists(core_path='/var/log/dsware/core', case_name='tc_p9000001_deploy')

"""
sys_str = platform.system()
nodes = self.getFusionStorageNode()
core_flg = False
for node in nodes:
if not node.doesPathExist({'path': core_path}):
continue
response = node.run({'command': ['ls -alF --color=never'],
"directory": core_path})
if not response['stdout']:
raise CommandException
matcher = re.search("core.gz", response['stdout'])
if matcher:
clock = time.strftime("%Y%m%d %H%M", time.localtime())
day, minuit = clock.split()
# 上传到执行机上路径
local_path = ''
if sys_str.lower() == 'windows':
local_path = os.path.abspath('D:/core/%s/%s_%s/%s/' % (day, minuit, case_name, node.localIP.strip()))
elif sys_str.lower() == 'linux':
local_path = os.path.abspath('/var/core/%s/%s_%s/%s/' % (day, minuit, case_name, node.localIP.strip()))
# 本地创建文件夹
if not os.path.exists(local_path):
os.makedirs(local_path)
lines_list_all = re.split('\r\n|\n', response['stdout'])
log_name_list = []
for line in lines_list_all:
matchersub = re.search("\s+(\S+core.gz)", line)
if matchersub:
log_name_list.append(matchersub.group(1))
for log_name in log_name_list:
node.command.getFile(src='%s%s' % (core_path, log_name), dst=os.path.join(local_path, log_name))
# 删除节点里面的core文件
node.deleteFile('%s/*' % core_path.rstrip('/'))
core_flg = True

# 拷贝2进制文件：
osfilelist = ['agent', 'mdc', 'osd', 'vbs']
for osfile in osfilelist:
filepath = ("/opt/dsware/%s/bin/" % osfile)
if not node.doesPathExist({'path': filepath}):
continue
response = node.run({'command': ['ll --color=never'],
"directory": filepath})
lines_list_all = re.split('\r\n|\n', response['stdout'])
for line in lines_list_all:
if re.search("#", line) or not re.search(":", line):
continue
if sys_str.lower() == 'windows':
local_path = os.path.abspath(
'D:/core/%s/%s_%s/%s/%s/' % (day, minuit, case_name, node.localIP.strip(), osfile))
elif sys_str.lower() == 'linux':
local_path = os.path.abspath(
'/var/core/%s/%s_%s/%s/%s/' % (day, minuit, case_name, node.localIP.strip(), osfile))
# 本地创建文件夹
if not os.path.exists(local_path):
os.makedirs(local_path)
filename = line.rstrip().split(" ")[-1]
node.command.getFile(src='%s%s' % (filepath, filename), dst=os.path.join(local_path, filename))
return core_flg