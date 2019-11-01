# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：该模块提供HyperV系统相关功能，包括对HyperV虚拟机的操作，HyperV主机的管理的方法和属性

版权信息：华为技术有限公司，版本所有(C) 2017-2018

作者: liruiqi 00355383
"""

from UniAutos.Device.Host.Windows import Windows
from UniAutos.Device.Host.Hypervisor.Utilities import HyperVAlias as hyperv_alias
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.Units import Units
import re, os


class HyperV(Windows):
    def __init__(self, username, password, params):

        """HyperV主机类，继承于Windows类，该类主要包含HyperV主机相关操作于属性
    -下面的Components类属于XenServer主机类，包含Nice Name与Component Class Name:

    Nice Name Component Class Name
    ================================================================
    To be Added

    -构造函数参数:
    Args:
    username (str): HyperV主机登陆使用的用户名, 建议使用root用户.
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
    hyperVObj (instance): hyperVObj.

    """


super(HyperV, self).__init__(username, password, params)

# Register HyperV Tool Wrapper, 暂时注释掉
# module = "UniAutos.Wrapper.Tool.PowerShell.HypervBase"
# __import__(module)
# moduleClass = getattr(sys.modules[module], "HypervBase")
# vmwareWrapperObj = moduleClass(username=username, password=password, ipAddr=params['ipv4_address'])
# vmwareWrapperObj.setDevice(self)
# self.registerToolWrapper(host=self, wrapper=vmwareWrapperObj)

for objType in self.classDict.itervalues():
    self.markDirty(objType)

res = self.command.cmd({'command': ['systeminfo']})
res['stdout'].replace("\cM\cJ", "\n")

regex = re.search('OS Name:\s*(.+)', res['stdout'], re.MULTILINE)
if regex:
    self.os = regex.groups()[0]

self.clusterName = params.get('cluster_name')
self.csvs = []
self.ps_params = {
    'ClusterName': self.clusterName,
    'UserName': self.username,
    'Password': self.password,
    'Verbose': ''
}


def run_powershell(self, params):
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

    """


if not params.has_key('timeout'):
    params['timeout'] = 3600
if params.has_key('command'):
    params['command'] = ['cmd', '/c', 'powershell'] + params['command']
response = self.run(params)
if 'rc' in response and response['rc'] != 0 or response['stderr'] is not None:
    raise UniAutosException('run powershell %s error\nerror message:%s'
                            % (params['command'], response['stderr']))
else:
    return response['stdout']


def get_cluster_name(self):
    """get the hyper-v cluster name

    Returns:
    name (str): cluster name

    Changes:
    l00355383 2017-11-21 15:58:50 Created

    """


cluster_name = self.run_powershell({'command': ['(get-cluster).name']})
return cluster_name


def get_cluster_hosts(self):
    """get the hyper-v cluster hosts` name

    Returns:
    hosts_name (list): the host name list

    Changes:
    l00355383 2017-11-21 15:58:50 Created

    """


hosts_name = self.run_powershell({'command': ['(get-clusternode).name']})
hosts_name = hosts_name.splitlines()
return hosts_name


def run_powershell_script(self, script_path, params=None, on_new_sessoin=False):
    """run powershell scprit

    Returns:
    script_path (str): the script path
    params (dict): (Optional)the power shell script params

    Changes:
    l00355383 2017-11-21 20:43:15 Created

    """


if not self.doesPathExist({'path': script_path}):
    raise UniAutosException('[%s]the script[%s] isn`t exist in windows system, please check'
                            % (self.localIP, script_path))
command = [r'%s' % script_path]
if params is not None:
    command += ['-%s %s' % (k, v) for k, v in params.items()]

if not on_new_sessoin:
    response = self.run({'command': ['cmd', '/c', 'powershell'] + command,
                         'timeout': 5400})
# 如果没有执行结果，或者stderr有执行错误则抛错
if 'rc' in response and response['rc'] != 0:
    raise UniAutosException('run powershell %s error\nerror message:%s'
                            % (command, response['stderr']))
else:
    result = response['stdout']
search_result = re.search(r'(Test Result\s*:\s*.*)', result, re.S)
groups = search_result.groups()
if len(groups) == 0:
    raise UniAutosException(
        'the powershell result format is not correct, there is no Test Result string')
else:
    reponse_result = groups[0]
