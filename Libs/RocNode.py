RocNode ::


#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能: 分布式块节点类
版权信息: 华为技术有限公司, 版本所有(C) 2014-2015
"""

import os
import sys
import re
import time
import datetime
import traceback
import thread
import socket
import threading
from UniAutos.Device.DeviceBase import DeviceBase
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import Adapter
from UniAutos.Device.Host.Linux import Linux
from UniAutos.Device.Host.NasNode.OceanStor import OceanStor
from UniAutos import Log
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.Time import sleep
from UniAutos.Util.Units import Units
from UniAutos.Wrapper.Tool.Roc.DiagnoseCli.Parser import parseRocHorizontalList
from UniAutos.Util.CommonFault.FaultType import FaultType
from UniAutos.Util.WrapperHolder import WrapperHolder
from UniAutos.Util.Codec import getFormatString
from UniAutos.Wrapper.Api.ApiBase import ApiBase
from UniAutos.Wrapper.Api.VmwareBase import VmwareBase
from UniAutos.Wrapper.Tool.Selenium.UniWebBase import UniWebBase
from UniAutos.Wrapper.Template.CLI import CliWrapper

gRocInitToolsLock = thread.allocate_lock()
log = Log.getLogger(__name__)

class RocNode(OceanStor, Linux):
"""RocNode初始化

功能说明: RocNode初始

Args:
username (str) : 与RocNode连接时需要使用的用户名
password (str) : 与RocNode连接时需要使用的密码
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
返回RocNode实例

Examples:
node = OceanStor.discover(params)

"""

def __init__(self, username, password, params):
super(RocNode, self).__init__(username, password, params)
self.nodeId = params.get('id')
self.services = []
self.role = None
self.docker_ports = []
self.dockers = {}
self.faultLock = threading.Lock()
self.fault = None
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
self.float_ip=self.detail.get('float_ip', '')
self.exfloat_gw=self.detail.get('external_float_gateway', '')
self.exfloat_mask=self.detail.get('external_float_mask', '255.255.254.0')
self.exfloat_ip=self.detail.get('external_float_ip', self.localIP)
self.infloat_gw=self.detail.get('internal_float_gateway', '')
self.infloat_mask=self.detail.get('internal_float_mask', '255.255.254.0')
self.infloat_ip=self.detail.get('internal_float_ip', self.localIP)
self.services = self.detail.get('service').replace(' ', '').split(',')
self.role = self.detail.get('role')
self.zk_esn = self.detail.get('zk_esn') # 当前节点用于创建集群的磁盘esn
self.ccdb_esn = self.detail.get('ccdb_esn') # 当前节点用于创建集群的磁盘esn
docker_ports = self.detail.get('docker_port', '').replace(' ', '')
if docker_ports != "":
self.docker_ports = docker_ports.split(',')

self.manager_map_ip = None
if self.information.get("inet_panels"):
manager_map = self.information['inet_panels'].get("manager_map")
if manager_map and manager_map.get("ipv4_address"):
self.manager_map_ip = manager_map.get("ipv4_address")

self.__available_zone = None
self.initFunctionModules()

map(lambda x: self.markDirty(x), self.classDict.values())

# 给dsware insight工具用的
self.dsware_dest_id = None
self.dsware_dest_ip = None

self.__node_version = None
# added by g00414304 2019-01-16 20:00:00
# 由于产品变更，产品会默认关闭8765和6666两个端口 需要在测试框架这里主动打开
# 2019-01-27 不在这里执行，在部署之后进行处理
# try:
# if hasattr(self, 'command'):
# self.run({'command': ['iptables -I INPUT -p tcp --dport 8765 -j ACCEPT']})
# self.run({'command': ['iptables -I INPUT -p tcp --dport 6666 -j ACCEPT']})
# except Exception as e:
# log.info('Modify 8765 and 6666 port error, details: %s' % e)

@staticmethod
def initFunctionModules():
filePath = os.path.split(os.path.realpath(__file__))[0]
pluginPath = os.path.join(filePath, 'Function')
fileList = os.listdir(pluginPath)
for index in xrange(len(fileList) - 1, -1, -1):
if fileList[index].startswith("__"):
fileList.pop(index)
elif not fileList[index].endswith(".py"):
fileList.pop(index)
else:
fileList[index] = 'UniAutos.Device.Storage.Roc.Function.' + \
fileList[index].replace('.py', "")
for m in fileList:
__import__(m)
for i in dir(sys.modules[m]):
if i.find("__") < 0:
method = getattr(sys.modules[m], i)
setattr(RocNode, i, method)

def setupEnableComponents(self):
"""
初始化设备允许创建的业务列表
"""
#self.addType('EdsLun', 'UniAutos.Component.Lun.Huawei.Roc.Eds.EdsLun.EdsLun')
self.addType('Lun', 'UniAutos.Component.Lun.Huawei.Roc.Cfg.CfgLun.CfgLun')
self.addType('Volume', 'UniAutos.Component.Volume.Huawei.Roc.Roc.Volume')
self.addType('IscsiInitiator', 'UniAutos.Component.Initiator.Huawei.Roc.Iscsi.Initiator')
self.addType('HostResource', 'UniAutos.Component.HostResource.Huawei.Roc.HostResource')
self.addType('HostResourceGroup', 'UniAutos.Component.HostResourceGroup.Huawei.Roc.HostResourceGroup')
self.addType('Snapshot', 'UniAutos.Component.Snapshot.Huawei.Roc.Roc.Snapshot')
self.addType('RmConsistencyGroup', 'UniAutos.Component.ConsistencyGroup.Huawei.EVS.RmConsistencyGroup.RmConsistencyGroup')
self.addType('HmConsistencyGroup', 'UniAutos.Component.ConsistencyGroup.Huawei.EVS.HmConsistencyGroup.HmConsistencyGroup')
self.addType('HyperMetroDomain', 'UniAutos.Component.HyperMetroDomain.Huawei.EVS.HyperMetroDomain')
self.addType('HyperMetroPair', 'UniAutos.Component.HyperMetroPair.Huawei.EVS.HyperMetroPair')
self.addType('IpPool', 'UniAutos.Component.IpPool.Huawei.EVS.IpPool')
self.addType('QuorumServer', 'UniAutos.Component.QuorumServer.Huawei.EVS.QuorumServer')
self.addType('RemoteDevice', 'UniAutos.Component.RemoteDevice.Huawei.EVS.RemoteDevice')
self.addType('RemoteReplication', 'UniAutos.Component.RemoteReplication.Huawei.EVS.RemoteReplication')
self.addType('RepClsPsk', 'UniAutos.Component.RepClsPsk.Huawei.EVS.RepClsPsk')
self.addType('ReplicateCluster', 'UniAutos.Component.ReplicateCluster.Huawei.EVS.ReplicateCluster')

def setAvailableZone(self, available_zone):
"""获取当前节点归属的AvailableZone对象"""
self.__available_zone = available_zone

def getAvailableZone(self):
"""设置当前节点归属的AvailableZone对象"""
return self.__available_zone

@classmethod
def discover(cls, params):
"""
获取RocNode对象

