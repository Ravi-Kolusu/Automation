
# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：该模块提供ESX系统相关功能，包括对VMware虚拟机的操作，ESX主机的管理的方法和属性

版权信息：华为技术有限公司，版本所有(C) 2008-2009

"""

import sys
import time
import re
import datetime
from UniAutos.Device.Host.Hypervisor.Vsphere import VSphere, HAS_VMOMI
from UniAutos.Device.Host.Linux import Linux
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Util.Time import repeat_timeout
from UniAutos.Util.Time import sleep
import os

try:
    from uniautos_esxlib.vmomiAdapter import VmomiAdapter
except ImportError:
    pass


class Esx(Linux):
    """
    Attributes:
    vCenter (VSphere): vSphere第三方库对象
    """


def __init__(self, username, password, params):
    """Esx主机类，继承于Linux类，该类主要包含ESX主机相关操作于属性
    -下面的Components类属于Esx主机类，包含Nice Name与Component Class Name:

    Nice Name Component Class Name
    ================================================================
    Disk UniAutos.Component.Virtualized.Disk.Vmware
    Datastore UniAutos.Component.Virtualized.Datastore.Vmware
    VritualMachine UniAutos.Component.Virtualized.VirtualMachine.Vmware

    -构造函数参数:
    Args:
    username (str): Linux主机登陆使用的用户名, 建议使用root用户.
    password (str): username的登陆密码.
    params (dict): 其他参数, 如下定义:
    params = {"protocol": (str),
    "port": (str),
    "ipv4_address": (str),
    "ipv6_address": (str),
    "os": (str),
    "type": (str)}
    params键值对说明:
    protocol (str): 通信协议，可选，取值范围:
    ["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
    port (int): 通信端口，可选
    ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
    ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
    os (str): 主机操作系统类型，可选
    type (str): 连接的类型

    Returns:
    esxObj (instance): Esx.

    Raises:
    None.

    Examples:
    None.

    """


super(Esx, self).__init__(username, password, params)
self.__vCenter = None
self.os = 'VMware_ESX'
self.esxHost = None
if HAS_VMOMI:
    self.vCenter = VSphere(username, password, params)
self.vCenter.login()


# self.esxHost = self.vCenter.get_host_system_byname(params['ipv4_address'])

def listVm(self):
    """list all virtualMachine on this esx host."""


vmList = []
if self.vCenter is not None:
    vmList = self.vCenter.list_all_vm()
return vmList


def changeMaxTransfer(self, value):
    """更改Esx最大传输速率为16M

    Args:
    value (str): 16M 16384 / 4M 4096 /256K 256

    Returns:
    True|False: True- 更改速率为16m成功
    False- 更改速率为16m失败

    Raises:
    CommandException:发生异常

    Examples:
    host.changeMaxTransfer4M():更改主机速率为16m

    """


try:
    response = self.run({"command": ["esxcfg-advcfg -s " + str(value) + " /DataMover/MaxHWTransferSize"]})
response = self.run({"command": ["esxcfg-advcfg -g /DataMover/MaxHWTransferSize"]})
lines = response['stdout']
if lines != 'Value of MaxHWTransferSize is ' + str(value):
    self.log.debug("MaxHWTransferSize change failed")
except Exception, e:
self.log.debug(e.message)
return False
return True


def vaai_hardwareAcceleratedMove(self, value):
    """打开vaai_hardwareAcceleratedMove开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.vaai_hardwareAcceleratedMove('1'):打开vaai_hardwareAcceleratedMove开关

    """


# change HardwareAcceleratedMove
hardwareAcceleratedMove = "esxcli system settings advanced set --int-value=" + str(
    value) + " --option /DataMover/HardwareAcceleratedMove"
response = self.run({"command": [hardwareAcceleratedMove]})
checkHardwareAcceleratedMove = "esxcli system settings advanced list --option /DataMover/HardwareAcceleratedMove"
try:
    response = self.run({"command": [checkHardwareAcceleratedMove]})
lines = response['stdout'].split('\r\n')[2].split(':')[1]
if lines.strip() != str(value):
    self.log.debug("HardwareAcceleratedMove change failed")
except Exception, e:
self.log.debug(e.message)
return False
return True


def vaai_hardwareAcceleratedLocking(self, value):
    """打开vaai_hardwareAcceleratedLocking开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.vaai_hardwareAcceleratedMove('1'):打开vaai_hardwareAcceleratedMove开关

    """


# change HardwareAcceleratedMove
hardwareAcceleratedMove = "esxcli system settings advanced set --int-value=" + str(
    value) + " --option /VMFS3/HardwareAcceleratedLocking"
response = self.run({"command": [hardwareAcceleratedMove]})
checkHardwareAcceleratedMove = "esxcli system settings advanced list --option /VMFS3/HardwareAcceleratedLocking"
try:
    response = self.run({"command": [checkHardwareAcceleratedMove]})
lines = response['stdout'].split('\r\n')[2].split(':')[1]
if lines.strip() != str(value):
    self.log.debug("HardwareAcceleratedLocking change failed")
except Exception, e:
self.log.debug(e.message)
return False
return True


def vaai_enableBlockDelete(self, value):
    """打开vaai_enableBlockDelete开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.vaai_hardwareAcceleratedMove('1'):打开vaai_enableBlockDelete开关

    """


# change EnableBlockDelete
enableBlockDelete = "esxcli system settings advanced set --int-value=" + str(
    value) + " --option /VMFS3/EnableBlockDelete"
response = self.run({"command": [enableBlockDelete]})
checkEnableBlockDelete = "esxcli system settings advanced list --option /VMFS3/EnableBlockDelete"
try:
    response = self.run({"command": [checkEnableBlockDelete]})
lines = response['stdout'].split('\r\n')[2].split(':')[1]
if lines.strip() != str(value):
    self.log.debug("EnableBlockDelete change failed")
except Exception, e:
self.log.debug(e.message)
return False
return True


def vaai_hardwareAcceleratedInit(self, value):
    """打开vaai_HardwareAcceleratedInit开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.vaai_hardwareAcceleratedMove('1'):打开vaai_HardwareAcceleratedInit开关

    """


# change HardwareAcceleratedInit
hardwareAcceleratedInit = "esxcli system settings advanced set --int-value=" + str(
    value) + " --option /DataMover/HardwareAcceleratedInit"
response = self.run({"command": [hardwareAcceleratedInit]})
checkHardwareAcceleratedInit = "esxcli system settings advanced list --option /DataMover/HardwareAcceleratedInit"
try:
    response = self.run({"command": [checkHardwareAcceleratedInit]})
lines = response['stdout'].split('\r\n')[2].split(':')[1]
if lines.strip() != str(value):
    self.log.debug("HardwareAcceleratedInit change failed")
except Exception, e:
self.log.debug(e.message)
return False
return True


def unmap_reclaim_space(self, volume_label):
    """在ESX6.0以前的主机上下发UNMAP指令

    Args:
    volume_label (str): datastore名称

    Returns:
    _unmap_log_file: 下发unmap成功后生成的日志文件

    Raises:
    CommandException:发生异常

    Examples:
    host.unmap_reclaim_space('unmap'):向数据存储unmap下发unmap并生成日志文件

    """


# 判断当前ESX的版本6.0,6.5还是其他版本，针对不同版本处理策略有差异
_unmap_cmd = "esxcli storage vmfs unmap --volume-label=" + volume_label
_unmap_log_file = '/tmp/%s.unmap.log' % time.strftime('%Y%m%d%H%M%S')
unmap_cmd = "nohup sh -c 'date && %s && date' 1>%s &" % (_unmap_cmd, _unmap_log_file)
check_unmap_cmd = "ps -c | grep '%s' | grep -v grep" % (_unmap_cmd)

try:
    self.run({"command": [unmap_cmd]})
# response = result['stdout'].split('\r\n')[2].split(':')[1]
time.sleep(5)
response = self.run({"command": [check_unmap_cmd]})
# response = result['stdout'].split('\r\n')
if response['stdout'] and not response['stderr']:
    self.log.debug("unmap started asyn on host %s success for datastore %s" % (self.localIP, volume_label))
else:
    self.log.debug("unmap started asyn on host %s fail " % self.localIP)
except Exception, e:
self.log.debug(e.message)
return None
# 返回临时日志文件
return _unmap_log_file


def get_unmap_interval(self, unmap_log_file):
    """从ESX6.0以前的主机上下发UNMAP指令后的日志文件中获取执行时间

    Args:
    unmap_log_file (str): unmap临时日志文件

    Returns:
    delta_time: unmap执行完成时间；如果是0则表明未完成

    Raises:
    CommandException:发生异常

    Examples:
    host.get_unmap_interval('/tmp/xxx.log'):向数据存储unmap下发unmap并生成日志文件

    """


# 在TIMEOUT时间范围内去查询该文件能够正确的返回2个时间戳
check_cmd = "cat %s " % unmap_log_file
response = self.run({"command": [check_cmd]})
delta_time = 0
# unmap执行命令失败，具体原因查看日志
if 'Intializing async unmap failed' in response['stdout']:
    raise Exception("Intializing async unmap failed on volume")
# unmap命令不支持，可能是本地硬盘或THICK LUN
if "do not support UNMAP" in response['stdout']:
    raise Exception("do not support UNMAP")
# 获取到unmap执行完成后的时间起止时间
time_list = re.findall(r'\d{2}:\d{2}:\d{2}', response['stdout'])
if not time_list:
    raise Exception("file not exist:%s ,unmap cmd sent fail" % unmap_log_file)
if len(time_list) == 1:
# unmap执行未完成重新执行
return delta_time
elif len(time_list) == 2:
# #任务完成后，解析为秒
str_start_time = time_list[0]
start_time = datetime.datetime.strptime(str_start_time, '%H:%M:%S')
str_end_time = time_list[1]
end_time = datetime.datetime.strptime(str_end_time, '%H:%M:%S')
delta_time = (end_time - start_time).total_seconds()
return int(delta_time)
else:
raise Exception("file not exist:%s,unmap cmd sent fail" % unmap_log_file)


def unmap_reclaim_datastore_space(self, datastore_name, timeout=3600, interval=60, is_wait=True):
    """to send unmap command to reclaim the datastore space

    Args:
    datastore_name (str): the datastore name

    Returns:
    duration (float): duration time

    Raises:
    CommandException:发生异常

    """


_unmap_cmd = 'esxcli storage vmfs unmap -l %s' % datastore_name
_unmap_log_file = '/tmp/%s.unmap.log' % time.strftime('%Y%m%d%H%M%S')
_running_cmd = 'nohup sh -c "date +%%Y-%%m-%%-d/%%H:%%M:%%S && %s && date +%%Y-%%m-%%-d/%%H:%%M:%%S" >%s 2>&1 &' \
               % (_unmap_cmd, _unmap_log_file)
response = self.run({"command": [_running_cmd], 'waitstr': '~]'})
sleep(5)
cat_cmd = 'cat %s' % _unmap_log_file
if response['rc'] is not None and response['rc'] != 0:
    error_msg = self.run({"command": [cat_cmd], 'waitstr': '~]'})
raise CommandException('running command[%s] error\nerror msg: %s' % (_running_cmd, error_msg['stdout']))
else:
if is_wait:
    @repeat_timeout('repeat get log file information')
    def repeat_cat_log_file(timeout, interval):


        log_msg = self.run({"command": [cat_cmd], 'waitstr': '~]'})
if log_msg['rc'] != 0 or log_msg['rc'] is None:
    return [False, log_msg]
else:
    time_list = re.findall(r'\d{4}-\d+-\d+/\d{2}:\d{2}:\d{2}', log_msg['stdout'])
if len(time_list) < 2:
# unmap执行命令失败，具体原因查看日志
if 'Intializing async unmap failed' in cat_result['stdout']:
    raise Exception("Intializing async unmap failed on volume")
# unmap命令不支持，可能是本地硬盘或THICK LUN
if "do not support UNMAP" in cat_result['stdout']:
    raise Exception("do not support UNMAP")
return [False, log_msg]
else:
return [True, log_msg]

cat_result = self.run({"command": [cat_cmd]})
log_msg = repeat_cat_log_file(timeout=timeout, interval=interval)[1]['stdout']
lines = log_msg.splitlines()
start_time = datetime.datetime.strptime(lines[0], '%Y-%m-%d/%H:%M:%S')
end_time = datetime.datetime.strptime(lines[1], '%Y-%m-%d/%H:%M:%S')
duration = (end_time - start_time).seconds
return duration
else:
return


def switchVaai(self, value):
    """打开VAAI开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.switchVaai('1'):打开VAAI

    """


result = self.vaai_enableBlockDelete(value)
if not result:
    raise CommandException('change UNMAP failed')
self.vaai_hardwareAcceleratedInit(value)
if not result:
    raise CommandException('change BLOCK ZERO failed')
self.vaai_hardwareAcceleratedLocking(value)
if not result:
    raise CommandException('change ATS failed')
self.vaai_hardwareAcceleratedMove(value)
if not result:
    raise CommandException('change FULL COPY failed')


def getHbaInfoCli(self):
    """获取主机HBA卡的信息


    Returns:
    hbaDict (dict): 主机HBA信息，hbaDict键值对说明:

    : {"port": ,
    "node": }
    port (str): hba卡port信息.
    node (str): hba卡node信息.


    Raises:
    CommandException: 命令执行失败.

    Examples:
    hbaInfo = hostObj.getHbaInfo()
    Output:
    >{'21:00:00:24:ff:49:99:e4': {'node': '20:00:00:24:ff:49:99:e4',
    'port': '21:00:00:24:ff:49:99:e4'},
    '21:00:00:24:ff:49:99:e5': {'node': '20:00:00:24:ff:49:99:e5',
    'port': '21:00:00:24:ff:49:99:e5'},
    '21:00:00:24:ff:54:3a:5a': {'node': '20:00:00:24:ff:54:3a:5a',
    'port': '21:00:00:24:ff:54:3a:5a'},
    '21:00:00:24:ff:54:3a:5b': {'node': '20:00:00:24:ff:54:3a:5b',
    'port': '21:00:00:24:ff:54:3a:5b'}}
    #增加status的状态
    '21:00:00:24:ff:54:3a:5b': {'node': '20:00:00:24:ff:54:3a:5b',
    'port': '21:00:00:24:ff:54:3a:5b'
    'status':'link-up'}


    """


response = self.run({"command": ["esxcli", "storage", "core", "adapter", "list", "|", "grep", "fc"]})
if response["rc"] != 0 and re.search(r'No such file or directory', response["stderr"]):
    self.logger.warn("No HBA card found on host.", self.getIpAddress())
return
elif response["rc"] != 0:
raise CommandException(response["stderr"])
lines = self.split(response["stdout"])
hba_dict = {}
for line in lines:
    if re.search(r'vmhba[0-9]', line):
        node = line.split()[3].replace('fc.', '').split(':')[0]
port = line.split()[3].replace('fc.', '').split(':')[1]
status = 'down'
name = ''
if re.search(r'link-up', line):
    status = 'up'
name = re.findall(r'vmhba[0-9]', line)[0]
hba_dict[port] = {"port": port,
                  "node": node,
                  "status": status,
                  "name": name}
return hba_dict


def getHbaInfo(self):
    """获取主机HBA卡的信息


    Args:
    ip (str): Esx主机的ip地址.
    username (str): Esx主机的登陆使用的用户名, 建议使用root用户.
    password (str): Esx主机的登陆密码.
    Returns:
    hbaDict (dict): 主机HBA信息，hbaDict键值对说明:

    : {"port": ,
    "node": }
    port (str): hba卡port信息.
    node (str): hba卡node信息.


    Raises:
    CommandException: 命令执行失败.

    Examples:
    hbaInfo = hostObj.getHbaInfo()
    Output:
    >{'21:00:00:24:ff:49:99:e4': {'node': '20:00:00:24:ff:49:99:e4',
    'port': '21:00:00:24:ff:49:99:e4'},
    '21:00:00:24:ff:49:99:e5': {'node': '20:00:00:24:ff:49:99:e5',
    'port': '21:00:00:24:ff:49:99:e5'},
    '21:00:00:24:ff:54:3a:5a': {'node': '20:00:00:24:ff:54:3a:5a',
    'port': '21:00:00:24:ff:54:3a:5a'},
    '21:00:00:24:ff:54:3a:5b': {'node': '20:00:00:24:ff:54:3a:5b',
    'port': '21:00:00:24:ff:54:3a:5b'}}

    """


self.esxHost = VmomiAdapter(ip=self.localIP, user=self.username, pwd=self.password)
self.esxHost.login()
hosts = self.esxHost.get_host_system()
for host in hosts:
    hba = host.list_hba_info()['fc']
hba_list = {}
for line in hba:
    node = line['node']
port = line['port']
hba_list[port] = {"port": port,
                  "node": node}
return hba_list


def get_vaai_hardware_accelerated_locking(self):
    """获取 VAAI HardwareAcceleratedLocking的状态，即ATS

    Returns:
    status (str): 0是关，1是开

    Changes:
    l00355383 2017-10-9 16:32:42 Created

    """


cmd = "esxcli system settings advanced list --option /VMFS3/HardwareAcceleratedLocking"
result = self.run({"command": [cmd]})
response = result['stdout'].split('\r\n')[2].split(':')[1]
status = response.strip()
return status


def get_vaai_hardware_accelerated_move(self):
    """获取 VAAI HardwareAcceleratedMove的状态，即XCOPY

    Returns:
    status (str): 0是关，1是开

    Changes:
    l00355383 2017-10-9 16:32:42 Created

    """


cmd = "esxcli system settings advanced list --option /DataMover/HardwareAcceleratedMove"
result = self.run({"command": [cmd]})
response = result['stdout'].split('\r\n')[2].split(':')[1]
status = response.strip()
return status


def get_vaai_hardware_accelerated_init(self):
    """获取 VAAI HardwareAcceleratedInit的状态，即WRITE SAME

    Returns:
    status (str): 0是关，1是开

    Changes:
    l00355383 2017-10-9 16:32:42 Created

    """


cmd = "esxcli system settings advanced list --option /DataMover/HardwareAcceleratedInit"
result = self.run({"command": [cmd]})
response = result['stdout'].split('\r\n')[2].split(':')[1]
status = response.strip()
return status


def get_vaai_enable_block_delete(self):
    """获取 VAAI EnableBlockDelete的状态，即UNMAP

    Returns:
    status (str): 0是关，1是开

    Changes:
    l00355383 2017-10-9 16:32:42 Created

    """


cmd = "esxcli system settings advanced list --option /VMFS3/EnableBlockDelete"
result = self.run({"command": [cmd]})
response = result['stdout'].split('\r\n')[2].split(':')[1]
status = response.strip()
return status


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

    Raises:
    CommandException: 命令执行异常

    Examples:
    cmdSpec = {"command": ["sftp", "admin@100.148.115.39"], "waitstr":
    "password", "input": ["123456", "[>#]", "ls", "[>#]"],
    "directory": "/home/"}
    result = self.run(cmdSpec)

    """


if not params.has_key('waitstr'):
    params['waitstr'] = '~]'
return super(Esx, self).run(params)


def upadm_show_path(self):
    """获取esxcli upadm show path的回显

    Args:
    None

    Returns:
    targets (list): 所有查询到的target信息,.

    Raises:
    CommandException: 命令执行失败.

    Examples:
    targets = hostObj.upadminShowPath()
    Output:
    Path ID Initiator Port Array Name Controller Target Port Path State Check State Port Type
    0 21000024ff4b81f8 Huawei.Storage 0A 22089017acb03969 Normal -- FC
    2 21000024ff4b81f9 Huawei.Storage 0B 24109017acb03969 Normal -- FC
    Result:
    [
    {
    'path_id' : '0',
    'initiator_port': '21000024ff4b81f8',
    'array_name': 'Huawei.Storage',
    'controller': '0A',
    'target_port': '22089017acb03969',
    'path_state': 'Normal',
    'check_state': '--',
    'port_type':'FC'
    },
    {
    'path_id' : '2',
    'initiator_port': '21000024ff4b81f9',
    'array_name': 'Huawei.Storage',
    'controller': '0B',
    'target_port': '24109017acb03969',
    'path_state': 'Normal',
    'check_state': '--',
    'port_type':'FC'
    }
    ]

    """


response = self.run({"command": ["esxcli", "upadm", "show", "path"]})
targetList = []
if response["stdout"] is None:
    return targetList

lines = self.split(response["stdout"])
compileSplit = re.compile('\s{2,}')
compileFind = re.compile('\d{1,}')
keys = []

for line in lines:
    targetDict = {}
# 过滤分隔符
if line.endswith('----'):
    continue
# 匹配表头，并且作为后续用的key值
if not re.findall(compileFind, line):
    tempsKeys = re.split(compileSplit, line)
for key in tempsKeys:
    key = key.strip()
keys.append(key.lower().replace(' ', '_'))
continue
line = line.strip()
values = re.split(compileSplit, line)
for (key, value) in zip(keys, values):
    targetDict[key] = value

targetList.append(targetDict)

return targetList


def upadm_show_vlun(self, vlun_id=None, array_id=None, vlun_type=None):
    """获取esxcli upadm show vlun的回显

    Args:
    vlun_id (str): (Optional)display the specified VLUN`s information
    array_id (str): (Optional)display information about all VLUNs of the specified disk array
    vlun_type (str): (Optional)display the specified type of VLUN`s information

    Returns:
    targets (list): 所有查询到的target信息

    Raises:
    CommandException: 命令执行失败.

    """


command = ["esxcli", "upadm", "show", "vlun"]
if vlun_id:
    command.append('-l %s' % vlun_id)
if array_id:
    command.append('-a %s' % array_id)
if vlun_type:
    command.append('-t %s' % vlun_type)
response = self.run({"command": command})
targetList = []
if response["stdout"] is None:
    return targetList

if vlun_id is None:
    lines = self.split(response["stdout"])
compileSplit = re.compile('\s{2,}')
compileFind = re.compile('\d{1,}')
keys = []

for line in lines:
    targetDict = {}
# 过滤分隔符
if line.endswith('----'):
    continue
# 匹配表头，并且作为后续用的key值
if not re.findall(compileFind, line):
    tempsKeys = re.split(compileSplit, line)
for key in tempsKeys:
    key = key.strip()
keys.append(key.lower().replace(' ', '_'))
continue
line = line.strip()
values = re.split(compileSplit, line)
for (key, value) in zip(keys, values):
    targetDict[key] = value

targetList.append(targetDict)

return targetList
else:
# TODO 解析带vlun id的回显
return targetList


def set_nmp_alua(self):
    """
    esxcli storage nmp satp rule add -V HUAWEI -M XSG1 -s VMW_SATP_ALUA -P VMW_PSP_RR -c tpgs_on
    """


_command = 'esxcli storage nmp satp rule add -V HUAWEI -M XSG1 -s VMW_SATP_ALUA -P VMW_PSP_RR -c tpgs_on'
response = self.run({"command": [_command]})
if response["rc"] != 0:
    raise CommandException(response["stderr"])


def storage_nmp_path_list(self):
    """获取esxcli storage nmp path list的回显

    Returns:
    targets (list): 所有查询到的target信息,.

    Raises:
    CommandException: 命令执行失败.

    Examples:
    fc.20000024ff8af5c0:21000024ff8af5c0-fc.2100143004b0e459:2080143004b0e459-naa.6143004100b0e4590139f72e00000046
    Runtime Name: vmhba2:C0:T0:L1
    Device: naa.6143004100b0e4590139f72e00000046
    Device Display Name: HUAWEI Fibre Channel Disk (naa.6143004100b0e4590139f72e00000046)
    Group State: active
    Array Priority: 0
    Storage Array Type Path Config: {TPG_id=1,TPG_state=AO,RTP_id=29,RTP_health=UP}
    Path Selection Policy Path Config: PSP VMW_PSP_RR does not support path configuration.

    fc.20000024ff8af5c1:21000024ff8af5c1-fc.2100143004b0e459:2091143004b0e459-naa.6143004100b0e4590139f72e00000046
    Runtime Name: vmhba3:C0:T3:L1
    Device: naa.6143004100b0e4590139f72e00000046
    Device Display Name: HUAWEI Fibre Channel Disk (naa.6143004100b0e4590139f72e00000046)
    Group State: active unoptimized
    Array Priority: 0
    Storage Array Type Path Config: {TPG_id=2,TPG_state=ANO,RTP_id=286,RTP_health=UP}
    Path Selection Policy Path Config: PSP VMW_PSP_RR does not support path configuration.

    Result:
    [
    {
    'path_id' : '0',
    'initiator_port': '21000024ff4b81f8',
    'array_name': 'Huawei.Storage',
    'controller': '0A',
    'target_port': '22089017acb03969',
    'path_state': 'Normal',
    'check_state': '--',
    'port_type':'FC'
    },
    {
    'path_id' : '2',
    'initiator_port': '21000024ff4b81f9',
    'array_name': 'Huawei.Storage',
    'controller': '0B',
    'target_port': '24109017acb03969',
    'path_state': 'Normal',
    'check_state': '--',
    'port_type':'FC'
    }
    ]

    """


response = self.run({"command": ["esxcli", "storage", "nmp", "path", "list"]})
paths_list = []
if response["stdout"] is None:
    return paths_list

paths_info = response["stdout"].split('\r\n\r\n')

for info in paths_info:
    _lines = info.split('\r\n')
line_compile = re.compile(r'(.*):\s*(.*)')
path = {}
for _line in _lines:
    search_result = line_compile.search(_line)
if search_result:
    groups = search_result.groups()
_key = groups[0].lower().strip().replace(' ', '_')
_value = groups[1]
path[_key] = _value
else:
self.logger.info('the format is error')
if path:
    paths_list.append(path)
return paths_list


def is_ultrapath_install(self):
    """
    esxcli upadm -h

    Returns:
    install_result (bool): True is install, False is not
    """


_command = 'esxcli upadm'
response = self.run({"command": [_command]})
if response["rc"] != 0:
    return False
else:
    return True


def get_vlun_paths_info(self, vlun_id, vlun_type=None):
    command = ["esxcli", "upadm", "show", "vlun", '-l', vlun_id]


if vlun_type:
    command.append('-t %s' % vlun_type)
response = self.run({"command": command})
if response["rc"] != 0:
    raise CommandException('send command error')
result = response['stdout']
paths_compile = re.compile(r'Path\s+\d+.*:.*', re.MULTILINE)
paths = paths_compile.findall(result)
paths_info = {}
for _path in paths:
    _path_search = re.search(r'Path\s+(\d+).*:\s+(.+)\r', _path)
if not _path_search:
    raise CommandException('the path format is error: %s' % _path)
_groups = _path_search.groups()
_path_id = _groups[0]
_state = _groups[1]
if paths_info.has_key(_state):
    paths_info[_state].append(_path_id)
else:
    paths_info[_state] = [_path_id]
return paths_info


def get_path_info(self, path_id):
    all_paths = self.upadm_show_path()


for _path in all_paths:
    if str(_path['path_id']) == str(path_id):
        return _path
return None


def get_version(self):
    command = ["vmware", '-l']


response = self.run({"command": command})
if response["rc"] != 0:
    raise CommandException('send command error')
result = str(response['stdout']).splitlines()[0]
self.logger.info('%s: %s' % (self.localIP, result))
return result


def upadm_show_version(self):
    """获取esxcli upadm show version

    Returns:
    targets (list): 所有查询到的target信息

    Raises:
    CommandException: 命令执行失败.

    """


command = ["esxcli", "upadm", "show", "version"]
response = self.run({"command": command})
info = {}
if response["stdout"] is None:
    return info
else:
    lines = str(response['stdout']).splitlines()
for line in lines:
    if re.search('(Software|Driver)', line):
        _split_infos = line.split(':')
_key = re.sub(r'\s+', '_', _split_infos[0].lower().strip())
_value = _split_infos[1].strip()
info[_key] = _value
return info


def set_nas_max_volumes(self, max_volumes):
    """设置主机上NAS共享的MaxVolumes数目，NFS3和NFS41

    Args:
    maxvolumes (int)：Value of MaxVolumes


    Returns:


    Examples:
    host.set_nas_MaxVolumes():

    """


MaxVolumes_info = "Value of MaxVolumes is " + str(max_volumes)
nfs3 = "esxcfg-advcfg -s " + str(max_volumes) + " /NFS/MaxVolumes"
nfs41 = "esxcfg-advcfg -s " + str(max_volumes) + " /NFS41/MaxVolumes"


def acmd(cmd):
    response = self.run({"command": [cmd]})


result = response['stdout']
if MaxVolumes_info in result:
    return True
else:
    return False


def check_nas_MaxVolumes():
    nfs3 = "esxcfg-advcfg -g /NFS/MaxVolumes"


nfs41 = "esxcfg-advcfg -g /NFS41/MaxVolumes"
ret = acmd(nfs3)
ret = acmd(nfs41)
return ret

# 检查MaxVolumes是否为所给数值
ret = check_nas_MaxVolumes()
if ret:
    self.log.info("Value of MaxVolumes is %s" % str(max_volumes))
else:
# 设置MaxVolumes为所给数值
ret = acmd(nfs3)
ret = acmd(nfs41)
if ret:
    self.reboot(wait=True)
sleep(120)
else:
raise CommandException("MaxVolumes Setup failed ")
# 设置完检查
ret = check_nas_MaxVolumes()
if ret:
    self.log.info("Value of MaxVolumes is %s" % str(max_volumes))
else:
    raise CommandException("MaxVolumes Setup failed ")


def check_nas_vaai(self):
    """检查nas vaai开关状态

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- vaai状态开
    False- vaai状态关


    Examples:
    host.check_nas_vaai():

    """


checkstatus = "esxcli software vib list |grep VAAI"
response = self.run({"command": [checkstatus]})
if response['stdout']:
    return True
else:
    return False


def set_nas_vaai(self, value, software_path):
    """设置nas vaai开关

    Args:
    value (str): 1代表开，0代表关

    Returns:
    True|False: True- 更改vaai状态成功
    False- 更改vaai状态失败

    Raises:
    CommandException:发生异常

    Examples:
    host.set_nas_vaai('1',,ip, port, user, password, path):

    """


# check nas vaai状态

ret = self.check_nas_vaai()
update_success = "The update completed successfully"
if value == "1":
    if ret:
# 打印info日志
self.log.info("nas vaai is installed in a good state")
return True
else:
try:
    install = "esxcli software vib install -d " + str(software_path)
response = self.run({"command": [install]})
if update_success not in response['stdout']:
    self.log.debug("install nas vaai software failed")
return False
except Exception, e:
self.log.debug(e.message)
self.log.debug("install nas vaai software failed")
return False
else:
self.reboot(wait=True)
# self.waitForReboot()
sleep(120)
ret = self.check_nas_vaai()
if ret:
    self.log.info("nas vaai is installed successfully")
return True
else:
self.log.debug("nas vaai installation Failed")
return False
else:
if ret:
    try:
        uninstall = "esxcli software vib remove --vibname=HuaweiVAAINasPlugin"
response = self.run({"command": [uninstall]})
if update_success not in response['stdout']:
    self.log.debug("uninstall nas vaai software failed")
return False
except Exception, e:
self.log.debug(e.message)
self.log.debug("uninstall nas vaai software failed")
return False
else:
self.reboot(wait=True)
# self.waitForReboot()
sleep(120)
ret = self.check_nas_vaai()
if not ret:
    self.log.info("nas vaai is Uninstall succeeded")
return True
else:
self.log.debug("nas vaai is Uninstall failed")
return False
else:
self.log.info("nas vaai is already not installed")
return True


def upadm_set_path_normal(self, path_id):
    """
    esxcli upadm set phypathnormal 0
    """


self.logger.info('[%s]设置path %s状态为Normal' % (self.localIP, path_id))
_command = 'esxcli upadm set phypathnormal -p %s' % path_id
response = self.run({"command": [_command]})
if response["rc"] != 0:
    raise CommandException(response["stderr"])


def getIqn(self):
    """获取该ESX主机的IQN信息

    Args:
    None.

    Returns:
    iqn (str): 该主机的iqn信息.

    Raises:
    None.

    Examples:
    hostObj.getIqn()
    Output:
    "iqn.2013-12.site:01:669c365dfece"
    Changes:
    2018-12-20 14:47:14 l00355383 Created
    """


_cmd = 'esxcli iscsi adapter list'
response = self.run({'command': [_cmd]})
if response["rc"] != 0:
    raise CommandException(response["stderr"])
else:
    lines = self.split(response["stdout"])
compile_split = re.compile('\s{2,}')
compile_find = re.compile('\d{1,}')
keys = []
target_list = []
for line in lines:
    target_dict = {}
# 过滤分隔符
if line.endswith('----'):
    continue
# 匹配表头，并且作为后续用的key值
if not re.findall(compile_find, line):
    temps_keys = re.split(compile_split, line)
for key in temps_keys:
    key = key.strip()
keys.append(key.lower().replace(' ', '_'))
continue
line = line.strip()
values = re.split(compile_split, line)
for (key, value) in zip(keys, values):
    target_dict[key] = value

target_list.append(target_dict)
if len(target_list) > 0:
    return target_list[0]['uid']
else:
    raise CommandException('ESX Host has no iscsi iqn, please check the ESX host env')


def unmap_reclaim_datastore(self, datastore_name, unmap_speed=None, timeout=3600, interval=60, is_wait=True):
    """
    esxcli下手动下发命令esxcli storage vmfs unmap -l -n手动触发空间回收

    Args:
    datastore_name: (str) datastore名字
    unmap_speed: (int) -n后面跟的unmap速度参数，不下发默认是200
    timeout: (int) 空间回收超时时间
    interval: (int) 每次检查间隔时间
    is_wait: (bool) 是否等待空间回收完成

    Returns:
    duration: (int)空间回收时间
    start_time: (str)空间回收开始时间
    end_time: (str)空间回收结束时间
    """


if unmap_speed is not None:
    _unmap_cmd = 'esxcli storage vmfs unmap -l %s -n %s' % (datastore_name, unmap_speed)
else:
    _unmap_cmd = 'esxcli storage vmfs unmap -l %s' % datastore_name
_unmap_log_file = '/tmp/%s.unmap.log' % time.strftime('%Y%m%d%H%M%S')
_running_cmd = 'nohup sh -c "date +%%Y-%%m-%%-d/%%H:%%M:%%S && %s && date +%%Y-%%m-%%-d/%%H:%%M:%%S" >%s 2>&1 &' \
               % (_unmap_cmd, _unmap_log_file)
response = self.run({"command": [_running_cmd], 'waitstr': '~]'})
sleep(5)
cat_cmd = 'cat %s' % _unmap_log_file
if response['rc'] is not None and response['rc'] != 0:
    error_msg = self.run({"command": [cat_cmd], 'waitstr': '~]'})
raise CommandException('running command[%s] error\nerror msg: %s' % (_running_cmd, error_msg['stdout']))
else:
if is_wait:
    @repeat_timeout('repeat get log file information')
    def repeat_cat_log_file(timeout, interval):


        log_msg = self.run({"command": [cat_cmd], 'waitstr': '~]'})
if log_msg['rc'] != 0 or log_msg['rc'] is None:
    return [False, log_msg]
else:
    time_list = re.findall(r'\d{4}-\d+-\d+/\d{2}:\d{2}:\d{2}', log_msg['stdout'])
if len(time_list) < 2:
# unmap执行命令失败，具体原因查看日志
if 'Intializing async unmap failed' in cat_result['stdout']:
    raise Exception("Intializing async unmap failed on volume")
# unmap命令不支持，可能是本地硬盘或THICK LUN
if "do not support UNMAP" in cat_result['stdout']:
    raise Exception("do not support UNMAP")
return [False, log_msg]
else:
return [True, log_msg]

cat_result = self.run({"command": [cat_cmd]})
log_msg = repeat_cat_log_file(timeout=timeout, interval=interval)[1]['stdout']
lines = log_msg.splitlines()
start_time_datetime = datetime.datetime.strptime(lines[0], '%Y-%m-%d/%H:%M:%S')
end_time_datetime = datetime.datetime.strptime(lines[1], '%Y-%m-%d/%H:%M:%S')
duration = (end_time_datetime - start_time_datetime).seconds
start_time = lines[0].replace('/', ' ')
end_time = lines[1].replace('/', ' ')
return duration, start_time, end_time
else:
return


def get_esxtop_infos(self):
    """
    获取esxtop的信息，包括VAAI

    Returns: headers (list): esxtop每一项的表头
    datas (list): esxtop每一项的回显
    """


esxtop_cfg_content = 'abcdefghij\n' \
                     'abcdefghijklmnopq\n' \
                     'abcdefghijkl\n' \
                     'AbcdefghijklmnOP\n' \
                     'abcdefghijkl\n' \
                     'abcdefghijklmnopq\n' \
                     'abcdef\n' \
                     'abcdef\n' \
                     'abcd\n' \
                     '5u'
esxtop_cfg_path = '/opt/esxtop_vaai'
if not self.doesPathExist({'path': esxtop_cfg_path}):
    self.writeToFile(esxtop_cfg_path, esxtop_cfg_content)
# output_file_path = '/opt/vaai_result.txt'
# self.run({'command': ['esxtop -n 1 -d 2 -c %s> %s' % (esxtop_cfg_path, output_file_path)]})
# lines = self.readFile(output_file_path)
# local_file_path = '%s/%s' % (Log.LogFileDir, 'esxtop_result.txt')
# self.getFile({"source_file": '%s' % output_file_path,
# "destination_file": local_file_path})
# with open(local_file_path, 'rb') as esxtop_file:
# lines = esxtop_file.readlines()
lines = self.run({'command': ['esxtop -n 1 -d 2 -c %s' % esxtop_cfg_path]})['stdout'].splitlines()
headers = lines[0].split(',')
datas = lines[1].split(',')
if len(headers) != len(datas):
    raise EnvironmentError('esxtop headers number %s is not equal infos number %s'
                           % (len(headers), len(datas)))
# os.remove(local_file_path)
return headers, datas


def get_vaai_info(self):
    """
    获取VAAI ESXTOP信息

    Returns:(dict)

    """


headers, datas = self.get_esxtop_infos()
# 查找XCOPY信息
clone_suc_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Success Latency ms/Clone"')
clone_fail_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Failure Latency ms/Clone"')
clone_write_number_compile = re.compile(r'".*\(naa\.(\w{32})\)\\CWrites"')
clone_write_mb_compile = re.compile(r'".*\(naa\.(\w{32})\)\\MBytes CWrites/sec"')
clone_read_number_compile = re.compile(r'".*\(naa\.(\w{32})\)\\CReads"')
clone_read_mb_compile = re.compile(r'".*\(naa\.(\w{32})\)\\MBytes CReads/sec"')
clone_fail_compile = re.compile(r'".*\(naa\.(\w{32})\)\\CFailed"')

# 查询ZERO信息
zero_suc_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Success Latency ms/Zero"')
zero_fail_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Failure Latency ms/Zero"')
zero_number_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Zeros"')
zero_fail_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Zeros Failed"')
zero_mb_compile = re.compile(r'".*\(naa\.(\w{32})\)\\MBytes Zeros/sec"')

# 查询ATS信息
ats_suc_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Success Latency ms/ATS"')
ats_fail_latency_compile = re.compile(r'".*\(naa\.(\w{32})\)\\Average Failure Latency ms/ATS"')
ats_number_compile = re.compile(r'".*\(naa\.(\w{32})\)\\ATS"')
ats_fail_compile = re.compile(r'".*\(naa\.(\w{32})\)\\ATS Failed"')

find_rule_dict = {
    'clone_success_latency': clone_suc_latency_compile,
    'clone_fail_latency': clone_fail_latency_compile,
    'clone_write_num': clone_write_number_compile,
    'clone_write_mb': clone_write_mb_compile,
    'clone_read_num': clone_read_number_compile,
    'clone_read_mb': clone_read_mb_compile,
    'clone_fail': clone_fail_compile,
    'zero_success_latency': zero_suc_latency_compile,
    'zero_fail_latency': zero_fail_latency_compile,
    'zero_num': zero_number_compile,
    'zero_fail': zero_fail_compile,
    'zero_mb': zero_mb_compile,
    'ats_success_latency': ats_suc_latency_compile,
    'ats_fail_latency': ats_fail_latency_compile,
    'ats_number': ats_number_compile,
    'ats_fail': ats_fail_compile
}

device_vaai_infos = dict()

for index, _h in enumerate(headers):
    for _key, _compile in find_rule_dict.items():
        if _compile.search(_h):
        _wwn = _compile.search(_h).groups()[0]
if device_vaai_infos.has_key(_wwn):
    device_vaai_infos[_wwn][_key] = datas[index]
else:
    device_vaai_infos[_wwn] = {_key: datas[index]}
break
else:
continue
return device_vaai_infos


def set_vaai_rule_v6(self):
    """
    设置V6 VAAI多segment rule

    Returns:
    None
    """


self.run({'command': ['esxcli storage core claimrule add -c Filter -P VAAI_FILTER -t vendor -V HUAWEI -u']})
self.run(
    {'command': ['esxcli storage core claimrule add -c VAAI -P VMW_VAAIP_T10 -t vendor -V HUAWEI -u -a -s']})
self.run({'command': ['esxcli storage core claimrule load -c Filter']})
self.run({'command': ['esxcli storage core claimrule load -c VAAI']})
self.run({'command': ['esxcli storage core claimrule run -c Filter']})
self.run({'command': ['esxcli storage core claimrule run -c VAAI']})


def remove_vaai_rule_v6(self):
    """
    移除V6 VAAI多segment rule

    Returns:
    None
    """


self.run({'command': ['esxcli storage core claimrule remove -r 5001 -c=Filter']})
self.run({'command': ['esxcli storage core claimrule remove -r 5001 -c=VAAI']})
self.run({'command': ['esxcli storage core claimrule load -c Filter']})
self.run({'command': ['esxcli storage core claimrule load -c VAAI']})
self.run({'command': ['esxcli storage core claimrule run -c Filter']})
self.run({'command': ['esxcli storage core claimrule run -c VAAI']})


def is_vaai_rule_set_v6(self):
    """
    判断是否存储V6 VAAI度segment rule

    Returns:
    is_set_result (bool): 是否存在
    """


_lines = self.run({'command': ['esxcli storage core claimrule list -c Filter|grep HUAWEI']})[
    'stdout']
if _lines is None:
    return False
_lines = self.run({'command': ['esxcli storage core claimrule list -c VAAI|grep HUAWEI']})[
    'stdout'].splitlines()
if _lines is None:
    return False
return True


def is_vmware67(self):
    """
    判断版本是否是6.7

    Returns:
    result (bool): 是否是6.7
    """


result = self.run({'command': ['vmware -l']})['stdout'].splitlines()
for _line in result:
    if re.search(r'.*6\.7\.0.*', _line):
        return True
return False


def set_aa_round_robin_rule(self):
    """
    设置AA round-robin

    Returns:
    None
    """


self.run({'command': [
    'esxcli storage nmp satp rule add -V HUAWEI -M XSG1 -s VMW_SATP_DEFAULT_AA -P VMW_PSP_RR -c tpgs_off']})