result_lines = reponse_result.splitlines()
cmd_result = dict()
for line in result_lines:
    if line:
        match_result = re.match(r'^(.*?):(.*)', line)
if match_result:
    _key, _value = match_result.groups()
_key = str(_key).strip().lower().replace(' ', '_')
_value = _value.strip()
cmd_result[_key] = _value
else:
raise UniAutosException(
    'a line[%s] of the poershell result format is not correct' % line)
if cmd_result['test_result'] == 'Passed' or cmd_result['test_result'] == 'True':
    return cmd_result
else:
    raise UniAutosException('the powershell script[%s] running failed, TestResult is not Passed'
                            % os.path.join(script_path, os.path.pardir))
else:
p = '(%s)' % ','.join(['"""-%s %s"""' % (k, v) for k, v in params.items()])
script_params = {
    'UserName': self.username,
    'Password': self.password,
    'ScriptPath': script_path,
    'Params': p
}
result = self.run_powershell_script(hyperv_alias.RUN_PS_SCRIPT, params=script_params, on_new_sessoin=False)
return result


def open_odx(self):
    """
    open the host odx
    """


self.logger.info('[%s]open the odx siwtch' % self.localIP)
self.run_powershell({'command': ['Set-ItemProperty', 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem',
                                 '-name', '"Filtersupportedfeaturesmode"', '-value 0']})
odx_switch = self.get_odx()
if odx_switch != 'on':
    raise UniAutosException('open the windows host[%s] odx switch failed' % (self.localIP))


def close_odx(self):
    """
    close the host odx
    """


self.logger.info('[%s]close the odx siwtch' % self.localIP)
self.run_powershell({'command': ['Set-ItemProperty', 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem',
                                 '-name', '"Filtersupportedfeaturesmode"', '-value 1']})
odx_switch = self.get_odx()
if odx_switch != 'off':
    raise UniAutosException('close the windows host[%s] odx switch failed' % (self.localIP))


def get_odx(self):
    """
    get the host odx switch

    Returns:
    odx_switch (str): on or off
    """


result = self.run_powershell(
    {'command': [r'Get-ItemProperty hklm:\system\currentcontrolset\control\filesystem']})
search_result = re.search(r'FilterSupportedFeaturesMode\s*:\s*(\d)', result)
if search_result:
    mode = search_result.groups()[0]
if mode == '0':
    return 'on'
elif mode == '1':
    return 'off'
else:
raise UniAutosException('the FilterSupportedFeaturesMode value is not correct')
else:
raise UniAutosException('there is no FilterSupportedFeaturesMode')


def create_csvs(self, luns, format_size=None):
    """
    创建cluster shared volume

    Args:
    luns (list): the lun component objects list
    format_size (str): (Optional)the csv format size, unit is MB/GB/TB

    Returns:
    result (dict): {
    'csv_result': [name1, name2],
    'start_time': xxx,
    'finish_time': xxx,
    'bandwidth': xxx
    ...
    }
    """


if len(luns) == 0:
    raise UniAutosException('there is no lun')
size_number = None
params = self.ps_params.copy()
if format_size is not None:
    size_number = Units.getNumber(Units.convert(format_size, 'GB'))
if size_number is not None:
    params['FormatSizeGB'] = size_number
luns_wwn = [lun.getProperty('wwn') for lun in luns]
luns_wwn_str = ','.join(['"""%s"""' % wwn for wwn in luns_wwn])
luns_wwn_str = '(%s)' % luns_wwn_str
params['LUNWWNs'] = luns_wwn_str
version_all = self.getVersion()
version = version_all.split('.')[0]
# 版本是Windows server 2016
if version == "10":
    result = self.run_powershell_script(hyperv_alias.CREATE_CSVS_2016, params=params)
# 版本是Windows server 2012及其他
else:
    result = self.run_powershell_script(hyperv_alias.CREATE_CSVS, params=params)
result['csv_created'] = result['csv_created'].split(' ')
return result


def wipe_csvs(self):
    """
    清理cluster下的所有csv
    """


self.logger.info('wipe clsuter[%s] cluster shared volumes' % self.clusterName)
self.remove_csvs()


def remove_csvs(self, csv_names=None):
    """
    清理指定名字的CSV，如果csv_names为None则全部清除

    Args:
    csv_names (list): csv name list

    """