Args：
params (dict): params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"type": (str),
"os": (str)
}
params键值对说明:
protocol (str): 通信协议, key可选, 取值范围["standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口, key可选
ipv4_address (str): 主机的ipv4地址, key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址, key与ipv4_address必选其一
type (str): 连接的类型
os (str): 操作系统类型，如Linux
Returns:
obj控制器对象

Examples:
params = {
"type": type,
"port": port,
"ipv4_address": node.localIP,
"os": os,
"username": username,
"password": password,
}
dockerObj = RocNode.discover(params)

"""
wrappers = []
if 'tool_wrappers' in params:
wrappers = params.pop("tool_wrappers")

obj = super(RocNode, cls).discover(params)
obj.wrapper_list = wrappers
obj.original_wrapper_list = wrappers
# Register wrapper
obj.registerCliWrapper()
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

def getLunDevNames(self, nameList=list(), iscsi=False):
"""
根据lun名字获取lun dev name list，lun对象必须已经mount之后，调用该函数才合法

AW逻辑：
如果 iscsi 为 True：
通过lsscsi获取所有挂载的lun，通过429命令获取所有SCSI方式挂载的lun
从所有挂载的lun全集中去掉 SCSI方式挂载的lun
如果 iscsi 为 False:
如果 nameList 为空：
通过429命令查询所有SCSI挂载的lun
否则：
按照namelist中的值，通过1504命令查询每个lun的设备名

Args:
nameList (list): 传入的lun名字list, 如 ['lun0','lun1','lun2']
iscsi (bool): 是否是查询iscsi挂载的lun，默认False

Returns:
retList|lsscsi_list (list): lun的dev名字列表， 如['/dev/sda','/dev/sdb']

Examples:
# 获取 SCSI 方式挂载的所有的lun的设备名
all_name_list = self.node.getLunDevNames()
# 获取 SCSI 方式挂载的指定的lun的设备名
specify_name_list = self.vbs_node.getLunDevNames(nameList=lun_name_list)
# 获取iscsi方式挂载的所有的lun的设备名
iscsi_name_list = self.node.getLunDevNames(iscsi=True)

"""
if not iscsi:
if not nameList:
res = self.dispatch('volumeGetAllVolumeInfo')
scsi_list = res[0]['parser'].keys()
return scsi_list

retList = []
for name in nameList:
dps = self.calcParamsForVbs()
params = {'volume_name': name}
params.update(dps)
result = self.dispatch('getVolumeInfo', params)
for line in reversed(result[0]['stdout']):
if 'show_vbs_query_wwn_by_name_result' not in line or 'node_id:' not in line or 'node_ip:' not in line or 'dev_name:' not in line:
continue
else:
ip = line.split('node_ip:')[-1].split(',')[0]
if ip in [self.localIP, self.internal_ip, self.exfloat_ip, self.manager_map_ip]:
devname = line.split(':')[-1][:-1]
retList.append(devname)
break

return retList
else:
result = self.run({'command': ['lsscsi | grep -v "-" | grep "VBS fileIO"']})
lsscsi_list = []
for line in result['stdout'].split('\r\n'):
if 'VBS fileIO' not in line or '/dev/sd' not in line:
continue
dev_name = re.search(r'.*(/dev/sd\S+)', line.strip()).groups()[0]
lsscsi_list.append(dev_name)
#获取所有scisi方式挂载的盘符
res = self.dispatch('volumeGetAllVolumeInfo')
scsi_list = res[0]['parser'].keys()

# 获取到所有通过iscsi挂载的lun dev_name list
for i in scsi_list:
if i in lsscsi_list:
lsscsi_list.remove(i)
self.logger.info('The iscsi lun dev name list now is %s' % lsscsi_list)

# 过滤掉namelist中的 dev_name
if len(nameList) > 0:
name_wwn_list = []
for name in nameList:
ret = self.dispatch('getVolumeInfo', params={'volume_name':name})
name_wwn_list.append(ret[0]['parser']['id']['wwn'])
self.logger.info('The iscsi mount lun name list is {name_list}, and related dev name list is {dev_name_list}'.format(
name_list=nameList, dev_name_list=name_wwn_list))

tmp_list = []
rr = self.run({'command':['ls -l /dev/disk/by-id/']})
for nw in name_wwn_list:
tmp_list.extend([x.strip().split('/')[-1] for x in rr['stdout'].split('\r\n') if nw in x])

removeList = []
for i in lsscsi_list:
if i and i.split('/')[-1] not in tmp_list:
removeList.append(i)
for tmpDisk in removeList:
lsscsi_list.remove(tmpDisk)
return lsscsi_list


def rescanDisk(self):
"""
覆盖linux下的方法，不需要hot add方法了
:return:
"""
pass

def doesPathExist(self, params):
"""
判断路径是否存在，会调用Linux中的doesPathExist函数

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
node.doesPathExist({'path': '/home/permitdir/dha/download/dha_ctrl0.tar.bz2'})

"""
return Linux.doesPathExist(self, params)

def run(self, params):
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
return Linux.run(self, params)

def syncClassDispatch(self, componentClass, criteriaDict=None, syncParamsDict=None, device=None, ):
# """使用Tool Wrappers同步更新这个类别里面所有对象实例的properties
#
# Args:
# componentClass(String): Wrapper方法名称,可在相应的Wrapper类里面获取使用信息
# criteriaDict(Dict): 根据同步的对象属性Dict和过滤的Dict进行匹配
# syncParamsDict(Dict): 需要同步的参数属性Dict
# device(UniAUtos.Device): UniAutos Device 对象
#
# Returns:
# returnDict(Dict): 获得相应的Wrapper对象
#
# Raises:
# UniAutos.Exception.UniAutosException
#
# """
# syncParams = deepcopy(syncParamsDict)
# return Linux.syncClassDispatch(self, componentClass, criteriaDict, syncParams, device)

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

"""

if not syncParamsDict:
syncParamsDict = {}
classes = []
candidateKeys = componentClass.getCandidateKeys()

searchKeys = candidateKeys
if criteriaDict is not None:
for critProp in criteriaDict.keys():
if critProp not in searchKeys:
searchKeys.append(critProp)

NewWrapper = False
propInfoDict = {}
twInfoDict = {}
if NewWrapper:
wrapperList = filter(lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.CLI.CliWrapper',
self.wrapper_list)
cliWrapper = wrapperList[0].get('wrapper')
propInfoDict = self.createPropertyInfoHash(componentClass, searchKeys)
twInfoDict = wrapperList[0]
else:
for wrapperDict in self.wrapper_list:
wrapperObj = wrapperDict['wrapper']
if wrapperDict['wrapper'].getDevice is None:
if (isinstance(self, DeviceBase)):
wrapperDict['wrapper'].setDevice(self)
propInfoDict = wrapperObj.createPropertyInfoHash(componentClass, searchKeys)
loopBreak = False
if criteriaDict is not None:
for prop in criteriaDict:
if prop not in propInfoDict:
loopBreak = True
break
if loopBreak:
continue
twInfoDict = wrapperDict
break
else:
if propInfoDict:
twInfoDict = wrapperDict
break
else:
continue
if twInfoDict is None:
wrappers = []
for wrapper in self.wrapper_list:
fullName = wrapper['wrapper'].__module__ + '.' \
+ wrapper['wrapper'].__class__.__name__
wrappers.append(fullName)
raise UniAutosException('None of the configured tool wrappers (%s) supply '
'any of the defined identifier properties (%s) '
'for %s.' % (','.join(wrappers), ','.join(searchKeys), componentClass))

host = twInfoDict.get('host')
wrapper = twInfoDict.get('wrapper')

methodDict = {}
partial = False
if NewWrapper:
result = propInfoDict.get("show")
if isinstance(result, dict):
params = result.get("extra", {})
if result.get("method").startswith("adapter"):
methodName, params = Adapter.__dict__.get(result["method"])(params)
else:
methodName = result.get("method")
syncParamsDict.update(params)
partial = result.get("partial", False)
else:
methodName = result
methodDict = {"methdName": methodName}
else:
for propValue in propInfoDict.values():
if propValue.has_key('getmethod'):
funcId = propValue['getmethod']
if not methodDict.has_key(funcId):
methodDict[funcId] = funcId
if not syncParamsDict:
classObj = wrapper.getCommonPropertyInfo(propValue['getmethod'], searchKeys)
classes.extend(classObj)

if len(classes) == 0:
classes.append(componentClass.__module__ + '.' + componentClass.__name__)

# threadLock here for all classes
threadComponentClassLocks = []
try:
for klass in classes:
device.threadComponentClassLock(klass)
threadComponentClassLocks.append(klass)
newCriteriaDict = {}
optionKeys = candidateKeys + componentClass.getOptionKeys()

fullFind = True

if criteriaDict is not None:
for criteriaKey in criteriaDict.keys():
if type(criteriaDict[criteriaKey]).__name__ in ['str', 'bool', 'int', 'float']:
if (criteriaKey in optionKeys):
newCriteriaDict[criteriaKey] = criteriaDict[criteriaKey]

if len(newCriteriaDict) != 0:
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(newCriteriaDict)
else:
tempKeys = componentClass.getCandidateKeys()
if criteriaDict:
for criteriaKey in criteriaDict.keys():
if (criteriaKey in tempKeys):
if 'options' not in syncParamsDict:
syncParamsDict['options'] = []
syncParamsDict['options'].append(criteriaKey)

twProps = []
for methodName in methodDict.values():
runWrapperParams = {}
if host is not None:
runWrapperParams['host'] = host
runWrapperParams['wrapper'] = wrapper
ret = self.__callWrapperForRoc(runWrapperParams, methodName, syncParamsDict, 1)

for result in ret:
twProps.extend(result['parser'].values())
if result.get("partial", False) or partial:
fullFind = False
return {'properties': twProps,
'classes': classes,
'full_find': fullFind,
'thread_locks': threadComponentClassLocks}
except Exception as e:
self.logger.info(traceback.format_exc())
for name in threadComponentClassLocks:
device.threadUnlock(name)
raise e
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
from UniAutos.Exception.InvalidParamException import InvalidParamException
raise InvalidParamException("Retry count must be an integer >= 0.")
exception = {"command": cmdInfo["cmdline"]}
info = {}
tries = 0
while tries = 0:
curWrapper.disConnect()
curWrapper.connect()
curWrapper.connectedTime = datetime.datetime.now()

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, UniWebBase):
can = curWrapper.can(methodName)
if can is None:
raise CommandException(
"Invalid method name '%s' specified for wrapper '%s'" % (methodName, wrapperClassNm))

ret = self.activateCan(can, curWrapper, wrapperParamsDict)
self.logger.cmdResponse(getFormatString(ret))
elif isinstance(curWrapper, CliWrapper):
ret = [curWrapper.runWrapper(methodName, wrapperParamsDict)]
else:
newParams = {}
newParams['wrapper'] = curWrapper
newParams['method'] = methodName
newParams['params'] = wrapperParamsDict
ret = runWrapperParamsDict['host'].runToolWrapperMethod(newParams)

return ret
finally:
if dispatching:
dispatching()


def _insight(self, nodeType, destId, destIp, destPort, destMid, commandType, parameter=None, timeout=None, useDIcmd=None, directory='/opt/fusionstorage/agent/tool'):
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
# directory = '/opt/fusionstorage/agent/tool'
timeout_cmd = timeout if timeout else 600
if useDIcmd and nodeType != '0':
cmdSpec = {
'command': ["timeout -s 2 %s ./dsware_insight_cmd.sh dsware_insight" % timeout_cmd, nodeType, destId, destIp, destPort, destMid, commandType],
"directory": directory,
"timeout": timeout if timeout else 600
}
else:
cmdSpec = {
'command': ["./dsware_insight", nodeType, destId, destIp, destPort, destMid, commandType],
"directory": directory,
"timeout": timeout if timeout else 600
}

if parameter:
cmdSpec['command'].append(parameter)

return self.run(cmdSpec)

def getPlogManagerMasterInfo(self, filePath='/opt/fusionstorage/persistence_layer/mdc/conf/mdc_conf.cfg',
directory='/opt/fusionstorage/agent/tool', deploy=None, useDIcmd=None):
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
result ={}
nodes = self.getAvailableZone().getRegion().getFusionStorageNode()
for node in nodes:
if 'plogmanager' in node.rawService:
# 过滤出有用的进行信息
cmdSpec = {'command': ['ps -ef | grep -e dsware_mdc -e plog_manager | egrep -v grep']}
info = node.run(cmdSpec)
mdcIP = node.localIP
if info['stdout'] and re.search('mdc_conf.cfg', info['stdout']):
# 读取文件内容
# ret = node.readFile(filePath='/opt/fusionstorage/persistence_layer/mdc/conf/mdc_conf.cfg')
# 修改增加filePath形参，默认值为/opt/fusionstorage/persistence_layer/mdc/conf/mdc_conf.cfg
# 2019.7.10 lwx731007 修改
ret = node.readFile(filePath=filePath)
for item in ret:
if re.search('mdc_id=(\d+)', item):
identity = re.search('mdc_id=(\d+)', item).group(1)
if re.search('mdc_port=(\d+)', item):
port = re.search('mdc_port=(\d+)', item).group(1)
if re.search('mdc_ip_2=', item):
#适配IPV6
mdcIP = re.search('mdc_ip_2=(\S+)@\S+', item).group(1)
if '[' in mdcIP:
mdcIP=mdcIP.replace('[','').replace(']','')

i = 1
while i = 2000000000:
# fnPattern = 'FusionStorage_aarch64.*8\.0.*\.tar\.gz'

def __generate_fns(incl, excl):
_pf = {_p: {} for _p in PACKAGE_TYPES}

dl = False
if incl is not None and isinstance(incl, str):
for l in lines:
l = re.sub(r'\s.*', ' ', l)
# get file name
fn = l.split(' ')[-1]
if not fn.endswith('.tar.gz'):
continue
if not re.match(r"^Fusion[sS]torage", fn):
continue
if re.search(r'' + incl + '', l):
dl = True
break
if not dl:
incl = None
excl = 'dl'

for l in lines:
l = re.sub(r'\s.*', ' ', l)
# get file name
fn = l.split(' ')[-1]
if not fn.endswith('.tar.gz'):
continue

if not re.match(r"^Fusion[sS]torage", fn):
continue

if not re.search(r'' + fnPattern + '', fn) and not re.search(r'^FusionStorage_8\.0.*\.tar\.gz', fn):
continue

if incl is not None and isinstance(incl, str):
if not re.search(r''+incl+'', fn):
continue

if excl is not None and isinstance(excl, str):
if re.search(r''+excl+'', fn):
continue

# Fusionstorage_oam_1.0.0.debug.20180327010002.tar.gz
# Fusionstorage_oam_1.0.0.20180327010002.tar.gz
# Fusionstorage_oam_1.0.0_20180327010002.tar.gz
# Fusionstorage_oam_1.0.0.release.20180327010002.tar.gz
# Fusionstorage_oam_1.0.0.valgrind.20180327010002.tar.gz
# Fusionstorage_oam_1.0.0_20180327010002_release.tar.gz
# Fusionstorage_oam_1.0.0.20180327010002_release.tar.gz
# luomingzhi add 2018-08-04 15:37
# Fusionstorage_base_1.0.0.mock.20180327010002.tar.gz

timestamp = fn.split('_')[-1].replace('.tar.gz', '').split('.')[-1]

if not timestamp.isdigit():
# 如果不是再继续判断下是不是package_type的标签在最后的.
timestamp = fn.split('_')[-2].split('.')[-1]
if not timestamp.isdigit():
if re.search(r'^FusionStorage_8\.0\.(RC\d+|\d+|\w+\d+)\.tar\.gz', fn):
timestamp = "%s" % time.time()
else:
continue

for _p in PACKAGE_TYPES:
if re.search(r''+_p+'', fn):
if timestamp not in _pf[_p]:
_pf[_p][timestamp] = [fn]
else:
_pf[_p][timestamp].append(fn)
break
else:
# 类型不在定义中的都认为是debug包
if 'FusionStorage_8.0' in fn:
if timestamp not in _pf['release']:
_pf['release'][timestamp] = [fn]
else:
_pf['release'][timestamp].append(fn)
elif "8.0.RC2" in fn:
if timestamp not in _pf['release']:
_pf['release'][timestamp] = [fn]
else:
_pf['release'][timestamp].append(fn)
else:
if timestamp not in _pf['debug']:
_pf['debug'][timestamp] = [fn]
else:
_pf['debug'][timestamp].append(fn)

fns = _pf[package_type] if _pf[package_type] else _pf['debug']

return fns

fns = __generate_fns(include, exclude)
# 获取最新的文件
retFn = None
timestamp = '0'
for t in fns:
if t >= timestamp:
timestamp = t
retFn = fns[t][0]
if retFn is None:
self.run({"command": ['quit']})
raise CommandException("Have not specify file, please check return message, include words: %s, "
"package_type: %s, package_path: %s." % (fnPattern, package_type, path))
# if '/stash' in path:
# # if ip in ['100.99.87.75', '100.99.115.122']:
# self.run({"command": ['quit']})
# cmd['command'] = ["wget -P %s http://100.99.118.157%s%s" % (target, path, retFn)]
if ip in ['100.99.87.75', '100.99.115.122']:
self.run({"command": ['quit']})
_c = """export ec=18; while [ $ec -eq 18 ]; do curl -C - -o %s/%s -L http://100.99.118.157%s%s; export ec=$?; done""" % (target, retFn, path, retFn)
cmd['command'] = [_c]
elif ip in ["10.249.33.153", "8.46.21.162", "8.41.203.229", "8.76.0.161", "8.34.0.179", "8.39.255.5", "15.0.4.63"]:
self.run({"command": ['quit']})
_c = """export ec=18; while [ $ec -eq 18 ]; do curl -C - -o %s/%s -L http://%s:81%s%s; export ec=$?; done""" % (
target, retFn, ip, path, retFn)
cmd['command'] = [_c]
# cmd['command'] = ["wget --timeout=3600 -P %s http://100.99.118.157%s%s" % (target, path, retFn)]
else:
cmd['command'] = ["get %s %s" % (retFn, target)]
#cmd['command'] = ["get %s %s" % (retFn, target)]
cmd['timeout'] = 3600
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Download file %s failed." % retFn)
params = {
"command": ['quit'],
}
self.run(params)
return fnPattern

def sftpGetLastAgentUpgradeFile(self, ip, port, user, password, path, fnPattern, target, timeout=1200,
package_type='debug'):
"""获取指定sftp服务器上的文件到主机
"""
# login
cmd = "sftp -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -P {0} {1}@{2}".format(port, user, ip)
params = {
"command": [cmd],
"input": [password, "sftp>"],
"waitstr": "assword:",
"timeout": timeout,
}
ret = self.run(params)
if ret['rc'] != 0:
raise CommandException("Connected to sftp: %s failed." % ip)
cmd = {"command": ['cd %s' % path],
"waitstr": "sftp>",
"timeout": timeout}
# change to source directory
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Change directory to %s failed." % path)
# ls all file
cmd["command"] = ['ls -1t']
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Show directory file failed.")

if ret.get('stdout') is None:
self.run({"command": ['quit']})
raise CommandException("Show directory file failed.")
lines = self.split(ret.get('stdout'))

release = {}
debug = {}
valgrind = {}
mock = {}
for l in lines:
l = re.sub(r'\s.*', ' ', l)
# get file name
fn = l.split(' ')[-1]
if not fn.endswith('.zip'):
continue
if not re.search(r'' + fnPattern + '', fn):
continue
# FusionStorage_Block_1.0.0.20180717170456_Agent_Upgrade.zip
timestamp = fn.split('_')[2].split('.')[-1]

if not timestamp.isdigit():
continue
if re.search(r'release', fn):
release[timestamp] = fn
elif re.search('valgrind', fn):
valgrind[timestamp] = fn
elif re.search('mock', fn):
mock[timestamp] = fn
else:
debug[timestamp] = fn

if package_type == 'release':
fns = release if release else debug
elif package_type == 'valgrind':
fns = valgrind if valgrind else debug
elif package_type == 'mock':
fns = mock if mock else debug
else:
fns = debug
# 获取最新的文件
retFn = None
timestamp = '0'
for t in fns:
if t > timestamp:
timestamp = t
retFn = fns[t]
if retFn is None:
self.run({"command": ['quit']})
raise CommandException("Have not specify file, include words: %s." % fnPattern)

cmd['command'] = ["get %s %s" % (retFn, target)]
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Download file %s failed." % retFn)
params = {
"command": ['quit'],
}
self.run(params)

def getPlogManagerNodesInfo(self, destId=None, destIp=None, destPort=None, destMid='8', commandType='181', useDIcmd=None):
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
info = self.getPlogManagerMasterInfo(useDIcmd=useDIcmd)

def get_specified_node_role(identity, ip, port, mid='8', commandType='149'):
"""查询节点的角色
"""
tmp = self._insight(nodeType='0', destId=identity, destIp=ip, destPort=port, destMid=mid,
commandType=commandType, useDIcmd=useDIcmd)
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
commandType=commandType,
useDIcmd=useDIcmd
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

def getPlogClientNodesInfo(self, destId=None, destIp=None, destPort=None, destMid='8', commandType='110', useDIcmd=None):
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
info = self.getPlogManagerMasterInfo(useDIcmd=useDIcmd)
info = self._insight(
nodeType='0',
destId=destId if destId else info['identity'],
destIp=destIp if destIp else info['ip'],
destPort=destPort if destPort else info['port'],
destMid=destMid,
commandType=commandType,
parameter=" |sed '1d'|sed 's/|/ /g'|tr -s ' '|awk '{print and(0xffff, $2), $0}'",
useDIcmd=useDIcmd
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

cmd = "sftp -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -P {0} {1}@{2}".format(port, user, ip)
params = {
"command": [cmd],
"input": [password, "sftp>"],
"waitstr": "assword:",
"timeout": timeout,
}
result = self.run(params)

for f in files:
cmd = "get %s %s" % (f, target)
params = {
"command": [cmd],
"waitstr": 'sftp>',
"timeout": timeout,
}
self.run(params)
params = {
"command": ['quit'],
}
self.run(params)


def registerCliWrapper(self):
"""
注册CLI wrapper
"""
#TODO mock版本，目前没有版本信息这些内容，后边别忘了修改
from UniAutos.Wrapper.Template.RocCLI import RocCliWrapper
wrapper = RocCliWrapper()
self.registerToolWrapper(host=self, wrapper=wrapper)


def runNewWrapper(self, methodName, params, interactRule=None, option=None, interrupt=0):
"""
Overwrite UniAutos.Dispatcher.runNewWrapper method to avoid the conflict with OceanStor way

Changes:
2016-05-10 y00292329 Created

"""
dispatching = None
try:
if interrupt != 0:
dispatching = self.markAsDispatching()
wrapperList = filter(
lambda x: x.get("wrapper_type", None) == 'UniAutos.Wrapper.Template.RocCLI.RocCliWrapper',
self.wrapper_list)


cliWrapper = wrapperList[0].get('wrapper')
result = cliWrapper.runWrapper(methodName, params,interactRule, option)
return [result]
finally:
if dispatching:
dispatching()


@classmethod
def createTemporaryNode(cls,login_params, wrapper_list=[],cliType='debug',view_params=None, info=None):
"""
创建指定用户登录的RocNode对象，目前的主要需求是用新建的对象来dispatch命令
Args:
login_params (dict): 包含下面几个参数
ip (str): 登录IP
port (int|str): 登录端口号 ,默认22
username (str): 登录用户名，默认root
password (str): 登录密码，默认huawei@123
wrapper_list(list): 从已有的rocnode对象获取
cliType (str): （可选）默认debug， 可选admincli
view_params (dict): 包含下面几个参数，需要切换视图时使用
username (str): 要登录视图的用户名，如superAdmin
password (str): 要登录的视图的密码
newpassword (str): (可选) 初次登录可能要设置新密码

Returns:

"""

params = {
"type": 'rocSSH',
"os": 'Linux',
"port": str(login_params.get('port',22)),
"ipv4_address": login_params.get('ip'),
"username": login_params.get('username',"root"),
"password": login_params.get('password',"huawei@123")
}
if info:
if info.get('ipv4_address'):
info.pop('ipv4_address')
params.update(info)
if params.get('command'):
params.pop('command')
obj = RocNode.discover(params)
# 复制wrapper对象
for wrapper in wrapper_list:
obj.registerToolWrapper(host=obj, wrapper=wrapper['wrapper'])

if cliType == 'admincli':
obj.changeLoginAdminCliUser(view_params.get('username'), view_params.get('password'), view_params.get('newpassword'))

return obj

def changeLoginAdminCliUser(self, username, password, newpassword=None):
"""
更改当前登录admincli的用户
Args:
username (str): 用户名
password (str): 密码
newpassword (str): (optional) 第一次登录的时候可能需要输入新密码

Examples:
self.node.changeLoginAdminCliUser(username, password, newpassword)

"""
cmd = self.getCmdObj() # connectionPool对象
con = cmd.getConnection()
if newpassword:
con.chgmodel('admincli', username=username, password=password, newpassword=newpassword)
else:
con.chgmodel('admincli', username=username, password=password)

cmd.connectionPool[con.username].put(con)


@classmethod
def createDocker(cls, node, port, username, password, type='rocSSH', os='Linux'):
"""
在宿主机上发现docker对象(本质也是个RocNode对象)
此AW不会创建和运行docker，只会把已经运行的指定docker对象找出来
Args:
node (RocNode): roc node对象
port (str): docker 端口
username (str): docker 用户名
password (str): docker 密码
type (str): 通信类型 ["rocSSH","storSSH", "standSSH", "local", "telnet", "xmlrpc"]，默认rocSSH
os: (str): os类型，默认Linux

Returns:
dockerObj: 找到的docker对象

Examples:
self.dockerNode = RocNode.createDocker(self.node, port=tbInfos['docker_port'],
username=tbInfos['docker_user'],
password=tbInfos['docker_password'])

"""

if not node or not port or not username or not password:
raise UniAutosException('Create docker params empty, please check your params.')

if port in node.dockers.keys():
docker = node.dockers.get(port)
docker.reconnect() # 获取就重置一下连接，因为会有case主动杀掉视图的进程如admincli
return docker
else:
params = {
"type": type,
"port": port,
"ipv4_address": node.localIP,
"os": os,
"username": username,
"password": password,
}
dockerObj = RocNode.discover(params)

for wrapper in node.getWrapper():
dockerObj.registerToolWrapper(host=dockerObj, wrapper=wrapper['wrapper'])

# 保存docker对象到roc_node内部
node.dockers[port] = dockerObj

return dockerObj

def reconnect(self):
"""
重置当前node的连接信息
Examples:
docker.reconnect()
"""
cmd = self.getCmdObj() # connectionPool对象
con = cmd.getConnection()
if con.view == 'diagnose':
con.execCommand('exit', '@#>') # 显示退出diagnose，通知产品端进行清理，否则可能会出现登录人数过多导致登录失败
cmd.restoreConnectInfo()

def dispatch(self, method, params=None, interactRule=None, option=None):
""""
为roc node重写的dispatch方法，会调用父类(Dispatcher)的dispatch方法

Args:
methodName (str): 命令名称
params (dict): 命令所需参数
interactRule (dict): 交互输入。如过匹配到字典的key值，就输入字典的value
option (dict): 命令收发控制参数，控制命令超时时间，sessionType等

Returns:
dockerObj: 发现的docker对象

Examples:
result = self.fsm.dispatch('queryManageCluster', params={'zkRoleFlag': True, 'flag': 'true'})

"""
return super(RocNode, self).dispatch(method, params, interactRule, option)

def delUser(self, name=None, uid=None):
"""
删除指定的name或uid的用户
Args:
name (str): (optional) 用户名
uid (str): (optional) 用户id

Returns:
None

Examples:
fsm.delUser(uid='1000')

"""
users = self.listAllUser()
if uid:
name = users.get('uid', {}).get('name')
if name not in [v['name'] for k, v in users.iteritems()]:
self.logger.info("user: %s not exist." % name)
return

self.run({"command": ['userdel %s' % name]})
users = self.listAllUser()

if name in [v['name'] for k, v in users.iteritems()]:
raise UniAutosException("Canot delete user: %s, uid: %s" % (name, uid))

def getLastCmdExitCode(self):
"""
roc节点获取上一个命令执行的ret code

Returns:
执行成功返回0，否则为非0

Examples:
ret_code = self.node.getLastCmdExitCode()

"""
result = self.run({'command': ['echo $?'],
'timeout': 40})

raw = result['stdout'] if result['stdout'] else result['stderr']
if raw:
l = self.split(raw)
if len(l) == 3 and l[1].isdigit():
return int(l[1])
elif len(l) == 2 and l[0].isdigit():
return int(l[0])
return 0


def prepareIscsiForIo(self, host_ip, host_port, host_name, port_name, volume_list, dsware_params=None):
"""
下IO前准备Iscsi的动作，使用dswareinsight下发命令

Args:
host_ip: 本地IP
host_port: 本地端口
host_name: iscsi主机名称
port_name: IO目标启动器名称
volume_list: 本地volume列表
dsware_params: 下发给wrapper的参数，现在是一定要给的

Returns:
成功True，失败False

Examples:
logger.info('pre step 2.2： prepare iscsi')
ret = self.vbs_node.prepareIscsiForIo(host_ip=self.vbs_node.localIP,
host_port=3260, host_name='host0', port_name=self.getParameter('port_name')['port_name'],
volume_list=self.volume_names, dsware_params=self.dswareinsight_params)
if not ret:
raise UniAutosException('Something wrong when prepare iscsi for IO.')

"""
params = {'switch': 'open'}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('iscsiSwitch', params=params)
if not res[0]['parser']:
log.error('can not open iscsi switch')
return False

params= {'ip': host_ip, 'port': str(host_port)}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('addIscsiPortal', params=params)
if not res[0]['parser']:
log.error('can not add iscsi portal')
return False

params = {'port_name': port_name}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('createIscsiInitiator', params=params)
if not res[0]['parser']:
log.error('can not create iscsi initiator')
return False

params = dict()
if dsware_params:
params = dsware_params
initiators = self.dispatch('searchIscsiInitiator', params=params)
initiator_created = False
for initiator in initiators[0]['parser'].values():
if initiator['port_name'] == port_name:
initiator_created = True
break
if not initiator_created:
log.error('can not create iscsi initiator')
return False

params = {'host_name': host_name}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('createIscsiHost', params=params)
if not res[0]['parser']:
log.error('can not create iscsi host')
return False

params = {'host_name': host_name, 'port_name': [port_name]}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('addIscsiHostPort', params=params)
if not res[0]['parser']:
log.error('can not add iscsi host port')
return False

params = {'host_name': host_name, 'volume_name': volume_list}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('mapIscsiVolume', params=params)
if not res[0]['parser']:
log.error('can not map iscsi volume')
return False

return True

def cleanIscsiForIo(self, host_name, port_name, volume_list, dsware_params=None):
"""
下io后清理iscsi，使用dswareinsight，是prepareIscsiForIo的逆操作

Args:
host_name (str): iscsi 主机名称
port_name (str): IO目标启动器名称
volume_list (list): 本地volume列表
dsware_params (dict): (optional)传给wrapper的参数

Returns:
成功True，失败False

Examples:
ret = self.vbs_node.cleanIscsiForIo(host_name='host0', port_name=self.getParameter('port_name')['port_name'],
volume_list=self.volume_names, dsware_params=self.dswareinsight_params)

"""
result = True

params = {'host_name': host_name, 'volume_name': volume_list}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('unmapIscsiVolume', params=params)
if not res[0]['parser']:
log.error('can not unmap iscsi volume')
result = False

params = {'host_name': host_name, 'port_name': [port_name]}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('removeIscsiHostInitiator', params=params)
if not res[0]['parser']:
log.error('can not remove iscsi host initiator')
result = False

params = {'host_name': host_name}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('deleteIscsiHost', params=params)
if not res[0]['parser']:
log.error('can not remove iscsi host initiator')
result = False

params = {'port_name': port_name}
if dsware_params:
params.update(dsware_params)
res = self.dispatch('deleteIscsiInitiator', params=params)
if not res[0]['parser']:
log.error('can not delete iscsi initiator')
result = False

return result


def reboot(self, delay=5, wait=False, runTimeout=10, timeout='30M', recv_return=False, fastReboot=True):
"""
重启linux host

Args:
delay (int): (optional) 发送reboot命令之后，是否要sleep一段时间，默认是5秒
wait (bool): (optional) reboot之后是否要等待重启完成再返回，默认False
runTimeout (int): (optional) reboot命令发送的超时时间，默认10秒
timeout (str): (optional) 等待重启完成的超时时间，默认等待30M
recv_return (bool): (optional) 只发送重启命令，不接收回显，默认False（此参数不需要修改）
fastReboot (bool): (optional) 是否在reboot的时候加入 -f 参数，默认True

Returns:
True|False: 成功还是失败

Examples:
self.node.reboot(wait=True) # 重启并等待重启完成
self.node.reboot() # 重启且不等待，命令下发后直接返回

"""
timeoutNum = int(Units.getNumber(Units.convert(timeout, 'S')))
self.logger.info('host[%s] is rebooting' % self.localIP)
if fastReboot == True:
command = ["sh", "-c", "reboot -f"]
else:
command = ["sh", "-c", "reboot"]
result = self.run({"command": command, "timeout": runTimeout, 'recv_return': recv_return})
sleep(delay)
if wait:
self.waitForReboot(timeout=timeoutNum)
if result['rc'] != 0:
return False
return True


def waitForReboot(self, waitForShutdown=True, timeout=3600):
"""Waits for Node to come back from a reboot

Args:
waitForShutDown (Boolean): (Optional) Set to true to wait for the Node to shutdown first. (Default = True).
timeout (int) : (Optional) Amount of time to wait for reboot, unit is "S"
(Default: 3600).

Raises:
UniAutosException.

Examples:
self.waitForReboot(timeout=timeoutNum)

"""
self.log.debug("Waiting for the controller %s to finish rebooting" % self.localIP)
endTime = time.time() + timeout

# If specified, wait for the system to shutdown
if waitForShutdown:
self.log.debug("Waiting for the controller %s to complete shutdown" % self.localIP)
self.waitForShutdown(timeout=timeout)
self.log.debug("controller %s is shutdown" % self.localIP)

self.log.debug("Waiting for the controller %s to come up" % self.localIP)
while True:
if self.isReachable():
self.waitForSshRaiseUp()
self.restoreCmdObj()
if self.canCommunicate():
break
sleep(10)
if time.time() > endTime:
raise UniAutosException("Timed out waiting for reboot [ip: %s]"
"\n(Timed out while waiting for the system to come up" % self.localIP)


def waitForSshRaiseUp(self, timeout=600):
"""
等待节点22端口监听起来
Args:
timeout (int): 超时时间

Returns:
True ： 22端口起来

Exception:
如果timeout时间到了，就会抛异常出来

"""
self.logger.info("Let's check about the ssh status on this node %s." % self.localIP)
start = time.time()
times = 0
while time.time() < start + timeout:
try:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((self.localIP, 22))
self.logger.info("The %s 22 port is listening, should be OK, will return right now." % self.localIP)
return True
except (socket.error, EOFError, BaseException) as e:
self.logger.warn(e, 'Wait for ssh raised up failed the %s time' % times)
sleep(10)
times += 1
finally:
if sock:
sock.close()

raise UniAutosException('Ssh service does not raise up in host %s in %s seconds' % (self.localIP, timeout))


def canCommunicate(self):
"""
Checks to see if we can communicate with remote host by attempting to send a test command

Returns:
True|False: True- Able to communicate
False- Unable to communicate

Examples:
if node.canCommunicate():
#do sth here

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

def sftpGetReplicationLastFile(self, ip, port, user, password, path, fnPattern, target, timeout=1200,
package_type='debug', include=None, exclude=None):
"""
获取指定sftp服务器上的文件到主机（更多具体例子请在部署脚本中查找）
Args:
ip (str): 目前IP
port (str): 目前port
user (str): 用户名
password (str): 密码
path (str): 路径
fnPattern (str): 包含正则的字符串
target (str): 目标路径
timeout (int): (optional) 超时时间，默认1200S

Examples:
node.sftpGetReplicationLastFile(ip=sftp_ip,
port='22',
user=SFTP_USER if not self.sftp_address else self.sftp_user,
password=SFTP_PASS if not self.sftp_address else self.sftp_password,
path=path,
fnPattern='FusionStorage.*_replication_\d+.zip',
target='/root')

"""
# login
PACKAGE_TYPES = ['release', 'debug', 'valgrind', 'mock', 'perf']
if package_type not in PACKAGE_TYPES:
package_type = 'debug'
cmd = "sftp -o 'UserKnownHostsFile=/dev/null' -o 'StrictHostKeyChecking=no' -P {0} {1}@{2}".format(port, user, ip)
params = {
"command": [cmd],
"input": [password, "sftp>"],
"waitstr": "password:",
"timeout": timeout,
}
ret = self.run(params)
if ret['rc'] != 0:
raise CommandException("Connected to sftp: %s failed." % ip)
cmd = {"command": ['cd %s' % path],
"waitstr": "sftp>",
"timeout": timeout}
# change to source directory
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Change directory to %s failed." % path)
# ls all file
cmd["command"] = ['ls -1t']
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Show directory file failed.")

if ret.get('stdout') is None:
self.run({"command": ['quit']})
raise CommandException("Show directory file failed.")
lines = self.split(ret.get('stdout'))

fns = {}
_pf = {_p: {} for _p in PACKAGE_TYPES}

# 如果有查询到的包有dl，且指定了dl， 则流程不做任何变更
dl = False
if include is not None and isinstance(include, str):
for l in lines:
if re.search(r'' + include + '', l):
dl = True
break
# 如果查询到的包没有dl，则强制转换为非DL
if not dl:
include = None
exclude = 'dl'

for l in lines:
regex = re.search(r'('+fnPattern+')', l)
if not regex:
continue
fn = regex.groups()[0]
if not fn.endswith('.zip'):
continue

if include is not None:
if not re.search(r''+include+'', fn):
continue

if exclude is not None:
if re.search(r''+exclude+'', fn):
continue

# get file prefix, like: FusionStorage EVS V5 V100R007C00_replication_20180527170007.zip
# get file prefix, like: FusionStorage EVS V5 V100R007C00_replication_20180527170007_release.zip
timestamp = fn.split('_')[-1].replace('.zip', '').split('.')[-1]

if not timestamp.isdigit():
# 如果不是再继续判断下是不是package_type的标签在最后的.
timestamp = fn.split('_')[-2].split('.')[-1]
if not timestamp.isdigit():
continue

for _p in PACKAGE_TYPES:
if re.search(r''+_p+'', fn):
if timestamp not in _pf[_p]:
_pf[_p][timestamp] = [fn]
else:
_pf[_p][timestamp].append(fn)
break
else:
# 类型不在定义中的都认为是debug包
if timestamp not in _pf['debug']:
_pf['debug'][timestamp] = [fn]
else:
_pf['debug'][timestamp].append(fn)

fns = _pf[package_type] if _pf[package_type] else _pf['debug']

# 获取最新的文件
retFn = None
timestamp = '0'
for t in fns:
if t > timestamp:
timestamp = t
retFn = fns[t][0]
if retFn is None:
self.run({"command": ['quit']})
raise CommandException("Have not specify file, include words: %s." % fnPattern)

cmd['command'] = ["get '%s' %s" % (retFn, target)]
ret = self.run(cmd)
if ret['rc'] != 0:
self.run({"command": ['quit']})
raise CommandException("Download file %s failed." % retFn)
params = {
"command": ['quit'],
}
self.run(params)

def checkVbsInLdLibraryPath(self):
ret = self.run({"command": ["echo $LD_LIBRARY_PATH"], "ignore_error": True})
if '/opt/dsware/vbs/lib' not in ret['stdout'].split('\r\n')[0]:
self.run({'command': ['export LD_LIBRARY_PATH=/opt/dsware/vbs/lib:$LD_LIBRARY_PATH']})

def mountVolumes(self, nameList):
"""
将namelist中指定volume，mount到当前node上（必须是fsa节点）
Args:
nameList (list): 要mount的volume name list，如['lun0','lun1']

Examples:
self.vbs_node.mountVolumes(self.lun_name_list)
"""
for name in nameList:
ret = self.dispatch('volumeMount', params={'volume_name': name})
flag = False
for line in reversed(ret[0]['parser']):
if re.search(r'Attach volume on .*, Success', line) or re.search(r'volume has been attached', line):
flag = True
break
if not flag:
raise UniAutosException('Mount lun:%s failed, please have a check.' % name)

def unMountVolumes(self, nameList):
"""
将namelist中指定的volume unmount(必须是fsa节点)
Args:
nameList (list): 要unmount的volume name list

Examples:
self.vbs_node.unMountVolumes(self.lun_name_list)
"""
for name in nameList:
ret = self.dispatch('volumeUnmount', params={'volume_name': name})
flag = False
for line in reversed(ret[0]['parser']):
if re.search(r'return code = 0, Success', line) or re.search(r'volume has not been attached', line):
flag = True
break
if not flag:
raise UniAutosException('Umount lun %s failed, please have a check' % name)

def calcParamsForVbs(self):
"""
生成vbs dswareinsight下发命令时所需要的参数

Returns:
(dict): 所需的参数值

Examples:
params = self.node.calcParamsForVbs()

"""
self.vbs_node_type = '2'
self.vbs_dest_port = '10901'
self.vbs_dest_mid = '14'

self.logger.info("Check vbs path in LD_LIBRARY_PATH or not.")
self.checkVbsInLdLibraryPath()

if not self.dsware_dest_ip or not self.dsware_dest_id:
# self.logger.info("Export LD_LIBRARY_PATH for vbs.")
# export_cmd = "export LD_LIBRARY_PATH=/opt/dsware/vbs/lib:$LD_LIBRARY_PATH"
# self.run({"command": [export_cmd]})

self.logger.info("Get vbs_dest_id for vbs.")
result = self.run({"command": [
r"""cat /opt/dsware/vbs/conf/vbs_*.*.*.*_conf.cfg | grep vbs_url | awk -F '=' '{printf $2}'|awk -F ':' '{printf "%s\n", $1}'"""]})
self.dsware_dest_id = result['stdout'].split('\r\n')[0]
# 对ID做过滤，可能会有逗号
if self.dsware_dest_id.startswith(',') or self.dsware_dest_id.endswith(','):
self.dsware_dest_id = self.dsware_dest_id.strip(',')
self.logger.info("The vbs_dest_id is %s" % self.dsware_dest_id)

self.logger.info("Get vbs_dest_ip for vbs.")
result = self.run({"command": [
r"""cat /opt/dsware/vbs/conf/vbs_*.*.*.*_conf.cfg | grep vbs_ip_2 | awk -F '=' '{printf $2}'| awk -F '@' '{printf "%s\n", $2}'"""]})
self.dsware_dest_ip = result['stdout'].split('\r\n')[0]
self.logger.info("The vbs_dest_ip is %s" % self.dsware_dest_ip)

return {'exec_path': '/opt/dsware/vbs/bin/dsware_insight', 'node_type': self.vbs_node_type, 'dest_id': self.dsware_dest_id,
'dest_ip': self.dsware_dest_ip, 'dest_port': self.vbs_dest_port,
'dest_mid': self.vbs_dest_mid}

def showLunIoByFtds(self, proceId, key=None):
"""使用FTDS查询lunio数量
:param proceId:进程id
:param key:字典格式的key，可以指定回显存在的key值
:return:字典格式数据
"""
command = ["/opt/fusionstorage/persistence_layer/agent/tool/ftds_stat show -p", proceId]
result = self.run({"command": command})['stdout'].split('\r\n')
parse = parseRocHorizontalList(rawOutput=result, key=key)
return parse

def checkDswarePoolStatus(self, poolID=None):
"""用DswareTool检查Pool状态
:param poolID: pool的ID
:return:如何正确返回True, 错误返回False
"""
result = False
params = {}
if poolID is not None:
params = {'poolId': poolID}
ret = self.dispatch('poolQueryUsageInfo', params)
for m in range(len(ret[0]['stdout'])):
if "Result Code:0" in ret[0]['stdout'][m]:
result = True
break
return result


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
toolObj = SdTester(self, True)

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
gRocInitToolsLock.acquire()
tool = getToolObj(toolName)
finally:
gRocInitToolsLock.release()

return tool

def getDiskDeviceName(self, lunComponent, timeout=300):
"""获取指定Lun对象映射到主机的设备名称

Args:
lunComponent (instance|list): lun对象.

Returns:
device (str|None): 映射的Lun对象的设备名称.
如果lunComponent为单个lun对象，返回值为该lun的盘符如 '/dev/sda'
如果lunComponenct为lun list，返回值为形如 ['/dev/sda', '/dev/sdb']

Raises:
CommandException: 命令执行失败.

Examples:
device = hostObj.getDiskDeviceName(lun)
or
device_list = hostObj.getDiskDeviceName(lun_list)

"""
start = time.time()
while time.time() < start + timeout:
try:
self.run({'command':['udevadm trigger']}) # 刷新scsi信息到/dev/disk/by-id add by g00414304 2018.12.08
result = self._getDiskDevice(lunComponent)
return result
except CommandException as e:
if e.message.startswith('No device name was found for lun '):
sleep(1)
else:
raise CommandException(e.message)

if isinstance(lunComponent, list):
luns = [n.getProperty('name') for n in lunComponent]
else:
luns = [lunComponent.getProperty('name')]
raise CommandException('Can not find lun dev name for luns: %s' % luns)


def _getDiskDevice(self, lunComponent):
"""获取指定Lun对象映射到主机的设备名称

Args:
lunComponent (instance | list): lun对象或者lun对象列表

Returns:
device (str|None): 映射的Lun对象的设备名称.

Raises:
CommandException: 命令执行失败.

Examples:
device = hostObj._getDiskDevice(lun)
Output:
>"/dev/sdb"

added by g00414304 2019.02.18

"""

response = self.run({"command": ["sh", "-c", "ls", "-l", "/dev/disk/by-id/"]})
if response["rc"] != 0 and not re.match(r'ls:\s+cannot\s+access\s+.*:\s+No\s+such\s+file\s+or\s+directory',
response["stderr"]):
raise CommandException(response["stderr"])

lines = self.split(response["stdout"])
if isinstance(lunComponent, list):
deviceList = []
for lun in lunComponent:
lunWwn = self.getLunWwn(lun) # 例如: 0x6888603000000001fa16a1705c6b2f32
device = None
for line in lines:
# 存在dm设备，wwn后十几位和lun相同，这里需要匹配整个wwn字符串
if re.search(r'' + str(lunWwn) + '', line):
tmpStr = self.trim(line)
tmpMatch = re.search(r'\/[\w-]+$', tmpStr)
if tmpMatch:
device = "/dev" + tmpMatch.group()
break
if device is not None:
deviceList.append(device)
else:
raise CommandException("No device name was found for lun with [id: %s], [wwn: %s]" %
(lun.getProperty('id'), lunWwn))
return deviceList
else:
lunWwn = self.getLunWwn(lunComponent)
device = None
for line in lines:
# 存在dm设备，wwn后十几位和lun相同，这里需要匹配整个wwn字符串
if re.search(r'' + str(lunWwn) + '', line):
tmpStr = self.trim(line)
tmpMatch = re.search(r'\/[\w-]+$', tmpStr)
if tmpMatch:
device = "/dev" + tmpMatch.group()
break
if device is not None:
return device
else:
raise CommandException("No device name was found for lun with [id: %s], [wwn: %s]" %
(lunComponent.getProperty('id'), lunWwn))


def getDeviceFault(self, ):
"""获取device的故障类型对象
Returns:
FaultType对象

Examples:
faultType = self.getDeviceFault()

"""
self.faultLock.acquire()
if self.fault is None:
self.fault = FaultType()
self.faultLock.release()
return self.fault


def getRepObjList(self, operation, component, property, findAll=False, cliType=None, controlClusterId=None):
"""功能：查找复制对象（建议双活、双活一致性、远程复制、远程复制一致性组才使用这个方法）

Args:
operation （func）查找使用的函数：device.find | device.waitForNewComponents
component （str）查找的对象
property （dict）指定特性属性查找特性对象
findAll （bool）是否查找所有对象，适用于复制对象超过40个的场景
cliType （str）cli类型："admincli" | "dswaretool"
controlClusterId （str）控制集群ID
Returns:
repObjListAll
"""

repObjListAll = []
# 查找指定对象
criteria = {}
if cliType == 'admincli':
criteria['cliType'] = 'admincli'
else:
criteria['controlClusterId'] = controlClusterId
criteria['cliType'] = 'dswaretool'
startId = 0
criteria['startId'] = str(startId)
criteriaSpec = dict(criteria, **property)
parameterSpec = {'alias': component, 'criteria': criteriaSpec, 'forceSync': True, 'onlyNew': False}
if 'find' not in str(operation):
parameterSpec = {'types': component, 'criteria': criteriaSpec}

if findAll == True:
# 查找所有对象
parameterAll = {'alias': component, 'criteria': criteria, 'forceSync': True, 'onlyNew': False}
if 'find' not in str(operation):
parameterAll = {'types': component, 'criteria': criteria}
repObjList = operation(**parameterAll)
while len(repObjList) == 40:
repObjList = operation(**parameterSpec)
if repObjList:
repObjListAll += repObjList
startId += 40
criteria['startId'] = str(startId)
repObjList = operation(**parameterAll)
else:
repObjList = operation(**parameterSpec)
if repObjList:
repObjListAll = repObjList
return repObjListAll


def find(self, alias, forceSync=False, onlyNew=False, criteria=None,
createByConfigureEnv=False, onlyConfigureEnv=False, validatedByConfigureEnv=False):
"""
为了适配现在的命令下发在fsm，而查找对象在fsa的情况
will deprecated later
"""
region = self.getAvailableZone().getRegion()
fsm_device = region.getSpecifyServiceNode('fsm')[0]
the_node = self

if self == fsm_device and (alias == 'Snapshot' or alias == 'Lun'):
the_node = region.getSpecifyServiceNode('fsa')[0]

criteriaDictCp = None
if (criteria is not None) and (criteria.keys() == ['cliType']):
import copy
criteriaDictCp = copy.copy(criteria)
criteria = None
elif (criteria is not None) and ('cliType' in criteria.keys()):
import copy
criteriaDictCp = copy.copy(criteria)
criteria.pop('cliType')

wrapperDictCp = None
for wrapperDict in self.wrapper_list:
if (criteriaDictCp is not None) and ('cliType' in criteriaDictCp.keys()):
if ((criteriaDictCp['cliType'] == 'admincli') and
('UniAutos.Wrapper.Tool.Roc.RocCli.RocCli' == wrapperDict['wrapper_type'])):
wrapperDictCp = wrapperDict
self.wrapper_list.remove(wrapperDict)
elif ((criteriaDictCp['cliType'] == 'dswaretool') and
('UniAutos.Wrapper.Tool.Roc.AdminCli.AdminCli.AdminCli' == wrapperDict['wrapper_type'])):
wrapperDictCp = wrapperDict
self.wrapper_list.remove(wrapperDict)

ret = super(RocNode, the_node).find(alias=alias, forceSync=forceSync, onlyNew=onlyNew, criteria=criteria,
createByConfigureEnv=createByConfigureEnv, onlyConfigureEnv=onlyConfigureEnv,
validatedByConfigureEnv=validatedByConfigureEnv)

if wrapperDictCp is not None:
self.wrapper_list.append(wrapperDictCp)

return ret


def waitProcessUp(self, name=None, id=None, timeout=300):
"""
等待节点上的进程恢复
:param name: 和id必须2选1
:param id: 和name必须2选1
:return:
"""
if not name and not id:
raise UniAutosException('Must specify name or id when wait process up')

start = time.time()
ret = None
while time.time() - start < timeout:
if name:
ret = self.getProcessId(name)
elif id:
ret = self.getProcessInfo(id)
if ret:
log.info('Process up after wait %s seconds, the process info is %s' % (time.time()-start, ret))
return True
time.sleep(1)

info = name if name else id
raise UniAutosException('The process %s still not up after wait %s seconds' % (info, timeout))


def dd(self, diskDevice='/dev/sdb', of='/dev/null', skip=None, seek=None, bs=None, count=None, iflag=None,
oflag=None):
"""
DD zhe disk。

Args:
diskDevice (str)|（SnapshotBase|LunBase）: read from FILE instead of stdin，(支持盘符传递和映射对象去自助获取盘符)
of (str): write to FILE instead of stdout
skip (str): skip BLOCKS ibs-sized blocks at start of input
seek (str): skip BLOCKS obs-sized blocks at start of output
bs (int): read and write up to BYTES bytes at a time
count (int): copy only BLOCKS input blocks
iflag=FLAGS：指定读的方式FLAGS，参见“FLAGS参数说明”
oflag=FLAGS：指定写的方式FLAGS，参见“FLAGS参数说明”
"""

from UniAutos.Component.Lun.LunBase import LunBase
from UniAutos.Component.Snapshot.Huawei.OceanStor.Lun import Snapshot as SnapshotBase
from UniAutos.Component.Volume.Huawei.DSware import Volume
if isinstance(diskDevice, LunBase) or isinstance(diskDevice, SnapshotBase) or isinstance(diskDevice, Volume):
diskDevice = self._getDiskDevice(diskDevice)
command = ["sh", "-c", "dd", "if=%s" % diskDevice, "of=%s" % of]
if skip is not None:
command.append('skip=%s' % skip)
if seek is not None:
command.append('seek=%s' % seek)
if bs is not None:
command.append('bs=%s' % bs)
if count is not None:
command.append('count=%s' % count)
if iflag is not None:
command.append('iflag=%s' % iflag)
if oflag is not None:
command.append('oflag=%s' % oflag)
self.run({"command": command})


def compareData(self, srcobj, dstobj, srcoffset=None, dstoffset=None, srclength=None, dstlength=None, timeout=None):
"""
对两个文件进行数据比较,数据不一致会保留当前环境，以便定位

Args:
src (obj/str): 比较源数据对象，lun或者snapshot对象或者文件系统路径
dst (obj/str): 比较目标数据对象，lun或者snapshot对像或者文件系统路径
srcoffset (str): 源LUN偏移量 与 dstoffset，否则无效
dstoffset (str): 目标LUN偏移量 与 srcoffset，否则无效
srclength (str): 源LUN偏长度
dstlength (str): 目标LUN偏长度
timeout (int|str): cmp超时时间
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
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Component.Lun.LunBase import LunBase
from UniAutos.Component.Snapshot.Huawei.OceanStor.Lun import Snapshot as SnapshotBase
from UniAutos.Component.Volume.Huawei.DSware import Volume
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
if isinstance(src, LunBase) or isinstance(src, SnapshotBase) or isinstance(src, Volume):
srcDiskDevice = self._getDiskDevice(src)
else:
srcDiskDevice = src

source_lun_id = ""
if isinstance(src, LunBase):
source_lun_id = src.getProperty("id")
elif isinstance(src, SnapshotBase):
source_lun_id = src.getProperty('source_lun_id')

target_lun_id = ""
if isinstance(dst, LunBase):
target_lun_id = dst.getProperty("id")
elif isinstance(dst, SnapshotBase):
target_lun_id = dst.getProperty('source_lun_id')

if isinstance(dst, LunBase) or isinstance(dst, SnapshotBase) or isinstance(dst, Volume):
dstDiskDevice = self._getDiskDevice(dst)
else:
dstDiskDevice = dst
# 执行清cache操作
self.run({"command": ['sh', '-c', "sync"]})
self.run({'command': ['sh', '-c', 'echo 1', '>', '/proc/sys/vm/drop_caches']})
self.run({'command': ['sh', '-c', 'echo 2', '>', '/proc/sys/vm/drop_caches']})
self.run({'command': ['sh', '-c', 'echo 3', '>', '/proc/sys/vm/drop_caches']})
self.run(
{"command": ['sh', '-c', 'sync', '&&', 'echo 3', '>', '/proc/sys/vm/drop_caches', '&&', 'sleep 2']})
# 构造命令下发参数
if srcoffset and dstoffset:
if srclength and dstlength:
command = ["sh", "-c", "cmp", srcDiskDevice, dstDiskDevice, "-i", str(srcoffset), "-n",
str(srclength)]
else:
command = ["sh", "-c", "cmp", "-i", str(srcoffset) + ":" + str(dstoffset), srcDiskDevice,
dstDiskDevice, ]
else:
command = ["sh", "-c", "cmp", srcDiskDevice, dstDiskDevice]
if timeout is None:
cmd_dict = {"command": command}
else:
cmd_dict = {"command": command, "timeout": int(timeout)}
result = self.run(cmd_dict)
if result['stderr']:
raise CommandException(str(result['stderr']))
else:
# 当stdout不为None且differ显示的数量不为0，数据不一致
if result['stdout'] and 'differ:' in result['stdout']:
self.logger.error("Data consistent compare failed between source lun: %s and target lun: %s" %
(source_lun_id, target_lun_id))
raise UniAutosException('It\'s data inconsistent between the specified files.')
self.logger.info("Data consistent compare passed between source lun: %s and target lun: %s" %
(source_lun_id, target_lun_id))
else:
raise InvalidParamException

def createBitmap(self, bitmapName, toSnapName, fromSnapName=None):
"""
创建bitmap（必须是fsa节点）
Args:
bitmapName (str):bitmap名字
fromSnapName (str):(可选参数)最早创建的起始快照或者不填此时默认从根节点开始
toSnapName (str):中止的快照

Examples:
self.vbs_node.createBitmap(self.lun_name_list)
"""
if isinstance(toSnapName, object):
toSnapName = toSnapName.getProperty('name')
params = {'volume_name': bitmapName, 'to_snapName':toSnapName}
if fromSnapName:
if isinstance(fromSnapName, object):
fromSnapName = fromSnapName.getProperty('name')
params['from_snapName'] = fromSnapName
ret = self.dispatch('createBitmapInsight', params=params)
flag = False
for line in reversed(ret[0]['parser']):
if re.search(r'Create bitmap volume, return code.+snap_size.+bitmap_size.+block_size.+', line):
flag = True
break
if not flag:
raise UniAutosException('Crete Bitmap:%s failed, please have a check.' % bitmapName)

def createCloneBitmap(self, bitmapName, toSnapName, fromSnapName=None):
"""
创建bitmap（必须是fsa节点）
Args:
bitmapName (str):bitmap名字
fromSnapName (str):(可选参数)最早创建的起始快照或者不填此时默认从根节点开始
toSnapName (str):中止的快照

Examples:
self.ebsSlaveNode.createCloneBitmap(bitmapName=self.bitmapName, fromSnapName=self.snap1,toSnapName=self.clone_volume_name1)
"""
if isinstance(toSnapName, object):
toSnapName = toSnapName
params = {'volume_name': bitmapName, 'to_snapName': toSnapName}
if fromSnapName:
if isinstance(fromSnapName, object):
fromSnapName = fromSnapName
params['from_snapName'] = fromSnapName
ret = self.dispatch('createBitmapInsight', params=params)
flag = False
for line in reversed(ret[0]['parser']):
if re.search(r'Create bitmap volume, return code.+snap_size.+bitmap_size.+block_size.+', line):
flag = True
break
if not flag:
raise UniAutosException('Crete Bitmap:%s failed, please have a check.' % bitmapName)

def queryBitmap(self, bitmapName, poolId=None):
"""
创建bitmap（必须是fsa节点）
Args:
bitmapName (str):bitmap名字
poolId (int):(可选参数，兼容老版本保留) 资源池Id

Examples:
self.vbs_node.queryBitmap(bitmapName='veXT_0v0003225')
"""
params = {'volume_name': bitmapName}
if poolId:
params['Pool_id'] = poolId
ret = self.dispatch('QuerySingleBitmapInsight', params=params)
flag = False
for line in reversed(ret[0]['stdout']):
if re.search(r'Query volume , return code = 0, Success', line):
flag = True
break
if not flag:
raise UniAutosException('Query Bitmap:%s failed, please have a check.' % bitmapName)
else:
return ret[0]['parser']

def queryAllBitmap(self, poolId):
"""
创建bitmap（必须是fsa节点）
Args:
bitmapName (str):bitmap名字
poolId (int):(可选参数，兼容老版本保留) 资源池Id

Examples:
self.vbs_node.queryAllBitmap(poolId=0)
"""
params = {'Pool_id': poolId}
ret = self.dispatch('QueryAllBitmapInsight', params=params)
flag = False
for line in reversed(ret[0]['parser']):
if re.search(r'Query volume , return code = 0, Success', line):
flag = True
break
if not flag:
raise UniAutosException('Query Bitmap: Pool Id %s failed, please have a check.' % str(poolId))

@property
def internal_ip(self):
return self.information['inet_panels']['internal']['ipv4_address']

@property
def external_ip(self):
return self.information['inet_panels']['external']['ipv4_address']

def __repr__(self):
return "rocnode:{ip}".format(ip=self.localIP)

@property
def node_version(self):
try:
if self.__node_version is None:
self.__node_version = self.run({'command':['./dswareTool.sh --version']})['stdout'].split('\r')[0]
return self.__node_version
except Exception as e:
self.__node_version = None
return None
