#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：苹果操作系统mac类
"""

from Libs.Unix import Unix
from Libs.Exception.UniAutosException import UniAutosException
import re

class Mac(Unix):
    """MAC主机类, 继承于Unix类

    提供主机操作相关接口，如: 创建分区， 创建文件系统等.

    Args:
        username (str): MAC主机登陆使用的用户名, 建议使用root用户.
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

    Attributes:
        self.os (str): 主机的操作系统类型, 指定为: 'MAC'.
        self.openIscsi (bool): 主机是否安装openIscsi, 默认为False; False: 未安装，True: 已安装.

    Returns:
        Mac (instance): MAC主机对象实例.

    Raises:
        None.

    Examples:
        None.
    """

    def __init__(self, username, password, params):
        super(Mac, self).__init__(username, password, params)
        self.os = 'Mac'
        pass

    def getSystemInfo(self):
        """获取Mac操作系统信息

        Args:
            None

        Returns:
            syncSystemInfo (dict): Mac操作系统信息, 键值对说明如下:
            host_name (str): 主机名，例如 'Numbers.local'
            os_type (str): 操作系统类型, 例如 'Mac'
            kernel_name (str): 内核名, 例如 'Darwin'
            kernel_release (str): 内核发布版本,　例如 '12.0.0'
            kernel_version (str): 内核版本信息,　例如 'Darwin Kernel Version 12.0.0: Mon Jan 30 18:41:34 PST 2012'
            hardware_name (str): 硬件名,　例如　'root:xnu-2050.1.12~1/RELEASE_X86_64'
            processor_type (str): 处理器类型,　例如　'x86_64'
            hardware_platform (str): 硬件平台,　例如　'root:xnu-2050.1.12~1/RELEASE_X86_64'

        Raises:
            CommandException: 获取系统信息命令执行失败.

        Examples:
            macObj.getSystemInfo()
            Output:
                {'host_name': 'Numbers.local',
                'os_type': 'Mac',
                'kernel_name': 'Darwin',
                'kernel_release': '12.0.0',
                'kernel_version': 'Darwin Kernel Version 12.0.0: Mon Jan 30 18:41:34 PST 2012'
                'hardware_name': 'root:xnu-2050.1.12~1/RELEASE_X86_64'
                'processor_type' : 'x86_64'
                'hardware_platform' : 'root:xnu-2050.1.12~1/RELEASE_X86_64'}
        """
        if hasattr(self, "systemInfo"):
            return self.systemInfo

        syncSystemInfo = {}

        res = self.run({'command' :['uname', '-a']})
        if 'stdout' in res and res['stdout'] is not None:
            syncSystemInfo['stdout'] = res['stdout'].strip()
            orignalInfo = re.split("\s+", res['stdout'])

            syncSystemInfo['os_type'] = 'MAC'
            syncSystemInfo['kernel_name'] = orignalInfo.pop(0)
            syncSystemInfo['host_name'] = orignalInfo.pop(0)
            syncSystemInfo['kernal_release'] = orignalInfo.pop(0)

            syncSystemInfo['processor_type'] = orignalInfo.pop()
            syncSystemInfo['hardware_platform'] = orignalInfo.pop()

            syncSystemInfo['kernal_version'] = ' '.join(orignalInfo)

            syncSystemInfo['hardware_name'] = syncSystemInfo['hardware_platform']
        else:
            raise UniAutosException("Cannot get the system information")

        self.systemInfo = syncSystemInfo

        return syncSystemInfo

    def getSoftwareVersion(self):
        """获取Mac软件版本信息

        Args:
        None

        Returns:
        swInfo (dict): Mac软件版本信息, 键值对说明如下:
        product_name (str): 产品名，例如 'Mac OS X'
        product_version (dict): 产品版本
        full (str): 全称, 例如'10.8'
        major (str): 大版本号, 例如 '10'
        minor (str): 小版本号, 例如 '8'
        build_version (str): 软件build信息, 例如 '12A128p'

        Raises:
        CommandException: 获取MAC软件信息命令执行失败.

        Examples:
        macObj.getSoftwareVersion()
        Output:
        {'product_name': 'Mac OS X',
        'product_version': {
        'full': '10.8',
        'major': '10',
        'minor': '8',},
        'build_version': '12A128p'}

        """
        res = self.run({'command' :['sw_vers'], 'check_rc':True})

        swInfo = {}
        for line in self.split(res['stdout']):
            nameGroups = re.match('^ProductName\:\s+(.+)', line, re.IGNORECASE)
            if nameGroups:
                swInfo['product_name'] = nameGroups.groups(1)
                continue

            verGroups = re.match('^ProductVersion\:\s+(.+)', line, re.IGNORECASE)
            if verGroups:
                swInfo['priduct_version']['full'] = verGroups.groups(1)
                verSplit = re.split("\.", swInfo['priduct_version']['full'])
                swInfo['priduct_version']['major'] = verSplit.pop(0)
                swInfo['priduct_version']['minor'] = verSplit.pop(0)
                continue

            buildGroups = re.match('^BuildVersion\:\s+(.+)', line, re.IGNORECASE)
            if buildGroups:
                swInfo['build_version'] = buildGroups.groups(1)
                continue
        return swInfo

    def isOsX(self):
        """判断该MAC主机是否为OsX

        Args:
            None

        Returns:
            isOsX (Boolean): 1 : 该MAC主机是OsX
            0 : 该MAC主机不是OsX

        Raises:
            CommandException: 获取MAC软件信息命令执行失败.

        Examples:
            macObj.isOsX()
        """
        swInfo = self.getSoftwareVersion()
        matcher = re.search("Mac\s*OS\s*X", swInfo['product_name'], re.IGNORECASE)
        if 'product_name' in swInfo and not matcher:
            return 1
        return 0

    def mountNfsFilesystem(self, export, mountpoint=None):
        """在MAC主机上mount NFS 文件系统

        Args:
            export (str): 必选参数，被mount的文件系统export路径
            mountpoint (str): 可选参数，被挂载文件系统在MAC主机上的路径，如果为空，则系统会自动生成一个MAC主机上的文件路径

        Returns:
            mountpoint (str): 返回该NFS文件系统在MAC主机上mount的路径

        Raises:
            CommandException: 获取MAC软件信息命令执行失败.

        Examples:
            mountpoint = macObj.mountNfsFilesystem()
        """
        cmds = ['mount', '-t', 'nfs']
        cmds.append(export)
        if not mountpoint:
            mountpoint = self.createRandomDirectory('/mnt', 'uniAutos_mac_%c%c%%d%d')
        if not self.doesPathExist({'path' : mountpoint}):
            self.createDirectory(mountpoint)
        cmds.append(mountpoint)
        self.run({'command' : cmds, 'check_rc' : True})
        return mountpoint


    def getMountpoints(self, device=None):
        """在MAC主机上mount NFS 文件系统

        Args:
            device (str): 可选参数，默认值为None，用来过滤符合该device的挂载点，例如 /dev/huaweiUltraPath

        Returns:
            mountpoint (dict): 该字典包含MAC主机上以device为主键的所有挂载点
            {'/dev/emcpowerab1' : {
            mountpoints : ['/mnt/huawei/luns/ab/1', '/mnt/huawei/luns/ab/2']
            partition : '/dev/huaweipowerab1',
            type : 'NFS'
            }

            }

        Raises:
            CommandException: 获取MAC软件信息命令执行失败.

        Examples:
            retDict = macHostObj.getMountpoints();
            Output:
                retDict['/dev/emcpowerab1'] = {
                mountpoints => [/mnt/huawei/luns/ab/1, /home/huawei/ab/1],
                partition => '/dev/huaweipowerab1',
                type => NFS,
                }
        """
        reps = self.run({'command' : ['mount', '-v']})
        retDict = {}
        for line in self.split(reps['stdout']):
            matchers = re.match('^(\S+) on (.+?) \((\S+)\,', line)
            if matchers and not re.search('none', matchers.group(1)):
                continue
            lineDevice = matchers.group(1)
            lineMount = matchers.group(2)
            mpType = matchers.group(3)
            if device and lineDevice != device:
                continue
            if lineMount == '/':
                self.rootDisk = lineDevice
            if lineDevice not in retDict:
                retDict[lineDevice] = {}
                retDict[lineDevice]['mountpoints'].append(lineMount)
                retDict[lineDevice]['partition'] = lineDevice
                retDict[lineDevice]['type'] = mpType
        return retDict