self.logger.info('remove clsuter[%s] cluster shared volumes:%s' % (self.clusterName, csv_names))
params = self.ps_params.copy()
if csv_names:
    csvs = ','.join(['"""%s"""' % name for name in csv_names])
params['$CSVPaths'] = csvs
result = self.run_powershell_script(hyperv_alias.REMOVE_CSVS, params=params)
return result


def remove_vms(self, csv_names=None, vm_name_prefix=None):
    """
    删除csv_names指定vm_name_prefix的虚拟机，如果csv_names为None，则删除所有csv的虚拟机

    Args:
    csv_names (list): (Optional)csv name list who to be deleted
    vm_name_prefix (str): (Optional) vm name prefix who to be deleted

    """


if vm_name_prefix is None:
    vm_name_prefix = '*'
self.logger.info('clear vms in csvs-%s, vm name prefix %s' % (csv_names, vm_name_prefix))
params = self.ps_params.copy()
if csv_names:
    csvs = ','.join(['"""%s"""' % name for name in csv_names])
params['$CSVPaths'] = csvs
params['VMNamePrefix'] = vm_name_prefix

result = self.run_powershell_script(hyperv_alias.CLEAR_VMS, params=params, on_new_sessoin=True)
return result


def wipe_vms(self):
    """
    wipe the virtual machines in cluser
    """


self.logger.info('wipe the vms in cluster[%s]' % self.clusterName)
params = self.ps_params.copy()
self.run_powershell_script(hyperv_alias.WIPE_VMS, params, True)


def copy_vhd_files(self, src_file_path, dst_volume_path, vhd_file_name_prefix='VHD', number=1, robocopy=True):
    """
    将src_path下的vhd文件复制给dst_path

    Args:
    src_file_path (str): 需要复制的源文件路径
    dst_volume_path (str): 复制文件到目标共享卷路径
    vhd_file_name_prefix (str): 复制到共享卷的vhd 文件名字前缀
    number (int): (Optional)复制的数量
    robocopy (bool): (Optional)是否使用robocopy，默认为True
    """


self.logger.info('copy %s to %s name prefix %s number %s'
                 % (src_file_path, dst_volume_path, vhd_file_name_prefix, number))
params = self.ps_params.copy()
params['SrcVHDFile'] = src_file_path
params['DstVHDFileNamePrefix'] = vhd_file_name_prefix
params['DstDir'] = dst_volume_path
params['Concurrency'] = number
if robocopy:
    params['UseRobocopy'] = ''
result = self.run_powershell_script(hyperv_alias.COPY_VHDFS, params=params)
return result


def copy_vhd_to_csv(self, csv_name, template_path=hyperv_alias.ODX_TEMPLATE):
    """
    copy 一份50G的vhd到csv共享卷

    Args:
    csv_name (str): 共享卷名字（路径）
    template_path (str): template path in windows system, default is
    C:\uniautos_hyperv_tools\template\ODX_TEMPLATE.vhdx

    Returns:
    vhd_file_path (str): vhd文件路径
    """


template_path = self.transfer_path(template_path)
self.run({"command": ["cmd", "/c", "copy", template_path, csv_name]})
# template_name = os.path.basename(template_path)
template_name = template_path.split('\\')[-1]
path_name = '%s\\%s' % (csv_name, template_name)
return path_name


def copy_vm_template_to_csv(self, csv_name, template_path):
    """
    copy virtual machine template to csv

    Args:
    csv_name (str): 共享卷名字（路径）
    template_path (str): the virtual machine template path

    Returns:
    vhd_file_path (str): vhd文件路径
    """


template_path = self.transfer_path(template_path)
path_name = '%s\\%s\\' % (csv_name, template_path.split('\\')[-1])
self.run({"command": ["cmd", "/c", "xcopy", '"%s" "%s"' % (template_path, path_name), '/s', '/e']})
return path_name


def create_vhd_files(self, csv_path, vhd_file_name_prefix, number=1, vhd_size='50GB'):
    """
    将src_path下的vhd文件复制给dst_path

    Args:
    csv_path (str): 创建VHD共享卷路径
    vhd_file_name_prefix (str): 创建到共享卷的vhd 文件名字前缀
    number (int): (Optional)创建的数量
    vhd_size (str): (Optional)创建VHD的大小

    Returns:
    result (dict): powershell test case result
    """


self.logger.info('create vhd files in %s name prefix %s number %s size %s'
                 % (csv_path, vhd_file_name_prefix, number, vhd_size))
params = self.ps_params.copy()
params['VHDFileNamePrefix'] = vhd_file_name_prefix
params['DstDir'] = csv_path
params['Concurrency'] = number
params['DiskSizeGB'] = Units.getNumber(Units.convert(vhd_size, 'GB'))
result = self.run_powershell_script(hyperv_alias.CREATE_VHDFS, params=params)
return result


def create_vms_by_vhd(self, csv_path, vhd_file_path, vm_name_prefix='ODX_VM', number=1):
    """
    create the virtual machine and copy the the vhd file to the vitural machine

    Args:
    csv_path (str): the csv path
    vhd_file_path (str): the vhd file path
    vm_name_prefix (str): (Optional)the create virtual machien name prefix
    number (int): (Optional)the create number

    Returns:
    vm_paths (list): the create vm paths list
    """


self.logger.info('create vm in %s name prefix %s number %s with vhd file %s'
                 % (csv_path, vm_name_prefix, number, vhd_file_path))
params = self.ps_params.copy()
params['SrcVHDFile'] = vhd_file_path
params['DstDir'] = csv_path
params['Concurrency'] = number
params['VMNamePrefix'] = vm_name_prefix

result = self.run_powershell_script(hyperv_alias.PREPARE_VMS, params=params, on_new_sessoin=True)
vm_paths = result['vm_paths'].split(' ')
return vm_paths


def migrate_vms(self, src_csv_path, dst_csv_path, vm_name_prefix=None, number=1):
    """
    migrate the vms from src csv to dst csv

    Args:
    src_csv_path (str): the csv path
    dst_csv_path (str): the vhd file path
    vm_name_prefix (str): (Optional)the virtual machine`s name prefix who need to migrate
    number (int): (Optional)the migrate vm number, default is 1

    Returns:
    result (dict): powershell test case result
    """


if vm_name_prefix is None:
    vm_name_prefix = '*'
self.logger.info('migrate vm from %s to %s name prefix %s'
                 % (src_csv_path, dst_csv_path, vm_name_prefix))
params = self.ps_params.copy()
params['SrcDir'] = src_csv_path
params['DstDir'] = dst_csv_path
params['VMNamePrefix'] = vm_name_prefix
params['Concurrency'] = number

result = self.run_powershell_script(hyperv_alias.MIGRATE_VMS, params=params, on_new_sessoin=True)
return result


def init_hyperv_env(self):
    script_params = {
        'UserName': self.username,
        'Password': self.password,
    }


self.run_powershell_script(hyperv_alias.INIT_ENV, params=script_params)


def import_vms(self, csv_path, template_path, vm_name_prefix='ODX_BKG_IO_VM', number=1):
    """
    create the virtual machine and copy the the vhd file to the vitural machine

    Args:
    csv_path (str): the csv path
    template_path (str): the virtual machine template path
    vm_name_prefix (str): (Optional)the create virtual machine name prefix
    number (int): (Optional)the create number

    Returns:
    result (dict): powershell test case result
    """


self.logger.info('import vm in %s name prefix %s number %s with template %s'
                 % (csv_path, vm_name_prefix, number, template_path))
params = self.ps_params.copy()
params['SrcDir'] = template_path
params['DstDir'] = csv_path
params['Concurrency'] = number
params['VMNamePrefix'] = vm_name_prefix

result = self.run_powershell_script(hyperv_alias.IMPORT_VMS, params=params, on_new_sessoin=True)
result['vm_paths'] = result['vm_paths'].split(' ')
return result


def export_vms(self, src_path, dst_path, vm_name_prefix='ODX_VM', number=1):
    """
    create the virtual machine and copy the the vhd file to the vitural machine

    Args:
    src_path (str): the virtual machine source path
    dst_path (str): the export virtual machine destination path
    vm_name_prefix (str): (Optional)the create virtual machine name prefix
    number (int): (Optional)the create number

    Returns:
    result (dict): powershell test case result
    """


self.logger.info('export vm in %s name prefix %s number %s to path %s'
                 % (src_path, vm_name_prefix, number, dst_path))
params = self.ps_params.copy()
params['SrcDir'] = src_path
params['DstDir'] = dst_path
params['Concurrency'] = number
params['VMNamePrefix'] = vm_name_prefix

result = self.run_powershell_script(hyperv_alias.EXPORT_VMS, params=params, on_new_sessoin=True)
return result


def add_vm_disks(self, vm_path, luns):
    """
    add virtual machine disks by luns` wwn

    Args:
    vm_path (str): the virtual machine path
    luns (list): the lun object list

    Returns:
    result (dict): powershell test case result
    """


params = self.ps_params.copy()
luns_wwn = [lun.getProperty('wwn') for lun in luns]
luns_wwn_str = ','.join(["'%s'" % wwn for wwn in luns_wwn])
luns_wwn_str = '(%s)' % luns_wwn_str
params['LUNWWNs'] = luns_wwn_str
params['VMPath'] = vm_path
result = self.run_powershell_script(hyperv_alias.ADD_VM_DISKS, params=params, on_new_sessoin=True)
return result


def power_on_vms(self, vm_name_prefix, number=1):
    """
    power on the virtual machines

    Args:
    vm_name_prefix (str): the virtual machine prefix name
    number (int): (Optional)the power on vm number

    Returns:
    result (dict): powershell test case result
    """


params = self.ps_params.copy()
params['Concurrency'] = number
params['VMNamePrefix'] = vm_name_prefix

result = self.run_powershell_script(hyperv_alias.POWERON_VMS, params=params, on_new_sessoin=True)
return result


def remove_item(self, path):
    """
    remove the file or dir

    Args:
    path (str): the file or dir path

    """


self.logger.info('remove the file or dir path is %s' % path)
self.run_powershell({'command': ['Remove-Item', path, '-Recurse']})


def remove_csv_files(self, csv_path):
    csv_path = self.transfer_path(csv_path)


path = '%s\\%s' % (csv_path, '*')
self.remove_item(path)


def get_csvs_by_luns(self, luns):
    params = self.ps_params.copy()


luns_wwn = [lun.getProperty('wwn') for lun in luns]
luns_wwn_str = ','.join(["'%s'" % wwn for wwn in luns_wwn])
luns_wwn_str = '(%s)' % luns_wwn_str
params['LUNWWNs'] = luns_wwn_str
result = self.run_powershell_script(hyperv_alias.GET_CSV_BY_WWN, params=params)
csvs = sorted(result['csv_paths'].split(' '))
self.logger.info('the csvs is %s' % csvs)
return csvs


def get_disk_number_by_wwn(self, luns):
    params = self.ps_params.copy()


luns_wwn = [lun.getProperty('wwn') for lun in luns]
luns_wwn_str = ','.join(["'%s'" % wwn for wwn in luns_wwn])
luns_wwn_str = '(%s)' % luns_wwn_str
params['LUNWWNs'] = luns_wwn_str
result = self.run_powershell_script(hyperv_alias.GET_DISK_NUMBER_BY_WWN, params=params)
num = result['cluster_disk_number'].split(' ')
self.logger.info('the cluster disk number is %s' % num)
return num


def get_lun_wwns_by_csvs(self, csv_paths):
    params = self.ps_params.copy()


csv_paths_str = ','.join(["'%s'" % csv_path for csv_path in csv_paths])
csv_paths_str = '(%s)' % csv_paths_str
params['CSVPaths'] = csv_paths_str
result = self.run_powershell_script(hyperv_alias.GET_WWN_BY_CSV, params=params)
lun_wwns = result['lun_wwns'].lower().split(' ')
self.logger.info('the lun wwns are %s' % lun_wwns)
return lun_wwns


def format_csv(self, luns, full_copy=False):
    """
    format the csv

    Args:
    luns (list): the lun object
    full_copy (bool): (Optional)if use full copy

    Returns:
    result (dict): powershell test case result
    """


params = self.ps_params.copy()
luns_wwn = [lun.getProperty('wwn') for lun in luns]
luns_wwn_str = ','.join(["'%s'" % wwn for wwn in luns_wwn])
luns_wwn_str = '(%s)' % luns_wwn_str
params['LUNWWNs'] = luns_wwn_str
params['Concurrency'] = len(luns)
if full_copy:
    params['FullFormat'] = ''
result = self.run_powershell_script(hyperv_alias.FORMAT_DISKS, params=params, on_new_sessoin=True)
return result


def transfer_path(self, path):
    """
    由于powershell不支持/斜杠，所有需要将/转换成\\
    :param path: 文件或者文件夹路径
    :return: 转移后的路径
    """


self.logger.info('transfer the path %s / to \\' % path)
return str(path).replace('/', '\\')

