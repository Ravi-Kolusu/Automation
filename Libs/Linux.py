#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能: Linux主机类, 提供主机操作相关接口，如: 创建分区， 创建文件系统等.
"""

import re
import os
from Libs.Unix import Unix
from Libs.Time import sleep
from Libs.Units import Units, BYTE, MEGABYTE, SECOND
#from UniAutos.Component.Lun.LunBase import LunBase
#from UniAutos.Component.Snapshot.Huawei.OceanStor.Lun import Snapshot as SnapshotBase
#from UniAutos.Component.Snapshot.Huawei.Roc.Roc import Snapshot as RocSnapShotBase
#from UniAutos.Component.Filesystem.FilesystemBase import FilesystemBase
#from UniAutos.Component.Volume.Huawei.DSware import Volume
from Libs.Exception.CustomExceptions import CommandException
from Libs.Exception.CustomExceptions import FileNotFoundException
from Libs.Exception.CustomExceptions import InvalidParamException
from Libs.Exception.UniAutosException import UniAutosException
#from UniAutos.Component.Upgrade.Huawei.Simulator import Simulator
#from UniAutos.Util.Fault import Fault
import threading
import random
import textwrap
import time
import datetime
from Libs.Threads import Threads


class Linux(Unix):
    """Linux主机类, 继承与Unix类

    提供主机操作相关接口，如: 创建分区， 创建文件系统等.

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

    Attributes:
        self.os (str): 主机的操作系统类型, 指定为: 'Linux'.
        self.openIscsi (bool): 主机是否安装openIscsi, 默认为False; False: 未安装，True: 已安装.

    Returns:
        Linux (instance): Linux主机对象实例.

    Raises:
        None.

    Examples:
        None.
    """
    def __init__(self, username, password, params):
        super(Linux, self).__init__(username, password, params)
        self.os = 'Linux'
        self.openIscsi = False
        try:
            self.set_never_time_out()
        except Exception:
            pass
        self.glock = threading.Lock()

    def set_never_time_out(self):
        sys_info = self.run({"command": ["sh", "-c", "cat /proc/version"]})["stdout"]
        no_timeout = True if "Red Hat" in sys_info or "SUSE" in sys_info else False
        if no_timeout:
            self.logger.info("Set never timeout on the Red Hat operating system")
            self.run({"command": ["sh",
                                  "-c",
                                  "sed -i \'s/#ClientAliveInterval 0/ClientAliveInterval 60/g\' sshd_config"],
                                  "directory": "/etc/ssh"})
            self.run({"command": ["sh",
                                  "-c",
                                  "sed -i \'s/#ClientAliveCountMax 3/ClientAliveCountMax 3/g\' sshd_config"],
                                  "directory": "/etc/ssh"})
            self.run({"command": ["sh",
                                  "-c",
                                  "service sshd reload"]})

    def rescanDisk(self):
        """安装华为自研多路径的情况下重新扫描映射的LUN
        Examples:
            hostObj.rescanDisk()
        """
        self.logger.info("Starting to rescan the disks with command 'hot_add' on %s" % self.getIpAddress())
        try:
            self.glock.acquire()
            for times in range(3):
                result = self.run({"command": ["sh", "-c", "hot_add"], "timeout": 1800})['stdout']
                if result:
                    if result.find('ERROR') < 0:
                        return
                    sleep(1)
        finally:
            self.glock.release()

    def rescanDiskNoUltraPath(self):
        """不安装华为自研多路径的情况下重新扫描映射的LUN

        Examples:
            self.host.rescanDiskNoUltraPath()
        """
        self.logger.info("Starting to rescan the disks with command 'rescan-scsi-bus.sh' on %s" % self.getIpAddress())
        try:
            self.glock.acquire()
            # 当三条命令都没有报错，则退出，如果有命令报错，则循环执行三次
            for times in range(3):
                result1 = self.run({"command": ["sh", "-c", "rescan-scsi-bus.sh"]})['stdout']
                result2 = self.run({"command": ["sh", "-c", "lsscsi"]})['stdout']
                result3 = self.run({"command": ["sh", "-c", "fdisk -l"]})['stdout']
                # 如下命令为重新扫盘
            p = '\[(\d+):\d+:\d+:\d+\]\s+disk\s+HUAWEI\s+XSG1'
            rstList = list(set(re.findall(p, result2, re.S)))
            for rst in rstList:
                self.run({'command': ['sh', '-c', 'echo "- - -" > /sys/class/scsi_host/host%s/scan' % rst]})
            i = 0
            for result in (result1, result2, result3):
                if result:
                    if result.find('ERROR') < 0:
                        i += 1
                    sleep(1)
            if i == 3:
                return
        finally:
            self.glock.release()

    def getDisk(self, diskLabel):
        """获取主机指定的单个磁盘信息, 该方法仅适用于Linux

        Args:
            diskLabel (str): 映射的Lun在Linux上的设备名称，如: "/dev/sdb"(不是分区, 如: "/dev/sdb1").

        Returns:
            diskInfo (dict): 获取的磁盘信息, diskInfo键值对说明:
            size (str): 指定磁盘的总容量.
            partition (dict): 指定磁盘的分区信息, getPartitions()接口获取, 参考由getPartitions()说明.

        Raises:
            CommandException: 指定磁盘不存在时抛出异常.

        Examples:
            hostObj.getDisk("/dev/sdb")
            Output:
            {'partitions': [
            {'end': '3051MB',
            'fs': None,
            'info': 'linux',
            'label': 'msdos',
            'mounts': [],
            'partition': '/dev/sdb3',
            'size': '1024MB',
            'start': '2027MB',
            'status': None,
            'type': 'primary'},],
            'size': '10.7GB'}
        """
        diskInfo = {}
        response = self.run({"command": ["sh", "-c", "fdisk", diskLabel, "-l"]})

        if response["rc"] != 0:
            raise CommandException("Could not find disk %s" % diskLabel)

        size = re.search(r"((\d+(\.\d*)?)|0\.\d+) ([GKMTP]?B)", response["stdout"])
        if size:
            size = size.group()
        hasPartition = True
        if re.search(r'doesn\'t contain a valid partition table', response["stdout"]):
            hasPartition = False
        if re.search(r'' + str(diskLabel) + '\d+', response["stdout"]) is None:
            hasPartition = False

        partitions = []
        if hasPartition:
            partitions = self.getPartitions(disk=diskLabel)
        diskInfo = {"size": size.replace(" ", ""),
        "partitions": partitions}
        return diskInfo

    def getDisks(self):
        """获取当前主机的磁盘信息，包含磁盘名称和容量"""
        diskInfo = {}
        response = self.run({"command": ["sh", "-c", "fdisk", "-l"]})

        if response["rc"] != 0:
            raise CommandException("Could not find disks")

        regex = re.compile(r'^Disk\s*(/dev/\S*):\s*(\d+\.\d+\s+\w+),')
        lines = self.split(response['stdout'])
        for l in lines:
            matcher = regex.match(l)
            if matcher:
                disk = matcher.groups()[0]
                size = matcher.groups()[1]
                diskInfo.update({disk: size})
        return diskInfo

    def getPartitions(self, lunComponent=None, disk=None, raw=False):
        """获取指定的Lun对象或磁盘设备的分区信息

        Args:
            lunComponent (instance): Lun实例对象，lunComponent和disk都未指定时获取全部分区, 可选参数, 默认为None.
            disk (str): 需要获取分区信息的磁盘设备, 可选参数, 默认为None, 如: "/dev/sdb".
            raw (bool): 是否只获取文件系统类型为raw的分区, True为只获取raw分区，False获取全部,
            -可选参数，默认为False.

        Returns:
            retArr (dict)：指定Lun对象或磁盘设备的分区信息,reArr键值对说明:
            end (str): 分区在磁盘设备的结束位置, Linux操作系统专有.
            fs (str): 分区的文件系统类型.
            info (str): 分区系统信息, linux系统分区一般为"Linux".
            label (str): 分区标签.
            mounts (list): 分区的挂载目录, 一个分区可以挂载多个目录.
            partition (str): 分区名称.
            size (str): 分区大小.
            start (str): 分区在磁盘设备的开始位置, Linux操作系统专有.
            status (str): Linux默认为None.
            type (str): 分区类型, 如: primary, extended等.

        Raises:
            CommandException: 命令执行失败，未找到分区时抛出异常.

        Examples:
            hostObj.getPartitions(disk="/dev/sdb", raw=True) or hostObj.getPartitions(lun=LunObj, raw=True)
            Output:
            [{'end': '1003MB',
            'fs': 'ext2',
            'info': 'linux',
            'label': 'msdos',
            'mounts': [],
            'partition': '/dev/sdb1',
            'size': '1003MB',
            'start': '32.3kB',
            'status': None,
            'type': 'primary'},
            {'end': '4075MB',
            'fs': 'ext2',
            'info': 'linux',
            'label': 'msdos',
            'mounts': ['/mnt'],
            'partition': '/dev/sdb4',
            'size': '1024MB',
            'start': '3051MB',
            'status': None,
            'type': 'primary'}]
        """
        partitions = []
        if lunComponent:
            disk = self._getDiskDevice(lunComponent)

        if disk:
            response = self.run({"command": ["sh", "-c", "parted", disk, "-s", "p"]})
        else:
            response = self.run({"command": ["sh", "-c", "parted", "-l"]})

        if response["rc"] != 0:
            if re.search(r'unrecognised disk label', response["stdout"]):
                raise CommandException("There are no partitions on disk %s" % disk)
            raise CommandException("Unable to find any partitions.")
        mounts = self.getMountPoints()

        currentDisk, currentLabel = '', ''
        retArr, vols, volMntMap = [], [], {}
        for line in self.split(response["stdout"]):
            currentDiskMatch = re.search(r'/dev((/\w+)*)', line)
            if currentDiskMatch:
                currentDisk = "/dev" + currentDiskMatch.group(1)
                continue

            currentLabelMatch = re.search(r'Partition Table: (\w+)', line)
            if currentLabelMatch:
                currentLabel = currentLabelMatch.group(1)
                continue

            partitionMatch = re.search(r'\d+\s+\d+', line)
            if partitionMatch:
                vols = re.split(r'\s+', self.trim(line))
                partition = currentDisk + vols[0]
                if len(vols) > 5 and re.match(r'\w+\d*', vols[5]):
                    fs = vols[5]
                else:
                    fs = None
                if not fs and raw:
                    continue
                mnt = []
                if partition in mounts and "mount_points" in mounts[partition]:
                    mnt = mounts[partition]["mount_points"]

                tmpInfo = {"partition": partition,
                            "mounts": mnt,
                            "label": currentLabel,
                            "fs": fs,
                            "type": vols[4],
                            "size": vols[3],
                            "start": vols[1],
                            "end": vols[2],
                            "status": None,
                            "info": "linux"}
                retArr.append(tmpInfo)
                volMntMap[partition] = tmpInfo
        return retArr

    def getDiskDeviceName(self, lunComponent):
        """获取指定Lun对象映射到主机的设备名称

        Args:
            lunComponent (instance): lun对象.

        Returns:
            device (str|None): 映射的Lun对象的设备名称.

        Raises:
            CommandException: 命令执行失败.

        Examples:
            device = hostObj._getDiskDevice(lun)
            Output:
            >"/dev/sdb"
        """
        result = []
        for time in xrange(5):
            try:
                if time == 4:
                    result = self._getDiskDeviceNew(lunComponent)
                else:
                    result = self._getDiskDevice(lunComponent)
                    break
            except CommandException as e:
                if e.message.startswith('No device name was found for lun ') and time < 4:
                    sleep(1)
                    self.rescanDisk()
            else:
                raise CommandException(e.message)
        return result

    def getNasMountPoints(self, fileComponent):
        """Get the Filesystem mount point in linux environment

        Args:
            fileComponent Type(FilesystemBase): FileSystem component object

        Returns:
            mountPoint Type(str): The file system mount point in linux environment

        Raises:
            None

        Changes:
            2015/12/24 y00305138 Created
        """
        fileName = ""
        if isinstance(fileComponent, FilesystemBase):
            fileName = fileComponent.getProperty("name")
        else:
            raise InvalidParamException("%s is not a filesystem Component. " % fileComponent)
        response = self.run({"command": ["sh", "-c", "df"]})
        if response["rc"] != 0:
            raise CommandException(response["stderr"])
        lines = self.split(response["stdout"])
        for line in lines:
            if re.search(r'/' + str(fileName) + '', line):
                tmpStr = self.trim(line)
                tmpMatch = re.search('\s+(\S+)$$', tmpStr)
                if tmpMatch:
                    device = self.trim(tmpMatch.group())
                    return device
        return None

    def getFileShareIoPath(self, fileComponent):
        """Get the IO path for special file share directory

        Args:
            fileComponent Type(FilesystemBase): FileSystem component objectone

        Returns:
            None

        Raises:
            None

        Changes:
            2015/12/24 y00305138 Created
        """
        fileMountPoint = self.getNasMountPoints(fileComponent)

        if fileMountPoint is not None:
            ioFile = "%s/%s" % (fileMountPoint, "io_file")
            self.createFile(ioFile)
            return ioFile
        else:
            raise CommandException("%s has no share directory" % fileComponent)

    def getIqn(self):
        """获取该主机的Iqn信息

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
        """
        self._checkOpenIscsi()
            return self._parseIqn("/etc/iscsi/initiatorname.iscsi")

    def removeIqn(self):
        """移除主机上的Iqn信息

        Examples:
            self.host.removeIqn()

        """
        self._checkOpenIscsi()

        def iqnParser(output):
            """解析主机上的Iqn信息

            Args:
                output type(str): 命令回显

            Return:
                result: ['iqn.2006-08.com.huawei:oceanstor:2100e09796b5fa4f::21f01:130.46.81.90',
                'iqn.2006-08.com.huawei:oceanstor:2100e09796b5fa4f::1020700:8.47.81.91']
            """
            result = []
            # 将回显根据换行符进行切割
            if output:
                output = re.split("\x0d?\x0a|\x0d", output)
            else:
                return result
            for line in output:
                if 'iqn' in line:
                    iqn = line.split()[1]
                    result.append(iqn)
            return result

        output = self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node"]})
        if output:
            output = output['stdout']
            iqns = iqnParser(output)
            if iqns:
                for iqn in iqns:
                    # 注销iqn
                    self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node",
                                          "--targetname", "%s" % iqn, "--logout"]})
                    # 删除iqn
                    response = self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node", "--op",
                                                     "delete", "--targetname", "%s" % iqn]})
                    if response["rc"] != 0:
                        self.logger.debug("Remove iqn: [%s] failed." % iqn)
                    else:
                        self.logger.debug("Remove iqn: [%s] successfully." % iqn)

    def _checkOpenIscsi(self):
        """检查主机是否安装open iSCSI软件, 该方法外部不可直接调用

        Args:
            None.

        Returns:
            None.

        Raises:
            FileNotFoundException: 未安装openIscsi软件.

        Examples:
            None.
        """
        if self.which("iscsiadm"):
            self.openIscsi = True
        else:
            raise FileNotFoundException("Open iSCSI is not installed on this Host.")

    def _parseIqn(self, filePath):
        """获取主机的Iqn信息, 该方法外部不可直接调用

        Args:
            filePath (str): iqn所在的文件路径, 默认指定为: "/etc/iscsi/initiatorname.iscsi".

        Returns:
            iqn (str): 主机的iqn.

        Raises:
            FileNotFoundException: 指定的iqn文件不存在或打开文件失败.

        Examples:
            None.
        """
        iqn = ""
        response = self.run({"command": ["sh", "-c", "cat", filePath]})
        if response["rc"] != 0:
            raise FileNotFoundException("Could not found the Open iSCSI initiatorname file. Please make sure you have Open iSCSI installed properly.")

        lines = self.split(self.trim(response["stdout"]))

        for line in lines:
            if re.search(r'cat', line):
                continue
            match = re.search(r'InitiatorName=(\S+)', line)
            if match:
                iqn = match.group(1)
                return iqn

    def _service(self, name, action):
        """Linux操作系统服务查询、启动、停止, 该方法外部不可直接调用.

        Args:
            name (str): 服务名称.
            action (str): 服务需要执行的操作, 取值范围为: start、stop、status.

        Returns:
            status (str): 当执行状态查询时返回服务的状态, 返回值为"running"或"stopped".
            当执行启动或停止服务操作时返回None.

        Raises:
            InvalidParamException: action非法.

        Examples:
            None.
        """
        if re.match(r'(start|stop|status)', action) is None:
            raise InvalidParamException("Service action is invalid.")

        response = self.run({"command": ["sh", "-c", "service", name, action]})

        if action == "status" and response["stdout"]:
            if re.search(r'running', response["stdout"]):
                return "running"
            elif re.search(r'stopped|unused', response["stdout"]):
                return "stopped"
        elif action == "status" and response["stdout"] is None:
            self.logger.warn("Query Service %s status Failed, Error:/n %s" % (name, response["stderr"]))

        if (action == "start" or action == "stop") \
        and response["rc"] != 0 and re.search(r'done|ok', response["stdout"], re.I) is None:
            raise CommandException("Service %s %s Failed" % (name, action))

    def startService(self, name):
        """打开指定Linux操作系统服务

        Args:
            name (str): 服务名称.

        Returns:
            None.

        Raises:
            CommandException: 命令执行失败.

        Examples:
            host.startService("smb")
        """
        return self._service(name, "start")

    def stopService(self, name):
        """停止指定Linux操作系统服务

        Args:
            name (str): 服务名称.

        Returns:
            None.

        Raises:
            CommandException: 命令执行失败.

        Examples:
            hostObj.stopService("smb")
        """
        return self._service(name, "stop")

    def getServiceStatus(self, name):
        """获取指定Linux操作系统的服务状态

        Args:
            name (str): 服务名称.

        Returns:
            status (str): 服务状态信息， 返回值为"running"或"stopped".

        Raises:
            CommandException: 命令执行失败.

        Examples:
            hostObj.getServiceStatus("smb")
        Output:
            >"running"
        """
        return self._service(name, "status")

    def getHbaInfo(self):
    """获取主机HBA卡的信息

    Args:
    None.

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
    response = self.run({"command": ["sh", "-c", "ls", "-l", "\'/sys/class/fc_host/\'"]})
    if response["rc"] != 0 and re.search(r'No such file or directory', response["stderr"]):
    self.logger.warn("No HBA card found on host.", self.getIpAddress())
    return
    elif response["rc"] != 0:
    raise CommandException(response["stderr"])

    lines = self.split(response["stdout"])
    hbaAdapter = []

    for line in lines:
    if re.search(r'host[0-9]+', line):
    self.logger.info('#####[Debug Log]%s' % line)
    hbaAdapter.append(re.search(r'host[0-9]+', line).group())

    hbaDict = {}
    for adapter in hbaAdapter:
    response = self.run({"command": ["sh", "-c", "cat", "port_name", "node_name"],
    "directory": "/sys/class/fc_host/%s" % adapter})
    lines = self.split(response["stdout"])
    for line in lines:
    if re.search(r'cat', line):
    continue
    port = None
    if re.match(r'^0x', line):
    port = self.normalizeWwn(line)
    if port and re.match(r'^0x', lines[lines.index(line) + 1]):
    hbaDict[port] = {"port": port,
    "node": self.normalizeWwn(lines[lines.index(line) + 1])}
    break
    return hbaDict

    def getProcessId(self, processName):
    """获取指定进程名称的进程ID

    Args:
    processName (str): 进程名称.

    Returns:
    reArr (list): 指定进程名称的所有进程id.

    Raises:
    CommandException: 命令执行失败.

    Examples:
    pids = hostObj.getProcessId("sshd")
    Output:
    >['22912', '23430', '27333', '29117', '30581']

    """
    response = self.run({"command": ["sh", "-c", "ps", "-C", processName, "-o", "pid"]})
    if response["rc"] != 0:
    raise CommandException("Unable to find any processes with given process name: %s" % processName)

    retArr = []
    for line in self.split(response["stdout"]):
    tmpMatch = re.match(r'\d+', self.trim(line))
    if tmpMatch:
    retArr.append(tmpMatch.group())
    return retArr

    def getTargets(self):
    """获取主机中的ISCSI所有目标器

    Args:
    None

    Returns:
    targets (dict): 所有查询到的target信息, targets键值对说明:
    key (str): 目标器名称.
    value (list): 目标器所属的IP(target portal).

    Raises:
    CommandException: 命令执行失败.

    Examples:
    targets = hostObj.getTargets()
    Output:
    >{'iqn.2006-08.com.huawei:oceanstor:21000022a11055fa::1022006:129.94.10.11': ['129.94.10.11'],
    'iqn.2006-08.com.huawei:oceanstor:21000022a11055fa::22006:129.94.10.10': ['129.94.10.10'],
    'iqn.2006-08.com.huawei:oceanstor:2100313233343536::1020200:129.181.100.107': ['129.181.100.107'],
    'iqn.2006-08.com.huawei:oceanstor:2100313233343536::20200:128.181.100.107': ['128.181.100.107'],
    'iqn.2006-08.com.huawei:oceanstor:2100ac853ddbc42f::1020000:128.94.255.10': ['128.94.255.10'],
    'iqn.2006-08.com.huawei:oceanstor:2100ac853ddbc42f::20000:129.94.255.10': ['129.94.255.10'],
    'iqn.2006-08.com.huawei:oceanstor:2100ac853ddbc4a9::20000:128.94.255.12': ['128.94.255.12'],
    'iqn.2006-08.com.huawei:oceanstor:2100ac853ddbc4a9::20000:129.94.255.12': ['129.94.255.12']}

    """
    self._checkOpenIscsi()

    response = self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node", "list"]})
    targets = {}
    if response["rc"] != 0:
    self.logger.warn(response['stderr'])
    return targets

    lines = self.split(response["stdout"])
    for line in lines:
    tmpMatch = re.match("(\S+):\S+,\d+\s+(\S+)", line)
    if tmpMatch:
    ip = tmpMatch.group(1)
    target = tmpMatch.group(2)
    if target in targets:
    targets[target].append(ip)
    else:
    targets[target] = [ip]

    return targets

    def upadminShowPath(self):
    """获取upadmin show path的回显

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
    response = self.run({"command": ["sh", "-c", "upadmin", "show", "path"]})
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

    def upadminSetPathState(self, pathstate, pathIDList=[], portId=None, number=None):
    """在主机侧端口链路的断开和恢复

    Args:
    storageDevice (object): storageDevice对象
    tpgstate (str): 开启或禁用控制器模块:enable、disable
    portId (str): 端口ID
    pathIDList (list): 需要回复的链路id

    Returns:
    None

    Raises:
    CommandException: 命令执行失败.

    Examples:
    pathIDList = host.upadminSetPathState(pathstate = "disable", controllerId = "0A")
    host.upadminSetPathState(pathstate = "enable", pathIDList = pathIDList)


    """
    pathInfoList = self.upadminShowPath()
    if portId is not None:
    for pathInfo in pathInfoList:
    if pathInfo["port_id"] == portId:
    pathIDList.append(pathInfo["path_id"])
    if number is not None:
    if pathIDList == []:
    for pathInfo in pathInfoList:
    if pathInfo["path_state"] == "Normal":
    pathIDList.append(pathInfo["path_id"])
    if len(pathIDList) < number:
    raise InvalidParamException("normal path number:%s is not enough" % len(pathIDList))
    else:
    pathIDList = random.sample(pathIDList, number)

    if pathIDList == []:
    raise CommandException("Unable to find any path id for to SetPathState.")
    for pathId in pathIDList:
    commands = ["sh", "-c", "upadmin", "set", "pathstate=" + pathstate, "path_id=" + str(pathId)]
    response = self.run({"command": commands})
    if re.search(r'Succeeded in executing the command', response["stdout"]):
    self.logger.debug("tpgstate set succeeded.")
    else:
    self.logger.debug("tpgstate set succeeded.")
    # raise CommandException("pathstate set failed,path id is:%s." % pathId)
    return pathIDList

    def upadminShowArrary(self):
    """获取upadmin show array的回显

    Args:
    None

    Returns:
    targets (list): 所有查询到的阵列信息,.

    Raises:
    CommandException: 命令执行失败.

    Examples:
    targets = hostObj.upadminShowArrary()
    Output:
    Array ID Array Name Array SN Vendor Name Product Name
    0 Huawei.Storage DAu71fb15rf060f00004 HUAWEI XSG1
    Result:
    [ {'array_id': '0', 'vendor_name': 'HUAWEI', 'array_name': 'Huawei.Storage', 'product_name': 'XSG1', 'array_sn': 'DAu71fb15rf060g00004'}
    ]

    """
    response = self.run({"command": ["sh", "-c", "upadmin", "show", "array"]})
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

    def upadminSetTPGState(self, storageDevice, tpgstate, controllerId):
    """实现主机的控制器模块的故障和恢复

    Args:
    storageDevice (object): storageDevice对象
    tpgstate (str): 开启或禁用控制器模块:enable、disable
    controllerId (str): 控制器ID

    Returns:
    None

    Raises:
    CommandException: 命令执行失败.

    Examples:
    host.upadminSetTPGState(storageDevice = self.storageDevice, tpgstate = "disable", controllerId = "0A")
    host.upadminSetTPGState(storageDevice = self.storageDevice, tpgstate = "enable", controllerId = "0A")


    """
    arrayInfoList = self.upadminShowArrary()
    arrayID = None
    for arrayInfo in arrayInfoList:
    if arrayInfo["array_sn"] == storageDevice.SN:
    arrayID = arrayInfo["array_id"]
    if arrayID is None:
    raise CommandException("Unable to find any array id for storage sn:%s." % storageDevice.SN)
    commands = ["sh", "-c", "upadmin", "set", "tpgstate=" + tpgstate, "array_id=" + str(arrayID),
    "tpg_id=" + controllerId]
    response = self.run({"command": commands})
    if re.search(r'Succeeded in executing the command', response["stdout"]):
    self.logger.debug("tpgstate set succeeded.")
    else:
    raise CommandException("tpgstate set failed.")

def startNlockTest(self, dir, fileBegin, fileEnd, lockBegin, lockEnd, type,
toolPath='/opt/nlocktest/nlock_test', option=None):
"""使用nlock进行加锁测试

Args:
dir (str): 需要加锁的文件所在目录
fileBegin (int): 起始文件序号
fileEnd (int): 结束文件序号
lockBegin (int): 一个文件内起始lock序号
lockEnd (int): 一个文件内结束lock序号
type (str): 需要加锁的类型
option (str): 需要加锁的可选参数

Returns:
None

Raises:
CommandException: 命令执行失败.

Examples:
host.startNlockTest(dir = "/mnt/test2/dir", fileBegin = 1,
fileEnd = 2, lockBegin = 1, lockEnd =2, type = 'set')


"""
result = {}
if type == 'setw':
for i in xrange(lockBegin, lockEnd):
tempcmd = ["sh", "-c", toolPath, dir, str(fileBegin), str(fileEnd), str(i), str(i), type]
if option is not None:
tempcmd.append(option)
tempcmd.append('&')
response = self.run({"command": tempcmd, })
return
else:
cmd = ["sh", "-c", toolPath, dir, str(fileBegin), str(fileEnd), str(lockBegin), str(lockEnd), type]
if option is not None:
cmd.append(option)
response = self.run({"command": cmd})
match = re.search(r'total success\(\s*(\d+)\)\s*failure\(\s*(\d+)\)', response["stdout"])
if match:
result['success'] = int(match.group(1))
result['failure'] = int(match.group(2))
return result

def targetLogin(self, targetIqn, targetPortal=None, chapUser=None, chapPassword=None):
"""登陆ISCSI target

Args:
targetIqn (str): 目标器, 通常为target Iqn.
tartPortal (str): 目标器门户ip地址.
chapUser: (str): CHAP用户名, target配置了CHAP认证时.
chapPassword (str): CHAP密码.

Returns:
sessionIds (dict): target登陆后的会话ID, 键值对说明如下:
{"session_ids": }
sessionList (list): 主机上链接的target session id列表.


Raises：
None.

Examples:
sid = hostObj.targetLogin("iqn.2006-08.com.huawei:oceanstor:21000022a11055fa::22006:129.94.10.10")
Output:
>{'session_ids': ['4', '6']}

"""
self._checkOpenIscsi()
commands = []
nodeCmd = ["sh", "-c", "iscsiadm", "-m", "node", "--target", targetIqn]
if targetPortal is not None:
nodeCmd.extend(["--portal", targetPortal + ":3260"])
if chapUser is not None:
chapCmd = nodeCmd[:]
chapCmd.extend(["--op=update", "--name", "node.session.auth.authmethod", "--value=CHAP"])
commands.append(chapCmd)

userCmd = nodeCmd[:]
userCmd.extend(["--op=update", "--name", "node.session.auth.username", "--value=", chapUser])
commands.append(userCmd)

passCmd = nodeCmd[:]
passCmd.extend(["--op=update", "--name", "node.session.auth.password", "--value=", chapPassword])
commands.append(passCmd)

nodeCmd.append("--login")
commands.append(nodeCmd)

for cmd in commands:
self.run({"command": cmd})

sessions = self.getSessionMappings()
sessionIds = []
for sessionId in sessions:
if targetPortal is not None:
if sessions[sessionId]["portal"] == targetPortal:
sessionIds.append(sessionId)
else:
sessionIds.append(sessionId)
return {"session_ids": sessionIds}

def getSessionMappings(self):
"""获取主机ISCSI链接的映射信息

Args:
None.

Returns:
mapInfo (dict): ISCSI链接的映射信息, 键值对说明如下：
: {
target (str): 目标器Iqn.
portal (str): 目标器门户地址.
scsi_device (str): scsi设备.
scsi_bus (str): scsi总线.
scsi_target_id (str): scsi 目标器ID.
"luns": { (str): 内部Lun Id.
}}

Raises:
None.

Examples:
session = hostObj.getSessionMappings()
Output:
>{'4': {'luns': {1: '0', 2: '1'},
'portal': '129.94.10.10',
'scsi_bus': '00',
'scsi_device': 'scsi13',
'scsi_target_id': '0',
'target': 'iqn.2006-08.com.huawei:oceanstor:21000022a11055fa::22006:129.94.10.10'},
'6': {'luns': {3: '0', 4: '1'},
'portal': '129.94.10.11',
'scsi_bus': '00',
'scsi_device': 'scsi15',
'scsi_target_id': '0',
'target': 'iqn.2006-08.com.huawei:oceanstor:21000022a11055fa::1022006:129.94.10.11'}}

"""
self._checkOpenIscsi()
cmd = ["sh", "-c", "iscsiadm", "-m", "session", "-P", "3"]
response = self.run({"command": cmd, "waitstr": "linux:~ #"})
if response["rc"] != 0:
self.logger.error("Host %s get iscsi session mappings failed." % self.getIpAddress())
return None
else:
if re.search(r'No active sessions', response["stdout"]):
self.logger.debug("Host %s have not active iscsi session mappings." % self.getIpAddress())
return None
mapInfo = {}
lines = self.split(response["stdout"])
curSession, curTarget, curPortal = None, None, None
lunCnt = 1
for line in lines:
curTargetMatch = re.search(r'Target:\s+(\S+)', line)
if curTargetMatch:
curTarget = curTargetMatch.group(1)
curPortalMatch = re.search(r'Current Portal:\s+(\S+):', line)
if curPortalMatch:
curPortal = curPortalMatch.group(1)
curSessionMatch = re.search(r'SID:\s+(\d+)', line)
if curSessionMatch:
curSession = curSessionMatch.group(1)
mapInfo[curSession] = {"target": curTarget,
"portal": curPortal}
scsiMatch = re.search(r'(scsi\d+)\s+Channel\s+(\d+)\s+Id\s+(\d+)', line)
if scsiMatch and curSession in mapInfo and "scsi_device" not in mapInfo[curSession]:
mapInfo[curSession]["scsi_device"] = scsiMatch.group(1)
mapInfo[curSession]["scsi_bus"] = scsiMatch.group(2)
mapInfo[curSession]["scsi_target_id"] = scsiMatch.group(3)
lunMatch = re.search(r'scsi\d+\s+Channel\s+\d+\s+Id\s+\d+\s+Lun:\s+(\d+)$', line)
if lunMatch and curSession in mapInfo:
if "luns" not in mapInfo[curSession]:
mapInfo[curSession]["luns"] = {lunCnt: lunMatch.group(1)}
lunCnt += 1
else:
mapInfo[curSession]["luns"][lunCnt] = lunMatch.group(1)
lunCnt += 1
return mapInfo

def rescanIscsiTarget(self):
"""重新扫描ISCSI目标器

Args:
None.

Returns:
None.

Raises:
None.

Examples:
hostObj.rescanIscsiTarget()

"""
self._checkOpenIscsi()
self.run({"command": ["sh", "-c", "iscsiadm", "-m", "session", "-R"]})
return

def addTargetPortal(self, ip, chapUser=None, chapPassword=None):
"""添加目标器门户

Args:
ip (str): 目标器门户IP地址.
chapUser: (str): CHAP用户名, 如果目标器配置CHAP认证, 则需要指定CHAP用户名.
chapPassword: (str): CHAP密码.

Returns:
None.

Raises:
None.

Examples:
hostObj.addTargetPortal(ip="100.10.10.10")

Notes:
open-iscsi 版本必须高于iscsiadm version 2.0-873.

"""
self._checkOpenIscsi()
commands = []
baseCmd = ["sh", "-c", "iscsiadm", "-m", "discovery", "-p", ip + ":3260", "-t", "st"]

newCmd = baseCmd[:]
newCmd.extend(["-o", "new"])
if chapUser is not None and chapPassword is not None:
enableChapCmd = baseCmd[:]
enableChapCmd.extend(["-o", "update", "--name=discovery.sendtargets.auth.authmethod",
"--value=CHAP"])
commands.append(enableChapCmd)

setUserCmd = baseCmd[:]
setUserCmd.extend(["-o", "update", "--name=discovery.sendtargets.auth.username",
"--value=%s" % chapUser])
commands.append(setUserCmd)

setUserPassword = baseCmd[:]
setUserPassword.extend(["-o", "update", "--name=discovery.sendtargets.auth.password",
"--value=%s" % chapPassword])
commands.append(setUserPassword)

discoverCmd = baseCmd[:]
# discoverCmd.append("--discover")
commands.append(discoverCmd)

for cmd in commands:
self.run({"command": cmd})

def sessionLogout(self, sessionId):
"""登出目标器链接

Args:
sessionId (str): 需要登出的session的ID.

Returns:
None.

Raises:
InvalidParamException: 输入的sessionID不存在.

Examples:
hostObj.sessionLogout("1")

"""
self._checkOpenIscsi()

sessions = self.getSessionMappings()

if sessionId not in sessions:
raise InvalidParamException("Session %s was not found." % sessionId)

portal = sessions[sessionId]["portal"]
target = sessions[sessionId]["target"]
self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node", "-u", "-T", target, "-p", portal + ":3260"]})

def getTargetPortals(self):
"""获取当前主机上的所有目标器入口门户数据

Args:
None.

Returns:
targetDict (dict): 目标器入口门户数据, 键值对说明如下：
: {
socket (str): target portal端口.
type (str): 取值范围为： 'sendtargets'、'isns'.
}

Raises:
None.

Examples:
targets = hostObj.getTargetPortals()
Output:
>{'128.181.100.107': {'socket': '3260', 'type': 'sendtargets'},
'128.94.255.10': {'socket': '3260', 'type': 'sendtargets'},
'128.94.255.12': {'socket': '3260', 'type': 'sendtargets'},
'129.181.100.107': {'socket': '3210', 'type': 'sendtargets'},
'129.94.10.10': {'socket': '3260', 'type': 'sendtargets'},
'129.94.10.11': {'socket': '3260', 'type': 'sendtargets'},
'129.94.255.10': {'socket': '3260', 'type': 'sendtargets'},
'129.94.255.12': {'socket': '3260', 'type': 'sendtargets'}}

"""
self._checkOpenIscsi()
cmd = ["sh", "-c", "iscsiadm", "-m", "discovery"]
response = self.run({"command": cmd})
# todo raise

targetDict = {}
if response["stdout"] is None:
return targetDict

lines = self.split(response["stdout"])
for line in lines:
targetMatch = re.match(r'^\s*(\S+):(\S+)\s+via\s+(\S+)', line)
if targetMatch:
targetDict[targetMatch.group(1)] = {"socket": targetMatch.group(2),
"type": targetMatch.group(3)}

return targetDict

def removeTargetPortal(self, ip, socket):
"""移除主机上的target Portal

Args:
ip (str): 目标器ip.
socket (str): 目标器端口.

Returns:
None.

Raises:
None.

Examples:
hostObj.removeTargetPortal("129.181.100.107", "3260")

Notes:
open-iscsi 版本必须高于iscsiadm version 2.0-873.

"""
self._checkOpenIscsi()
response = self.run({"command": ["sh", "-c", "iscsiadm", "-m", "discovery", "-p",
ip + ":" + socket, "-o", "delete", "-t", "st"]})

if response["rc"] != 0:
self.logger.debug("Remove target portal failed.")

def deletePartition(self, partition, async=0, umount=True):
"""删除磁盘分区

Args:
partition (str): 分区名称.
async (bool): 是否异步执行命令.
umount (bool): 是否umount目录，默认是

Attributes:
None.

Returns:
None.

Raises:
CommandException: 命令执行失败.

Examples:
hostObj.deletePartition("/dev/sdb1")

"""
if umount:
self.umount(partition)
tmpMatch = re.match(r'^(.+)(\d)', partition)
disk = tmpMatch.group(1)
volNum = tmpMatch.group(2)
if not async:
response = self.run({"command": ["sh", "-c", "parted", disk, "-s", "rm %s" % volNum]})
if response["rc"] != 0:
raise CommandException("Unable to delete partition # %s from disk %s" % (volNum, disk))
else:
return self.runAsync({"command": ["sh", "-c", "parted", disk, "-s", "rm %s" % volNum]})

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

Notes:
#原函数使用uniBlkIo去获取，若未安装uniBlkIo则会无法获取.

"""

response = self.run({"command": ["sh", "-c", "ls", "-l", "/dev/disk/by-id/"]})
if response["rc"] != 0 and not re.match(r'ls:\s+cannot\s+access\s+.*:\s+No\s+such\s+file\s+or\s+directory',
response["stderr"]):
raise CommandException(response["stderr"])

lines = self.split(response["stdout"])
if isinstance(lunComponent, list):
deviceList = []
for lun in lunComponent:
lunWwn = self.getLunWwn(lun)
device = None
for line in lines:
if re.search(r'' + str(lunWwn) + '', line) or re.search(r'' + str(lunWwn[16:]) + '', line):
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
# h90006090 2015/09/24 2800v3 Vm 命令回显的wwn为后16为字符, 判断语句中添加该场景.
if re.search(r'' + str(lunWwn) + '', line) or re.search(r'' + str(lunWwn[16:]) + '', line):
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

return None

def getAllDiskDevice(self):
"""upadmin show vlun all获取主机上所有的diskDevice Name
Return:
返回一个device字典，字典的key值为lun的wwn，value为盘符名称，形式如下
deviceList (dict): {'wwn':'/dev/sdxx'}
"""
response = self.run({"command": ["sh", "-c", "upadmin", "show", "vlun", "type=all"]})
if response["rc"] != 0 and not re.match(r'ls:\s+cannot\s+access\s+.*:\s+No\s+such\s+file\s+or\s+directory',
response["stderr"]):
raise CommandException(response["stderr"])
# 添加解析方法，解析response
lines = self.split(response["stdout"])
result = self.paseVlun(lines)
deviceList = {}
for vlun in result:
deviceList[result[vlun]["Lun WWN"]] = r"/dev/" + result[vlun]["Disk"]

return deviceList

def _getDiskDeviceNew(self, lunComponent):
"""获取指定Lun对象映射到主机的设备名称

Args:
lunComponent (instance | list): lun对象或者lun对象列表

Returns:
device (str|None): 映射的Lun对象的设备名称.

Raises:
CommandException: 命令执行失败.

Examples:
device = hostObj._getDiskDeviceNew(lun)
Output:
>"/dev/sdb"

Notes:
#原函数使用uniBlkIo去获取，若未安装uniBlkIo则会无法获取.

"""

response = self.run({"command": ["sh", "-c", "upadmin", "show", "vlun", "type=all"]})
if response["rc"] != 0 and not re.match(r'ls:\s+cannot\s+access\s+.*:\s+No\s+such\s+file\s+or\s+directory',
response["stderr"]):
raise CommandException(response["stderr"])
# 添加解析方法，解析response
lines = self.split(response["stdout"])
result = self.paseVlun(lines)
if isinstance(lunComponent, list):
deviceList = []
temp = []
for lun in lunComponent:
lunWwn = self.getLunWwn(lun)
device = None
for vlun in result:
if result[vlun]["Lun WWN"] == lunWwn or (("6.0." in lun.owningDevice.softVersion)
and result[vlun]["Dev Lun ID"] == lun.getProperty("id")):
device = "/dev/" + result[vlun]["Disk"]
deviceList.append(device)
if device == None:
raise CommandException("No device name was found for lun with [id: %s], [wwn: %s]" %
(lun.getProperty('id'), lunWwn))
return deviceList

else:
lunWwn = self.getLunWwn(lunComponent)
device = None
for vlun in result:
if result[vlun]["Lun WWN"] == lunWwn or (("6.0.0" in lunComponent.owningDevice.softVersion)
and result[vlun]["Dev Lun ID"] == lunComponent.getProperty(
"id")):
device = "/dev/" + result[vlun]["Disk"]
return device
if device == None:
raise CommandException("No device name was found for lun with [id: %s], [wwn: %s]" %
(lunComponent.getProperty('id'), lunWwn))

return None

def paseVlun(self, lines):
"""将命令回显转换的list解析为dict

Args:
lines (list): 回显字符转换后的list
Returns:
result (dict): 解析之后的业务属性字典.

Examples:

=================================================================================
1.横表解析
upadmin show vlun type=all

Vlun ID Disk name Lun WWn Status Capacity Ctrl(Own/Work)
------- ---------- --------- -------- ---------- --------- --------------

admin:/>

-解析后:
{
'0': {
'Vlun ID': '',
'Disk': '',
'name': '',
'Lun WWn': '',
'Status': '',
'Capacity': '',
'Ctrl(Own/Work)': '',
},
'1': {
'Vlun ID': '',
'Disk': '',
'name': '',
'Lun WWn': '',
'Status': '',
'Capacity': '',
'Ctrl(Own/Work)': '',
}
}
"""
result = {}
if len(lines) < 3:
return result
# 去除首尾的--
startLine = 0
endLine = -1
while not lines[startLine].startswith('------'):
startLine += 1
while not lines[endLine].startswith('------'):
endLine -= 1
startLine += 1
rawOutput = lines[startLine:endLine]
# 获取属性名作为key
keys = re.split('\\s{2,}', rawOutput[0])
# 对应key和value构造dic
for i in range(len(rawOutput)):
if i == 0:
continue
values = re.split('\\s{2,}', rawOutput[i].strip())
result[values[0]] = dict(zip(keys, values))
return result

def getLunWwn(self, lunComponent):
"""获取指定Lun Component对象的wwn

Args:
lunComponent (str): 需要获取wwn的Lun对象.

Returns:
None.

Raises:
None.

Examples:
lunWwn = hostObj.getLunWwn(lunObj)

"""
if isinstance(lunComponent, LunBase) or isinstance(lunComponent, SnapshotBase) \
or isinstance(lunComponent, Volume) or isinstance(lunComponent, RocSnapShotBase):
return lunComponent.getProperty("wwn")
raise InvalidParamException("%s is not a lun Component. " % lunComponent)

def createPartition(self, params):
"""
Args:
params (dict): 创建分区的参数, 键值对说明如下:
lun (instance): lun对象, 可选参数, lun和disk必须指定一个值.
disk (str): 磁盘名称, 可选参数, lun和disk必须指定一个值, 如: "/dev/sdb".
size (str): 需要创建的分区的大小, 可选参数.
mount (str): 分区创建后的挂载目录, 创建分区的同时格式化并挂载分区，不指定filesystem时默认格式化, 可选参数.
block_count (int): 创建文件系统的blocks个数, 指定block_count时必须指定filesystem值, 可选参数.
filesystem (str): 文件系统, 可选参数, 默认为None.
block_size (str): 为ext/ext2/ext3文件系统指定的块大小，提供的大小为: 1024 B, 2048 B, 4096 B ,
block_count指定时必须指定filesystem值, 可选参数.

Returns:
newVol (str): 创建的分区名称.

Raises:
InvalidParamException: 参数错误.
CommandException: 执行命令失败.

Examples:
hostObj.createPartition({"disk": "/dev/sdb", "size": "1GB", })
Output:
> "/dev/sdb1"

"""
if "lun" in params and params["lun"]:
params["disk"] = self._getDiskDevice(params["lun"])

if "disk" not in params or params["disk"] is None:
raise InvalidParamException("A LUN Object or a disk number must be provided.")

diskInfo = self.getDisk(params["disk"])
start, end = None, None
script = ""
usedVolNums = {}

if len(diskInfo["partitions"]) = 4:
raise CommandException("Failed to create a partition on %s "
"\nThere is no more free space on disk" % params["disk"])
for vol in partitions:
usedVolNums[vol["partition"]] = None

curStartSector, freeSpace = None, None
maxFreeSpace = "0MB"
lastEndSector = "0MB"
targetSize = "max"

if "size" in params and params["size"] and Units.isSize(params["size"]):
targetSize = Units.convert(params["size"], "MB")

partitions.append({"start": diskInfo["size"], "end": 1})

for vol in partitions:
curStartSector = vol["start"]
conCurStartSector = Units.convert(curStartSector, "MB")
conLastEndSector = Units.convert(lastEndSector, "MB")

freeSpace = Units.subtract(conLastEndSector, conCurStartSector)
if targetSize == "max":
tmpExp = Units.compareSize(freeSpace, maxFreeSpace)
if tmpExp > 0:
maxFreeSpace = freeSpace
start = lastEndSector
end = curStartSector
else:
tmpExp = Units.compareSize(freeSpace, targetSize)
if tmpExp >= 0:
start = lastEndSector
conLastEndSector = Units.convert(lastEndSector, MEGABYTE)
end = Units.add(conLastEndSector, targetSize)
break
lastEndSector = vol["end"]

if not start and not end:
raise InvalidParamException("Failed to create a partition on %s "
"\nThere is no more free space on disk" % params["disk"])
script += "mkpart primary %s %s p" % (start, end)
response = self.run({"command": ["sh", "-c", "parted", params["disk"], "-s", script]})
if response["rc"] != 0:
if re.search(r'Error: The location \d+ is outside of the device', response["stdout"]):
raise CommandException("Failed to create a partition on %s"
"\nThere is no more free space on disk" % params["disk"])
elif re.search(r'Error: Can\'t create any more partitions', response["stdout"]):
raise CommandException("Failed to create a partition on %s"
"\nCan't create any more partitions (4 is max)")
else:
raise CommandException("Failed to create a partition on %s" % params["disk"])

newPartition = self.getPartitions(disk=params["disk"])
newVol = None
for vol in newPartition:
if vol["partition"] not in usedVolNums:
newVol = vol["partition"]
break
if "filesystem" in params and params["filesystem"]:
partition = newVol
blockCount = None
blockSize = None
if "block_size" in params and params["block_size"]:
blockSize = params["block_size"]
if "block_count" in params and params["block_size"]:
blockCount = params["block_count"]
self.createFilesystem(partition=partition, filesystem=params["filesystem"],
blockSize=blockSize, blockCount=blockCount)
if "mount" in params and params["mount"]:
self.createFilesystem(partition=newVol)
self.createMount(device=newVol, mountPoint=params["mount"])

return newVol

def createFilesystem(self, partition=None, disk=None, filesystem=None,
blockCount=None, blockSize=None, async=False):
"""创建文件系统

Args:
partition (str): 主机中需要进行创建文件系统的分区; 可选参数, 默认为None; 如: "/dev/sdb1".
disk (str): 主机中需要进行创建文件系统的磁盘设备; 可选参数，默认为None; 如: "/dev/sdb".
filesystem (str): 创建文件系统使用的文件系统格式, 可选参数, 默认为None，创建文件系统为系统默认;
-参数范围为: ext2, ext3, ext4.
blockCount (str): 文件系统需要使用的blocks数量.
blockSize (str): 指定的block大小， 支持的大小为: 1024B, 2048B, 4096B, 需要设置filesystem时才生效, 默认为None.
async (bool): 是否异步后台执行, 可选参数，默认为False, 不指定. 取值为False、True.

Returns:
如果async参数为默认或指定为False返回None, 如果指定为True 返回 对象.

Raises:
InvalidParamException: 参数disk和partition都未指定时， blockSize不是Units类型时返回.

Examples:
hostObj.createFilesystem(partition="/dev/sdb1", async=False)

"""
cmd = []
createFsOnDisk = False
if disk:
partition = disk
createFsOnDisk = True
if partition is None:
raise InvalidParamException("Either partition or disk should be specified.")

if filesystem:
if blockSize and Units.isSize(blockSize):
blockSize = Units.getNumber(Units.convert(blockSize, BYTE))
cmd = ["sh", "-c", 'mkfs', '-t', filesystem, '-b', blockSize, partition]
elif not Units.isSize(blockSize):
raise InvalidParamException("blockSize is not correct: %s" % blockSize)
else:
cmd = ["sh", "-c", "mkfs", "-t", filesystem, partition]
else:
cmd = ["sh", "-c", "mkfs", partition]

if blockCount:
cmd.append(blockCount)
self.logger.debug("Formatting mount: %s" % partition)

if async:
if createFsOnDisk:
return self.runAsync({"command": cmd, "input": ["y\n", "#"], "waitstr": "Proceed anyway\? \(y\,n\)"})
else:
return self.runAsync({"command": cmd})
else:
if createFsOnDisk:
self.run({"command": cmd, "input": ["y\n", "#"], "waitstr": "Proceed anyway\? \(y\,n\)"})
else:
self.run({"command": cmd})
return

def getProcessList(self):
"""获取主机所有进程的信息

Args:
None.

Returns:
processInfo (dict): 进程信息字典, 键值对说面如下:
pid (str): 进程ID.
ppid (str): 父进程ID.
name (str): 进程名称.
priority (str): 进程优先级.
commandline (str): 进程的CMD和参数.

Raises:
None.

Examples:
hosts.getProcessList()
Output:
>{'1': {'cmdline': 'init [5]',
'name': 'init',
'pid': '1',
'ppid': '0',
'priority': '0'},
'10': {'cmdline': '[ksoftirqd/3]',
'name': 'ksoftirqd/3',
'pid': '10',
'ppid': '2',
'priority': '0'},...}

"""
response = self.run({"command": ["sh", "-c", "ps", "-Awwo", "nice,pid,ppid,comm,args"]})
processInfo = {}

for line in self.split(response["stdout"]):
pidMatch = re.match(r'^\s*(\-?\d*)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+?)\s*$', line)
if pidMatch:
processInfo[pidMatch.group(2)] = {"priority": pidMatch.group(1),
"pid": pidMatch.group(2),
"ppid": pidMatch.group(3),
"name": pidMatch.group(4),
"cmdline": pidMatch.group(5)}
return processInfo

def getProcessInfoByName(self, pName):
"""获取主机与指定名称相似的所有进程的信息

Args:
pName (str): 进行匹配的进程名称.

Returns:
processInfo (dict): 进程信息字典, 键值对说面如下:
pid (str): 进程ID.
ppid (str): 父进程ID.
name (str): 进程名称.
priority (str): 进程优先级.
commandline (str): 进程的CMD和参数.

Raises:
None.

Examples:
hosts.getProcessList()
Output:
>{'1': {'cmdline': 'init [5]',
'name': 'init',
'pid': '1',
'ppid': '0',
'priority': '0'},
'10': {'cmdline': '[ksoftirqd/3]',
'name': 'ksoftirqd/3',
'pid': '10',
'ppid': '2',
'priority': '0'},...}

"""
response = self.run({"command": ["sh", "-c", "ps", "-Awwo", "nice,pid,ppid,comm,args|grep %s" % pName]})
processInfo = {}

for line in self.split(response["stdout"]):
pidMatch = re.match(r'^\s*(\-?\d*)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+?)\s*$', line)
if pidMatch:
processInfo[pidMatch.group(2)] = {"priority": pidMatch.group(1),
"pid": pidMatch.group(2),
"ppid": pidMatch.group(3),
"name": pidMatch.group(4),
"cmdline": pidMatch.group(5)}
return processInfo

def checkMd5Checksum(self, path, checksum):
"""检查文件的md5值是否正确

Args:
path (str): 需要进行校验的文件路径.
checksum (str): 需要进行比较的md5值.

Returns:
None.

Raises:
CommandException: 命令执行失败，或者md5值与输入的不同时.

Examples:
hostObj.checkMd5Checksum("/etc/resolv.conf", "e00880a1a5caba6f5d2473b1fe2c0260")

"""
if not self.doesPathExist(path):
raise CommandException("%s was not found in." % path)

response = self.run({"command": ["sh", "-c", "md5sum", path]})
if response["rc"] != 0:
raise CommandException("Calculated checksum Failed.")

# lines = self.split(response)
lines = self.split(response["stdout"])
for line in lines:
if re.match(r'^md5sum', line):
continue
tmpMatch = re.match(r'^\w+', line)
if tmpMatch and tmpMatch.group() == checksum:
return
elif tmpMatch and tmpMatch.group() != checksum:
raise CommandException("Checksum do not match! Expected: %s; Calculated: %s"
% (checksum, tmpMatch.group()))

def getMd5Checksum(self, path):
"""获取指定文件的md5值

Args:
path (str): 需要获取md5的文件路径.

Returns:
md5sum (str): 指定文件的md5值.

Raises:
None.

Examples:
md5sum = hostObj.getMd5Checksum("/etc/resolv.conf")
Output:
>"e00880a1a5caba6f5d2473b1fe2c0260"

"""
if self.doesPathExist({"path": path}):
response = self.run({"command": ["sh", "-c", "md5sum", path]})
lines = self.split(response["stdout"])
for line in lines:
if re.match(r'^md5sum', line):
continue
tmpMatch = re.match(r'^(\w+)(\s+)' + str(path) + '', line)
if tmpMatch:
return tmpMatch.group(1)
else:
raise InvalidParamException("%s was not found in." % path)

def getNetworkInfo(self):
"""获取主机的网络信息

Args:
None.

Returns:
networkInfo (dict): 当前主机的网络信息, 键值对说明如下：
{
'hostname' (str): 主机名称.
'dns_domain' (str): dns名称.
'gateway' (str): 网关名称.
'interface' (str): {
: {
'netmask' (str): 子网掩码.
'ipv4_address (str): ipv4地址.
'ipv6_address' (str): ipv6地址.
},
...
},
...
}

Raises:
None.

Examples:
hostObj.getNetworkInfo()
Output:
>{'gateway': '100.94.0.1',
'hostname': 'linux',
'interface': {'eth4': {'ipv4_address': '100.94.11.11',
'ipv6_address': 'fe80::222:a1ff:fe0d:22d6/64',
'netmask': '255.255.0.0'},
'eth5': {'ipv4_address': '129.94.11.11',
'ipv6_address': 'fe80::222:a1ff:fe0d:22d7/64',
'netmask': '255.255.0.0'},
'lo': {'ipv4_address': '127.0.0.1',
'ipv6_address': '::1/128',
'netmask': '255.0.0.0'}}}

"""

if self.networkInfo:
return self.networkInfo

networkInfo = {}
# 获取主机名.
responseName = self.run({"command": ["sh", "-c", "uname", "-n"]})
lines = self.split(responseName["stdout"])

for line in lines:
if re.match(r'^uname -n', line):
continue
tmpMatch = re.match(r'^\S+$', line)
if tmpMatch:
networkInfo["hostname"] = tmpMatch.group()
break

# 获取网络信息
responseNet = self.run({"command": ["sh", "-c", "ifconfig"]})
currentInterface = None
networkInfo["interface"] = {}

for line in self.split(responseNet["stdout"]):

currentNetMatch = re.match(r'^(\S+)\s+Link\s+encap', line) # 匹配suse interface名称.
currentNetMatchRedHat = re.match(r'^(\S+):\s+flags=', line) # 匹配redhat interface名称.

if currentNetMatch:
currentInterface = currentNetMatch.group(1)
networkInfo["interface"][currentInterface] = {}
continue
elif currentNetMatchRedHat:
currentInterface = currentNetMatchRedHat.group(1)
networkInfo["interface"][currentInterface] = {}
continue

ipv4Match = re.search(r'inet\s+addr:\s*(\S+)\s+', line) # 匹配suse ipv4.
ipv4MatchRedHat = re.search(r'inet\s+(\S+)\s+', line) # 匹配redhat ipv4.

if ipv4Match and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["ipv4_address"] = ipv4Match.group(1)
netmaskMatch = re.search(r'Mask:\s*(\S+)\s*$', line) # 匹配suse mask.
if netmaskMatch and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["netmask"] = netmaskMatch.group(1)
continue
elif ipv4MatchRedHat and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["ipv4_address"] = ipv4MatchRedHat.group(1)
netmaskMatch = re.search(r'netmask\s+(\S+)\s+broadcast', line) # 匹配redhat mask.
if netmaskMatch and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["netmask"] = netmaskMatch.group(1)
continue

ipv6Match = re.search(r'inet6 addr:\s*(\S+)\s+Scope:Global$', line) # 匹配suse ipv6.
ipv6MatchRedHat = re.search(r'inet6\s+(\S+)\s+prefixlen\s+(\d+)', line) # 匹配redhat ipv6.
if ipv6Match and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["ipv6_address"] = ipv6Match.group(1)
elif ipv6MatchRedHat and currentInterface in networkInfo["interface"]:
networkInfo["interface"][currentInterface]["ipv6_address"] = ipv6MatchRedHat.group(1)

responseGateway = self.run({"command": ["sh", "-c", "netstat", "-rn"]})

for line in self.split(responseGateway["stdout"]):
gatewayMatch = re.match(r'^0\.0\.0\.0\s+(\S+)', line)
if gatewayMatch:
networkInfo["gateway"] = gatewayMatch.group(1)

networkInfo['dns_domain'] = self.getDomainInfo()

return networkInfo

def activateNetworkInterface(self, interface):
"""激活网卡

该操作需要root权限.

Args:
interface (str): 网卡名称.

Returns:
None.

Raises:
CommandException: 命令执行失败.

Examples:
hostObj.activateNetworkInterface("eth2")

"""
response = self.run({"command": ["sh", "-c", "/sbin/ifup", interface]})
if response["rc"] != 0:
raise CommandException("Activate Interface: %s Failed, Error:\n %s"
% (interface, response["stderr"]))

def getBondingNetworkInterfaceInfo(self, interface):
"""获取指定bond口的成员口信息

该操作需要root权限.

Args:
interface (str): 网卡名称.

Returns:
{
"active_menber":"xx",
"menbers":[xx,xx]
}

Examples:
hostObj.getBondingNetworkInterfaceInfo("bond1")
"""
ret = {}
response = self.run({"command": ["sh", "-c", "cat /proc/net/bonding/{name}".format(name=interface)]})

# 先找bond模式
bond_mode_match = re.search(r'Bonding Mode:\s*([\w|-]+)', response['stdout'])
if bond_mode_match:
bond_mode = bond_mode_match.group(1)
bond_mode = 'AP' if 'fault-tolerance' in bond_mode else 'AA'
ret['bond_mode'] = bond_mode
# 再找成员口
currentNetMatch = re.search(r'Currently Active Slave:\s*(\w+)\r+', response['stdout'])
if currentNetMatch:
ret['active_menber'] = currentNetMatch.group(1)
slaves = re.findall(r'Slave Interface:\s*(\w+)\r', response['stdout'])
ret['menbers'] = slaves
return ret

def deactivateNetworkInterface(self, interface):
"""取消激活网卡

该操作需要root权限.

Args:
interface (str): 网卡名称.

Returns:
None.

Raises:
CommandException: 命令执行失败.

Examples:
hostObj.deactivateNetworkInterface("eth2")

"""
response = self.run({"command": ["sh", "-c", "/sbin/ifdown", interface]})
if response["rc"] != 0:
raise CommandException("Deactivate Interface: %s Failed, Error:\n %s"
% (interface, response["stderr"]))

def setDnsServer(self, dnsServer):
"""本主机设置DNS server

Args:
dnsServer (str): 需要设置的Dns Server.

Returns:
None.

Raises:
None.

Examples:
hostObj.setDnsServer("100.10.10.10")

"""

hasDns = False
response = self.run({"command": ["sh", "-c", "grep", dnsServer, "/etc/resolv.conf"]})
for line in self.split(response["stdout"]):
if re.match(r'^grep ' + str(dnsServer) + '', line):
continue
elif re.search(r'' + str(dnsServer) + '', line):
hasDns = True
else:
continue

if not hasDns:
self.logger.debug("Adding DNS server %s to host " % (dnsServer, self.getIpAddress()))
self.run({"command": ["echo 'nameserver %s' >> " % dnsServer, "/etc/resolv.conf"]})
return
else:
self.logger.debug("DNS server %s already configured on host " % (dnsServer, self.getIpAddress()))
return

def getProcessInfo(self, pid):
"""获取指定进程ID的进程信息

Args:
pid (str): 进程ID

Returns:
processInfo (dict): 指定pid的进程信息, 键值对说面如下:
pid (str): 进程ID.
ppid (str): 父进程ID.
name (str): 进程名称.
priority (str): 进程优先级.
commandline (str): 进程的CMD和参数.

Raises:
CommandException: 命令执行失败.

Examples:
hostObj.getProcessInfo("5768")
Output:
>{'cmdline': '[ksoftirqd/3]',
'name': 'ksoftirqd/3',
'pid': '10',
'ppid': '2',
'priority': '0'}

"""
response = self.run({"command": ["sh", "-c", "ps", "-p", pid, "-wwo", "nice,pid,ppid,comm,args"]})
if response["rc"] != 0:
raise CommandException("Unable to find proc with id: %s" % pid)

for line in self.split(response["stdout"]):
pidMatch = re.match(r'^\s*(\-?\d*)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+?)\s*$', line)
if pidMatch:
return {"priority": pidMatch.group(1),
"pid": pidMatch.group(2),
"ppid": pidMatch.group(3),
"name": pidMatch.group(4),
"cmdline": pidMatch.group(5)}

def getIpAddress(self, interface=None, ipType=None):
"""主机的IP地址

Args:
interface (str): 网络设备名称, 如: "eth0".
ipType (str): IP地址类型, 取值范围为: "ipv4", "ipv6".

Returns:
ipAddress (str): 主机的ip地址.

Raises:
InvalidParamException: 输入的ip地址类型错误或对应地址类型的ip地址不存在时抛出异常.

Examples:
None.

"""
if ipType:
addressType = ipType + "_address"
else:
addressType = "ipv4_address"

# 默认返回测试床中配置的IP
if interface is None and ipType is None:
if self.localIP:
return self.localIP
netInfo = self.getNetworkInfo()

# 未指定ip但时指定了ipType时默认返回第一个Ip
if not interface and ipType:
ipAddress = ()
for inet in sorted(netInfo["interface"]):
if isinstance(netInfo["interface"][inet], dict):
if addressType in netInfo["interface"][inet]:
return netInfo["interface"][inet][addressType]

if interface not in netInfo["interface"]:
raise InvalidParamException("Interface %s does not exist on this host" % interface)

if addressType not in netInfo["interface"][interface]:
raise InvalidParamException("Interface %s does not have an "
"IP Address or the interface is down." % interface)
return netInfo["interface"][interface][addressType]

def rescanIscsiTargets(self):
"""重新扫描主机上的Target, 更新主机的Target列表

Examples:
hostObj.rescanIscsiTargets()

"""
self._checkOpenIscsi()
self.run({"command": ["sh", "-c", "iscsiadm", "-m", "session", "-R"]})
return

def initializeDisk(self, lunComponent=None, disk=None, mount=None, filesystem=None,
blockSize=None, blockCount=None):
"""对指定的已映射的磁盘或Lun对象进行初始化
#初始化包含将整个磁盘或Lun对象创建为一个分区, 并格式化为指定的文件系统, 挂载到指定的mount点或指定的驱动器号.

Args:
lunComponent (instance): 需要进行初始化的Lun的Component对象，可选参数，默认: None,
-lunComponent和disk必须指定一个值.
disk (str): 需要进行初始化的磁盘名称, 如: "/dev/sdb", 可选参数, 默认: None.
mount (str): 初始化后磁盘的挂载点, 可选参数，默认: None.
filesystem (str): 磁盘创建的文件系统, 取值范围为: (ext2,ext3,ext4), 默认: ext3.
blockSize (str): UniAuto Size 单位类型, 指定filesystem的block size, 取值范围为: 1024B, 2048B, 4096B.
blockCount (str): UniAuto Size 单位类型, 指定filesystem使用的blocks数量, 可选参数，默认为None.

Returns:
None.

Raises:
None.

Examples:
hostObj.initializeDisk(disk="/dev/sdb", filesystem="etx4", mount="/mnt/1")

"""

partition = self.createPartition({"disk": disk, "lun": lunComponent})

if mount is None:
mount = self._createRandomDirectory("/mnt", "uniAutoMnt_%d%d%d%d%d%d%d")

self.createFilesystem(partition=partition, filesystem=filesystem,
blockCount=blockCount, blockSize=blockSize)

self.createMount(device=partition, mountPoint=mount)

self.logger.debug("Initialized device %s and mounted it to %s" % (partition, mount))

return mount

def mountNfsFilesystem(self, export, mountPoint=None, acl=None, retryType=None, interrupt=None,
timeout=None, nfsVersion=None, minorVersion=None, port=None, readSize=None,
writeSize=None, securityMode=None, protocol=None, sync=None, persist=None):
"""在linux操作系统上支持NFS文件系统的挂载功能

Args:
export (str) : The exported filesystem or 'share'. e.g., '10.1.1.5:/localPath'.

mountPoint (Str) : (可选参数)Destination mountpoint to use on this host.By default one
is chosen for you and placed in /mnt directory. If mountpoint does not
exist it will be created for you automatically.

acl (bool) : (可选参数)(Default = System will attempt to auto detect), Selects
whether to use the NFSACL sideband protocol on this mount point. The NFSACL
sideband protocol is a proprietary protocol implemented in Solaris that manages
Access Control Lists. NFSACL was never made a standard
part of the NFS protocol specification.

retryType (str) : (可选参数)hard|soft, Specifies whether the program using a file via an NFS
connection should stop and wait (hard) for the server to come back online,
if the host serving the exported file system is unavailable, or if it should
report an error (soft).

interrupt (bool) : (可选参数)if type is hard. Allows NFS requests to be interrupted 、
if the server goes down or cannot be reached.

timeout (str) : (可选参数)UniAutos Time Unit.Specifies the time to pass before the error is reported.

nfsVersion (str) : (可选参数) 可选值: 2|3|4. Specifies which version of the NFS protocol to use.
This is useful for hosts that run multiple NFS servers. If no version
is specified, NFS uses the highest supported version by the kernel and
mount command.

minorVersion (int) : (可选参数)Specifies the protocol minor version number.NFSv4 introduces
"minor versioning," where NFS protocol enhancements can be introduced without
bumping the NFS protocol version number.

port (int) : (可选参数)Specifies the numeric value of the NFS server port.
If num is 0 (the default), then mount queries the remote host's portmapper
for the port number to use. If the remote host's NFS daemon is not registered
with its portmapper, the standard NFS port number of TCP 2049 is used instead.

readSize (str) : (可选参数)The maximum number of bytes in each network READ request
that the NFS client can receive when reading data from a
file on an NFS server. The actual data payload size of
each NFS READ request is equal to or smaller than the
read_size setting. The largest read payload supported by the
Linux NFS client is 1,048,576 bytes (one megabyte).
The read_size value is a positive integral multiple of 1024.
Specified read_size values lower than 1024 are replaced with
4096; values larger than 1048576 are replaced with
1048576. If a specified value is within the supported
range but not a multiple of 1024, it is rounded down to
the nearest multiple of 1024.
*Format is 1024 B, or 4096 B*

writeSize (str) : (可选参数)参考readSize

securityMode (str) : (可选参数)Specifies the type of security to utilize when
authenticating an NFS connection. Security types are
sys|krb5|krb5i|krb5p
(Not supported by all linux distros)

protocol (str) : (可选参数)tcp|udp

sync (bool) : (可选参数)if specified then all IO will try to be done synchronously.

persist (bool) : (可选参数)if specified then the mount will be persisted through reboots.

Returns:
mountPoint

Raises:
None.

Examples:
mp = linuxHost.mountNfsFilesystem('10.1.1.5:/share', nfsVersion='3', protocol='tcp', retryType='hadr' ...)
#将会生产以下命令 mount -t nfs 10.1.1.5:/share /tmp/tmp2 -o opt1 -o opt2=xyz -o etc

"""

cmds = ['mount', '-t']

# The option 'nfsvers' is not supported for nfs4
if nfsVersion and nfsVersion == '4':
cmds.append('nfs4')
else:
cmds.append('nfs')

cmds.append(export)

if not mountPoint:
mountPoint = self._createRandomDirectory('/mnt', 'uniAutos_%d%d%d%d%d%d%d%d')

if not self.doesPathExist({'path': mountPoint}):
self.createDirectory(mountPoint)

cmds.append(mountPoint)

options = []
if sync:
options.append('sync')

if retryType:
options.append(retryType)

if interrupt:
options.append('intr')

if timeout:
# This timeout value is in tenths of a second
timeout = str(Units.getNumber(Units.convert(timeout, SECOND)) * 10)
# 修改大规格小数点后为0取整的情况
decimalZeroFlag = re.match('(\d+)\.0', timeout)
if decimalZeroFlag:
timeout = decimalZeroFlag.groups()[0]
options.append('timeo=' + timeout)

if nfsVersion:
options.append('nfsvers=' + nfsVersion)

if minorVersion:
options.append('minorversion=' + str(minorVersion))

if port:
options.append('port=' + str(port))

if acl:
options.append('acl')
elif acl and not acl:
options.append('noacl')

if readSize:
readSize = str(Units.getNumber(Units.convert(readSize, BYTE)))
decimalZeroFlag = re.match('(\d+)\.0', readSize)
if decimalZeroFlag:
readSize = decimalZeroFlag.groups()[0]
options.append('rsize=' + readSize)

if writeSize:
writeSize = str(Units.getNumber(Units.convert(writeSize, BYTE)))
decimalZeroFlag = re.match('(\d+)\.0', writeSize)
if decimalZeroFlag:
writeSize = decimalZeroFlag.groups()[0]
options.append('wsize=' + writeSize)

if securityMode:
options.append('sec=' + securityMode)

if protocol:
options.append('proto=' + protocol)

if len(options) > 0:
cmds.append('-o')
cmds.append(','.join(options))
cmds.insert(0, '-c')
cmds.insert(0, 'sh')
self.run({'command': cmds, 'checkrc': 1})

if persist:
if len(options) > 0:
fstab = export + " " + mountPoint + " " + ','.join(options) + " 0 0"
else:
fstab = export + " " + mountPoint + " " + " 0 0"

cmds = ['sh', '-c', 'grep', export, '/etx/fstab']

result = self.run({'command': cmds})

if result['stdout']:
export.replace('\/', '\\\/')
export.replace('\.', '\\\.')
cmds = ['sh', '-c', 'sed', '-i', '/' + export + '.*/d', '/etx/fstab']
result = self.run({'command': cmds})

self.run({'command': ['sh', '-c', 'echo \"' + fstab + '\" >> /etc/fstab']})
return mountPoint

def unmountNfsFilesystem(self, mountPoint):
"""在linux操作系统上支持NFS文件系统的卸载功能

Args:
mountpoint (Str) : (可选参数)unmount the mountpoint

Returns:
mountPoint

Raises:
None.

Examples:
mp = linuxHost.mountNfsFilesystem('10.1.1.5:/share', nfsVersion='3', protocol='tcp', retryType='hadr' ...)
#将会生产以下命令 mount -t nfs 10.1.1.5:/share /tmp/tmp2 -o opt1 -o opt2=xyz -o etc

"""
self.umount(mountPoint)

def showNfsMount(self, nfsServerIP):
"""In the Linux operating system to support show mount information for an NFS server

Args:
nfsServerIP (Str) : NFS server ip or ip of storage engine

Returns:
remote NFS Server mountPoint information

Raises:
None.

Examples:
mps = linuxHost.showNfsMount('10.1.1.5')

"""
result = []
mountInfo = self.run({'command': ['sh', '-c', 'showmount', '--no-headers', '-e', nfsServerIP]})['stdout']

if mountInfo:
for line in re.split('\r|\n', mountInfo):
if re.search(r'^root*', line):
continue
elif line == '':
continue
else:
entry = line.split(' ')
result.append(entry[0])

return result

def getMountDir(self, fileSystemNameList):
"""在linux操作系统上获取文件系统挂载路径

Args:
fileSystemNameList (list) : (必选参数)文件系统名称list

Returns:
mountDir (list) : 挂载路径List

Raises:
None.

Examples:
mountDirList = linuxHost.getMountDir(['filename1', 'filename2'])

"""
result = []
mountDir = None
mountInfo = self.run({'command': ['sh', '-c', 'cat /proc/mounts']})['stdout']

if mountInfo:
mountInfo = mountInfo.split('\n')
else:
return result

for fileSystemName in fileSystemNameList:
for line in mountInfo:
matcher = re.search(fileSystemName, line)
snapshot = re.search('\.snapshot', line)
if matcher and not snapshot:
match = re.search('((\d+\.){3}\d+):(\S+)\s+(\S+)\s+\S+', line)
mountDir = match.groups()[3]

result.append(mountDir)
mountDir = None
return result

def getDomainInfo(self):
"""获取主机的DNS信息.

Args:
None.

Returns:
domain (str|None): 当前主机的dns信息.

Raises:
None.

Examples:
None.
"""
domain = None
response = self.run({'command': ['sh', '-c', 'dnsdomainname']})
if response['rc']:
return super(Linux, self).getDomainInfo()
if response['stdout']:
lines = self.split(response['stdout'])
for line in lines:
line = self.trim(line)
if re.search(r'sh -c dnsdomainname', line):
continue
elif line == '':
continue
else:
domain = line
return domain

def sendSerial(self, mode, user, pwd, *args, **kwargs):
"""通过串口发送命令,host上需要安装pyserial，目前手动安装；

Args:
mode (str):阵列的模式（目前仅支持PANGEA_SES/SUPER_ADMIN/IBMC(需下电)/PCIE_DSW/ADMIN_CLI）
user (str): 登录user
pwd (str): 登录pwd
cmd (str): 发送命令

Returns:
stdout，命令原始回显，需解析

Examples:
1、通过串口连接到PANGEA_SES模式，下发命令menu
ret= host.sendSerial("PANGEA_SES","admin","Admin@storage1","menu")

2、通过串口连接到IBMC模式，下发命令ls --color=never (取消颜色显示，否则回显会带颜色转义符)
ret= host.sendSerial("IBMC","administrator","Huawei12#$",'ls --color=never')

3、一次发送多条命令
ret= host.sendSerial("PCIE_DSW","_super_admin","Admin@dsw0", "help", "test", "menu")

4、测试超时时间，发送命令后，等待waitTime（s）后再获取回显；
ret= host.sendSerial("ADMIN_CLI","admin","Admin@storage1",'change safe_strategy session_expired_time=1',waitTime='70')

"""
waitTime = '0'
if 'waitTime' in kwargs:
waitTime = kwargs['waitTime']
# copy file :runSerial.py
tmp = os.path.split(os.path.realpath(__file__))[0]
src_file = os.path.join(tmp.split('Device')[0], 'Util\\runSerial.py')
self.putFile(
{'source_file': src_file,
'destination_file': "/home/runSerial.py"}
)

params = {}
cmds = ""
for cmd in args:
cmds = cmds + '\"' + cmd + '\"' + ' '

# 串口登陆Dorado 3U IBMC 时需要传入控制器的ID， 小写字母, 默认情况下不需要传入.
ctrl = kwargs.get('ctrl')
if ctrl is None:
params['command'] = ["sh", "-c", "python runSerial.py", mode, user, pwd, waitTime, cmds]
else:
params['command'] = ["sh", "-c", "python runSerial.py", mode, user, pwd, waitTime, ctrl, cmds]
params["directory"] = "/home"
response = self.run(params)
if response['stdout'] == None:
raise CommandException(response['stderr'])
return response['stdout']

def wipe(self, timeout=600):
"""清除Linux上的所有业务

Examples:
host.wipe()

"""
matcher = None
row_timeout, raw_stop_on_timeout = self.getTimeout, self.getStopOnTimeout
self.setTimeout(timeout, False)
# Stop SDTester
sdTester = self.run({'command': ['sh', '-c', 'ps', '-aux', '|', 'grep', 'sdtester']})
for line in re.split('\r|\n', sdTester['stdout']):
matcher = re.search('root\s+(\d+).*/sdtester', line)
if matcher:
self.run({'command': ['sh', '-c', 'kill', '-9', matcher.groups()[0]]})

# Stop VDBench
vdBench = self.run({'command': ['sh', '-c', 'ps', '-ef', '|', 'grep', 'java']})
for line in re.split('\r|\n', vdBench['stdout']):
matcher = re.search('.*?(\d+).*vdbench', line)
if matcher:
self.run({'command': ['sh', '-c', 'kill', '-9', matcher.groups()[0]]})

# Unmount filesystem
mount = self.run({'command': ['sh', '-c', 'mount']})
for line in re.split('\r|\n', mount['stdout']):
matcher = re.search('\d+\.\d+\:.*\s+(\S+)\s+type\s+nfs', line)
if matcher:
self.run({'command': ['sh', '-c', 'umount', '-l', matcher.groups()[0]]})
self.run({'command': ['sh', '-c', 'rm', '-rf', matcher.groups()[0]]})

self.setTimeout(row_timeout, raw_stop_on_timeout)

# Remove and recreate image file directory

# Remove file sharing directory

# NFS Service

# Clear multipath fault counter

def pingAddress(self, ipAddress):
"""Ping the special ip address

Changes:
2016/7/28 d00225755 Created
2018/04/25 wwx271515 适配回显存在network is unreachable也表示网络不通

"""
response = self.run({"command": ["sh", "-c", "ping", ipAddress, "-c", "1", "-W", "30"]})
if re.search(r'100% packet loss|network is unreachable', str(response.get('stdout', '')).lower()) or \
re.search(r'100% packet loss|network is unreachable', str(response.get('stderr', '')).lower()):
return False
else:
return True

def rescanInitiator(self, ipv4Address=None):
"""iscsiadm -m node -l，扫描已经有的启动器

Args:
ipv4Address (str): ipv4地址

Raises:
CommandException: 命令执行失败.
"""
self._checkOpenIscsi()
if ipv4Address:
self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node", "-l", '-p', ipv4Address]})
else:
self.run({"command": ["sh", "-c", "iscsiadm", "-m", "node", "-l"]})

def upadminSetLuntrespass(self, switch, arrayId=None, vlunId=None):
"""设置主机多路径切换开关
Args:
switch (str): 取值范围on|off, on为开启lun的工作控制器切换.
arrayId (str): 阵列ID.
vlunId (str): 虚拟LUN的ID, 取值为{ ID | ID1,ID2... | ID1-ID2 }.
Return:
True|False 设置成功还是失败.
"""
command = ["sh", "-c", "upadmin", "set", "luntrespass=%s" % switch]
cmd_spec = {"command": command}
# 如果需要设置array_id时，命令行时交互式的.
if arrayId:
command.append('array_id=%s' % arrayId)
cmd_spec.update(
{'waitstr': '[y,n]',
'input': ['y', "[>#]"]})
elif vlunId:
command.append('vlun_id=%s' % vlunId)

result = self.run(cmd_spec)
if result['rc'] != 0:
return False
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
return True
return False

def closeLuntrespass(self, storageDevice=None, vlunId=None):
"""关闭主机多路径切换开关
Args:
switch (str): 取值范围on|off, on为开启lun的工作控制器切换.
storageDevice (Unified): 同一存储阵列对象.
vlunId (str): 虚拟LUN的ID, 取值为{ ID | ID1,ID2... | ID1-ID2 }.
Return:
True|False 设置成功还是失败.
"""
arrayInfoList = self.upadminShowArrary()
arrayId = None
for arrayInfo in arrayInfoList:
if arrayInfo["array_sn"] == storageDevice.SN:
arrayId = arrayInfo["array_id"]
if arrayId is None:
raise CommandException("Unable to find any array id for storage sn:%s." % storageDevice.SN)

def faultClosure(params):
if not self.upadminSetLuntrespass('off', arrayId, vlunId):
raise UniAutosException('主机[%s]的多路径开关切换失败' % self.localIP)

def cleanupFaultClosure(params):
if not self.upadminSetLuntrespass('on', arrayId, vlunId):
raise UniAutosException('主机[%s]的多路径开关切换失败' % self.localIP)

fault = Fault(storageDevice, "closeLuntrespass", faultClosure,
obj=None, parameters={}, cleanupClosure=cleanupFaultClosure)
fault.inject(count=1)

return fault

def setUpadminHyperMetroWorkingmode(self, workingmode=None, storageDevice=None):
"""设置主机多路径双活工作模式
Args:
workingmode (str) : 取值范围priority|balance,：
"priority" read write within primary array.
"balance" read write between both arrays.
storageDevice (Unified): 统一存储阵列对象.
Return:
True|False 设置成功还是失败.
"""
arrayInfoList = self.upadminShowArrary()
arrayId = None
for arrayInfo in arrayInfoList:
if arrayInfo["array_sn"] == storageDevice.SN:
arrayId = arrayInfo["array_id"]
if arrayId is None:
raise CommandException("Unable to find any array id for storage sn:%s." % storageDevice.SN)

command = ["sh", "-c", "upadmin", "set", "hypermetro", "workingmode=%s" % workingmode,
"primary_array_id=%s" % arrayId]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if result['rc'] != 0:
return False
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
return True
else:
return False

def setUpadminHyperMetroSplitSize(self, splitSize=None):
"""设置主机多路径双活切片大小
Args:
splitSize (str) : size is in the range 512B-1G,unit can be B,K,M,G.
size must be power of 2.
Default is 128M
Return:
True|False 设置成功还是失败.
"""
command = ["sh", "-c", "upadmin", "set", "hypermetro", "split_size=%s" % splitSize]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if result['rc'] != 0:
return False
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
return True
else:
return False

def tcCommand(self, cmd, eth, type, param):
"""
linux host上执行 tc qdisc 命令

Args:
cmd (str): 注入错误的命令，如 'add','change'
eth (str): eth port名字
type (str): 命令的类型字段，如 'delay', 'loss', 'duplicate'
param (str): 命令最后的参数，接着参数type之后的命令，如 '100ms', '100ms 10ms 30%', '1% 30%'

Returns:
response (dict): 命令返回内容

Raises:
None

Examples:
host.tcCommand(cmd, eth, type, param)

"""
fcmd = 'sh -c tc qdisc %s dev %s root netem %s %s' % (str(cmd), str(eth), str(type), str(param))
fcmd = fcmd.split()
response = self.run({"command": fcmd})
return response

def ethUpDown(self, eth, type):
"""
以太网卡连接down或者up

Args:
eth (str): eth0, eth1
type (str): down 或 up

Returns:
result (dict): 命令返回结果

Example:
host.ethUpDown('eth1', 'up')

"""
command = ["sh", "-c", "ifconfig %s %s" % (eth, type)]
result = self.run({"command": command})
return result

def reboot(self, delay=5, wait=False, timeout='30M', mountPath=None):
"""
重启linux host

Return:
True|False: 成功还是失败
"""
timeoutNum = int(Units.getNumber(Units.convert('30M', 'S')))
self.logger.info('host[%s] is rebooting' % self.localIP)
command = ["sh", "-c", "reboot"]
result = self.run({"command": command})
sleep(delay)
if wait:
self.waitForReboot(timeout=timeoutNum)
if result['rc'] != 0:
return False
return True

def compareData(self, srcobj, dstobj, srcoffset=None, dstoffset=None, srclength=None, dstlength=None,
specified_start_zone=None, specified_range_size=None, parallel=False):
"""
对两个文件进行数据比较,数据不一致会保留当前环境，以便定位

Args:
src (obj/str): 比较源数据对象，lun或者snapshot对象或者文件系统路径
dst (obj/str): 比较目标数据对象，lun或者snapshot对像或者文件系统路径
srcoffset (str): 源LUN偏移量 与 dstoffset，否则无效
dstoffset (str): 目标LUN偏移量 与 srcoffset，否则无效
srclength (str): 源LUN偏长度
dstlength (str): 目标LUN偏长度
specified_start_zone (str): 指定区域比较开始比较点 "102400G:102400G"
specified_range_size (str): 指定比较区域大小
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
if parallel:
threads = []
errors = []
for src, dst in zip(srcobj, dstobj):
th = Threads(self.compareData, threadName="Thread-%s" % src.getProperty("id"),
srcobj=src, dstobj=dst, srcoffset=srcoffset, dstoffset=dstoffset, srclength=srclength,
dstlength=dstlength, specified_start_zone=specified_start_zone,
specified_range_size=specified_range_size, parallel=False)
threads.append(th)
th.start()
for th in threads:
if th.is_alive():
th.join()
if th.errorMsg:
errors.append(th.errorMsg)
if len(errors) > 0:
raise UniAutosException(str(errors))
else:
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
{"command": ['sh', '-c', 'sync', '&&', 'echo 3', '>', '/proc/sys/vm/drop_caches', '&&',
'sleep 2']})
# 构造命令下发参数
if srcoffset and dstoffset:
if srclength and dstlength:
command = ["sh", "-c", "cmp", srcDiskDevice, dstDiskDevice, "-i", str(srcoffset), "-n",
str(srclength)]
else:
command = ["sh", "-c", "cmp", "-i", str(srcoffset) + ":" + str(dstoffset), srcDiskDevice,
dstDiskDevice, ]
elif specified_range_size and specified_start_zone:
command = ["sh", "-c", "cmp", "-i", specified_start_zone, "-n", specified_range_size,
srcDiskDevice,
dstDiskDevice]
else:
command = ["sh", "-c", "cmp", srcDiskDevice, dstDiskDevice]
result = self.run({"command": command})
if result['stderr']:
raise CommandException(str(result['stderr']))
else:
# 当stdout不为None且differ显示的数量不为0，数据不一致
matcher = re.search('differ', result['stdout']) if result['stdout'] else None
if matcher:
self.logger.error(
"Data consistent compare failed between source lun: %s and target lun: %s" %
(source_lun_id, target_lun_id))
raise UniAutosException('It\'s data inconsistent between the specified files.')
self.logger.info("Data consistent compare passed between source lun: %s and target lun: %s" %
(source_lun_id, target_lun_id))
else:
raise InvalidParamException

def ulimit(self, params):
"""
linux系统下发ulimit

Args:
params (list): 下发命令的列表

Returns:
result (dict): 命令返回结果

Example:
host.ulimit(['-a'])

"""
command = ["sh", "-c", 'ulimit'] + params
result = self.run({"command": command})
return result

def addOpenFilesConfig(self):
"""
Append the configuration at the end of '/etc/security/limits.conf'

Author:
l00355383 2017-7-12 9:42:37 Created
"""
self.logger.info('Change the open files config')
command = ['sh', '-c', 'sudo', 'echo', '-e',
'"* soft nofile 65535\n* hard nofile 65535">>/etc/security/limits.conf']
self.run({"command": command})
self.reboot(wait=True)

def getOpenFilesNumber(self):
"""
get the system open files number

Returns:
number (int): the open files number

Author:
l00355383 2017-7-12 9:42:37 Created
"""
result = self.ulimit(['-a'])['stdout']
searchResult = re.search(r'open\s*files\s*\(-n\)\s*(\d+)', result)
openFilesNumber = int(searchResult.group(1))
return openFilesNumber

def dd(self, diskDevice='/dev/sdb', of='/dev/null', skip=None, seek=None, bs=None, count=None, iflag=None,
oflag=None, conv=None):
"""
DD zhe disk。

Args:
diskDevice (str)|（SnapshotBase|LunBase）: read from FILE instead of stdin，(支持盘符传递和映射对象去自助获取盘符)
of (str): write to FILE instead of stdout
skip (str): skip BLOCKS ibs-sized blocks at start of input
seek (str): skip BLOCKS obs-sized blocks at start of output
bs (int): read and write up to BYTES bytes at a time
count (int): copy only BLOCKS input blocks

Author:
hwx214803 2017-8-1 9:42:37 Created
"""
if isinstance(diskDevice, LunBase) or isinstance(diskDevice, SnapshotBase) or isinstance(diskDevice, Volume):
diskDevice = self._getDiskDevice(diskDevice)
if isinstance(of, LunBase) or isinstance(of, SnapshotBase) or isinstance(of, Volume):
of = self.getDiskDeviceName(of)
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
if conv is not None:
command.append('conv=%s' % conv)
self.run({"command": command})

def removeFile(self, fileName):
"""
remove a file

Args:
file (str): FILE name

Author:
hwx214803 2017-8-8 9:42:37 Created
"""
command = ["sh", "-c", "rm", "-rf", fileName]
self.run({"command": command})

def getSimulator(self):
"""
get zhe Simulator host

returns:
Simulator (linuxobj): UniAutos.Device.Host.Linux.Linux
Author:
hwx214803 2017-8-8 9:42:37 Created
"""
self.Simulator = Simulator(self)
return self.Simulator

def chapIscsiConfSeeting(self, usrName, userPasswd, fileBakPth='/opt/iscsid.confbat',
usrNameIn=None, userPasswdIn=None, ):
"""CHAP认证在主机端修改密码修改iscsiid.conf文件
Arges:

usrName str:[必选]chap认证用户名
userPasswd str:[必选]chap认证密码
usrNameIn str:[可选]chap认证用户名
userPasswdIn str:[可选]chap认证密码
fileBakPth str:[可选]备份文件路径，默认为/opt/iscsid.confbat

Example:
self.host.chapIscsiConfSeeting(usrName='dssss',userPasswd='sdwadwa',fileBakPth='/usr/iscsid.confbat')
"""
# 备份文件
self.run({"command": ["sh", "-c", "cp", "-rf", "/etc/iscsid.conf", "%s" % fileBakPth]})

# 修改/opt/iscsid.confbat文件
command = ["sh", "-c", "sed", "-i", "'/.node.session.auth.authmethod./c\\node.session.auth.authmethod = CHAP'",
'/etc/iscsid.conf']
self.run({"command": command})
command = ["sh", "-c", "sed", "-i",
("'/.discovery.sendtargets.auth.authmethod =." "/c\discovery.sendtargets.auth.authmethod = CHAP'"),
'/etc/iscsid.conf']
self.run({"command": command})
command = ["sh", "-c", "sed", "-i",
"'/.node.session.auth.username =./c\\node.session.auth.username = %s'" % usrName, '/etc/iscsid.conf']
self.run({"command": command})
command = ["sh", "-c", "sed", "-i",
"'/.node.session.auth.password =./c\\node.session.auth.password = %s'" % userPasswd,
'/etc/iscsid.conf']
self.run({"command": command})
if usrNameIn:
command = ["sh", "-c", "sed", "-i",
"'/.node.session.auth.username_in =./c\\node.session.auth.username_in = %s'" % usrNameIn,
'/etc/iscsid.conf']
self.run({"command": command})
if userPasswdIn:
command = ["sh", "-c", "sed", "-i",
"'/.node.session.auth.password_in =./c\\node.session.auth.password_in = %s'" % userPasswdIn,
'/etc/iscsid.conf']
self.run({"command": command})
command = ["sh", "-c", "sed", "-i",
(
"'/.discovery.sendtargets.auth.username =." "/c\discovery.sendtargets.auth.username = %s'" % usrName),
'/etc/iscsid.conf']
self.run({"command": command})
command = ["sh", "-c", "sed", "-i", (
"'/.discovery.sendtargets.auth.password =." "/c\discovery.sendtargets.auth.password = %s'" % userPasswd),
'/etc/iscsid.conf']
self.run({"command": command})
if usrNameIn:
command = ["sh", "-c", "sed", "-i", ("'/.discovery.sendtargets.auth.username_in =." "/c\discovery."
"sendtargets.auth.username_in = %s'" % usrNameIn), '/etc/iscsid.conf']
self.run({"command": command})
if userPasswdIn:
command = ["sh", "-c", "sed", "-i", ("'/.discovery.sendtargets.auth.password_in =." "/c\discovery."
"sendtargets.auth.password_in = %s'" % userPasswdIn),
'/etc/iscsid.conf']
self.run({"command": command})

def chapIscsiConfRestorr(self, fileBakPth='/opt/iscsid.confbat'):
"""主机端从备份路径还原修CHAP认证修改的iscsiid.conf文件
Arg:

fileBakPth str:[可选]指定备份文件还原至/etc/iscsid.conf，如果不输入默认备份路径为/opt/iscsid.confbat

Example:
self.host.chapIscsiConfRestorr(fileBakPth='/usr/iscsid.confbat')
"""
self.run({"command": ["sh", "-c", "cp", "-rf", "%s" % fileBakPth, "/etc/iscsid.conf"]})

def sgRawWriteSameData(self, lba, sizeData, lunObj):
"""对lun进行写块命令
arge:
lba(str):开始写入位置
sizeData(str):写入数据大小
lunObj(Lun):需要写入的lun对象

return:
返回命令执行回显

example:
hostlinux.sgRawWriteSameData(lba='1MB',sizeData='10MB',lunObj=lunList[0])
"""
device = self._getDiskDevice(lunObj)
# 转换单位为KB
lbaKB = Units.convert(lba, 'KB')
dateKB = Units.convert(sizeData, 'KB')
# 获取KB单位前面的数值
parserLba = int(Units.parse(lbaKB)[0]) * 2
parserdate = int(Units.parse(dateKB)[0]) * 2
# KB数值转换为16进制*2（1KB为2扇区）
startLba = int(hex(parserLba).split('0x')[1])
writedata = int(hex(parserdate).split('0x')[1])
# 查询LBA和data的长度
lenLba = len(str(startLba))
lenData = len(str(writedata))
totalLbaLen = 16
totalData = 8
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
DATA = '0' * (totalData - lenData) + str(writedata)
# 每隔两位空一格
pattern = re.compile('.{1,2}')
LBA = (' '.join(pattern.findall(LBA)))
DATA = (' '.join(pattern.findall(DATA))) + " 00 00"
cmd = ('cd /opt/gstool/;./sg_raw' + ' -s 512' + ' -i write_same_data ' +
device + ' 93 00 ' + LBA + ' ' + DATA)
cmdSpec = {"command": ["sh", "-c", cmd], "waitstr": 'SCSI Status: Good'}
result = self.run(cmdSpec)
return result

def sgRawWriteSameZero(self, lba, sizeData, lunObj):
"""从LBA开始（写零）回收空间
arge:
lba(str):开始写入位置
sizeData(str):写入数据大小
lunObj(Lun):需要写入的lun对象

return:
返回命令下发回显结果

example:
hostlinux.sgRawWriteZero(lba='0MB', sizeData='16MB', lunObj=lunList[0])

"""
device = self._getDiskDevice(lunObj)
# 校验单位是否合法
if not Units.isSize(lba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
if not Units.isSize(sizeData) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
lbaBt = Units.convert(lba, 'B')
dateBt = Units.convert(sizeData, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserLba = int(Units.parse(lbaBt)[0]) / 512
parserdate = int(Units.parse(dateBt)[0]) / 512
# KB数值转换为16进制
startLba = int(hex(parserLba).split('0x')[1])
writedata = int(hex(parserdate).split('0x')[1])
# 查询LBA和data的长度
lenLba = len(str(startLba))
lenData = len(str(writedata))
totalLbaLen = 16
totalData = 8
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
DATA = '0' * (totalData - lenData) + str(writedata)
# 每隔两位空一格
pattern = re.compile('.{1,2}')
LBA = (' '.join(pattern.findall(LBA)))
DATA = (' '.join(pattern.findall(DATA))) + " 00 00"
cmd = ('cd /opt/sgTool/;./sg_raw' + ' -s 512' + ' -i write_same_zero ' +
device + ' 93 08 ' + LBA + ' ' + DATA)
cmdSpec = {"command": ["sh", "-c", cmd], "waitstr": 'SCSI Status: Good'}
result = self.run(cmdSpec)
return result

def sgRawRead(self, lba, sizeData, lunObj):
"""LBA开始（写零）回收制定大小数据
arge:
lba(str):开始写入位置
sizeData(str):写入数据大小
lunObj(Lun):需要写入的lun对象

example:
hostlinux.sgRawReadData(lba='3MB', sizeData=512, lunObj=lunList[0])

"""
device = self._getDiskDevice(lunObj)
# 校验单位是否合法
if not Units.isSize(lba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
lbaBt = Units.convert(lba, 'B')
dateBt = Units.convert(sizeData, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserLba = int(Units.parse(lbaBt)[0]) / 512
parserdate = int(Units.parse(dateBt)[0]) / 512
# KB数值转换为16进制
startLba = int(hex(parserLba).split('0x')[1])
writedata = int(hex(parserdate).split('0x')[1])
# 查询LBA和data的长度
lenLba = len(str(startLba))
lenData = len(str(writedata))
totalLbaLen = 16
totalData = 8
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
DATA = '0' * (totalData - lenData) + str(writedata)
# 每隔两位空一格
pattern = re.compile('.{1,2}')
LBA = (' '.join(pattern.findall(LBA)))
DATA = (' '.join(pattern.findall(DATA))) + " 00 00"
cmd = ('cd /opt/sgTool/;./sg_raw' + ' -s 512' + ' -i zero_data ' + device +
' 93 08 ' + LBA + ' ' + DATA)
cmdSpec = {"command": ["sh", "-c", cmd], "waitstr": 'SCSI Status: Good'}
result = self.run(cmdSpec)
return result

def sgRawReadData(self, lba, length, lunObj):
"""从lba开始，读出length的长度数据，对比数据是否一致
arge:
lba(str）:开始写入位置，如1MB，1GB
length(int）:读取长度，如512
lunObj(Lun）:需要读取的lun对象

return:
返回命令下发回显

example:
hostlinux.sgRawReadData(lba='3MB', length=512, lunObj=lunList[0])

"""
device = self._getDiskDevice(lunObj)
# 校验单位是否合法
if not Units.isSize(lba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
lbaBt = Units.convert(lba, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserLba = int(Units.parse(lbaBt)[0]) / 512
# KB数值转换为16进制
startLba = int(hex(parserLba).split('0x')[1])
# 计算length单位512B为单位
length = length / 512
# 查询LBA和data的长度
lenLba = len(str(startLba))
lenData = len(str(length))
totalLbaLen = 8
totalLen = 4
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
DATA = '0' * (totalLen - lenData) + str(length)
# 每隔两位空一格
pattern = re.compile('.{1,2}')
LBA = (' '.join(pattern.findall(LBA)))
DATA = (' '.join(pattern.findall(DATA))) + " 00"
cmd = ('cd /opt/sgTool/;./sg_raw' + ' -r 512' + ' -o read_ws_data ' +
device + ' 28 00 ' + LBA + ' 00 ' + DATA)
cmdSpec = {"command": ["sh", "-c", cmd]}
result = self.run(cmdSpec)
return result

def sgUnmapdata(self, lba, blocks, lunObj):
"""Unmap回收
arg:
lba(str):回收地址，如1MB
blocks(str):回收块大小，如'16MB'
lunObj(Lun):需要写入的lun对象

return:
返回命令下发回显

example:
hostlinux.sgUnmapdata(lba='0B', blocks='16MB',lunObj=lunList[0])
"""
device = self._getDiskDevice(lunObj)
# 校验单位是否合法
if not Units.isSize(lba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
if not Units.isSize(blocks) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
lbaBt = Units.convert(lba, 'B')
blocksBt = Units.convert(blocks, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserLba = int(Units.parse(lbaBt)[0]) / 512
parserdate = int(Units.parse(blocksBt)[0]) / 512
# KB数值转换为16进制
startLba = int(hex(parserLba).split('0x')[1])
writedata = int(hex(parserdate).split('0x')[1])
# 查询LBA和data的长度
lenLba = len(str(startLba))
lenData = len(str(writedata))
totalLbaLen = 16
totalData = 8
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
DATA = '0' * (totalData - lenData) + str(writedata)
# 每隔两位空一格
pattern = re.compile('.{1,4}')
LBA = (' '.join(pattern.findall(LBA)))
DATA = (' '.join(pattern.findall(DATA)))
# 预制第一行内容
lba = '0000000: 0016 0010 0000 0000 %s ................' % LBA
# 预制第二行内容
block = '0000010: %s 0000 0000 0000 0000 0000 0000 ................' % DATA
# d读取unmapdata文件内容
unmapdatadatail = self.run({"command": ["sh", "-c", 'xxd /opt/sgTool/unmapdata']})['stdout']
# 对unmapdata文件内容第一行和第二行进行修改
unmapdatadatailList = unmapdatadatail.split('\n')
unmapdatadatailList[0] = lba
unmapdatadatailList[1] = block
# 重写unmapdata文件内容文件
self.run({"command": ["sh", "-c", 'mv', '/opt/sgTool/unmapdata', '/opt/sgTool/unmapdata.bak']})
for line in unmapdatadatailList:
if line == unmapdatadatailList[0]:
self.run({"command": ["sh", "-c", 'echo -e', line, '>', '/opt/sgTool/unmapdata']})
if line != unmapdatadatailList[0]:
self.run({"command": ["sh", "-c", 'echo -e', line, '>>', '/opt/sgTool/unmapdata']})
self.run({"command": ["sh", "-c", 'chmod +x', '/opt/sgTool/unmapdata']})
# 执行命令，固定格式
cmd = 'cd /opt/sgTool/;./sg_raw -i unmapdata -s 512 %s 42 00 00 00 00 00 00 00 18 00' % device
cmdSpec = {"command": ["sh", "-c", cmd]}
result = self.run(cmdSpec)
return result

def sgExtendCopyParam(self, sourceLba, targetLba, blocks, sourceLun, targeteLun):
"""从源lun 固定区域拷贝数据到目标lun指定的区域
arg:
lba(str):回收地址，如1MB
blocks(str):回收块大小，如'16MB'
sourceLba(Lun):源lun对象
targetLba(Lun):目标lun对象

return:
返回命令下发回显

example:
hostlinux.sgExtendCopyParam(sourceLba='1MB', targetLba='10MB', blocks='10MB',
sourceLun=lunList[0],targeteLun=lunList[1])
"""
# 获取主lun盘符
device = self._getDiskDevice(sourceLun)
# 校验单位是否合法
if not Units.isSize(sourceLba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
if not Units.isSize(targetLba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
if not Units.isSize(blocks) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
sourceLba = Units.convert(sourceLba, 'B')
targetLba = Units.convert(sourceLba, 'B')
blocks = Units.convert(blocks, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserSourceLba = int(Units.parse(sourceLba)[0]) / 512
parserTargetLba = int(Units.parse(targetLba)[0]) / 512
parserdate = int(Units.parse(blocks)[0]) / 512
# KB数值转换为16进制
parserSourceLba = int(hex(parserSourceLba).split('0x')[1])
parserTargetLba = int(hex(parserTargetLba).split('0x')[1])
parserBlocks = int(hex(parserdate).split('0x')[1])
sourceLba = '0' * (8 - len(str(parserSourceLba))) + str(parserSourceLba)
targetLba = '0' * (20 - len(str(parserTargetLba))) + str(parserTargetLba) + ' 00'
# 获取两个LUN的wwn号并分割成两部分以便写入
sourceWwn = textwrap.wrap(text=sourceLun.getProperty("wwn"), width=16)
targetWwn = textwrap.wrap(text=targeteLun.getProperty("wwn"), width=16)
# 读取extendcopyparam文件内容
extendcopyparamdetail = self.run({"command": ["sh", "-c", 'xxd /opt/sgTool/extendcopyparam']})['stdout']
# 对extendcopyparam进行修改
extendcopyparamList = extendcopyparamdetail.split('\n')
pattern = re.compile('.{1,4}')
# 修改extendcopyparam文件中的主从lun WWN
extendcopyparamList[1] = '0000010: e400 0000 0103 0010 %s ........f6...trl' % (
' '.join(pattern.findall(sourceWwn[0])))
extendcopyparamList[2] = '0000020: %s 2 0000 0000 0000 0200 ................' % (
' '.join(pattern.findall(sourceWwn[1])))
extendcopyparamList[3] = '0000030: e400 0000 0103 0010 %s ........f6...trl' % (
' '.join(pattern.findall(targetWwn[0])))
extendcopyparamList[4] = '0000040: %s 0000 0000 0000 0200 .3.', '/opt/sgTool/extendcopyparam']})
for line in extendcopyparamList:
if line != extendcopyparamList[0]:
self.run({"command": ["sh", "-c", 'echo -e', line, '>>', '/opt/sgTool/extendcopyparam']})
self.run({"command": ["sh", "-c", 'chmod +x', '/opt/sgTool/unmapdata']})
# 执行命令，固定格式
cmd = ('cd /opt/sgTool/;./sg_raw -i extendcopyparam -s 108 %s 83 00 00 00 00'
' 00 00 00 00 00 00 00 00 6C 00 00' % device)
cmdSpec = {"command": ["sh", "-c", cmd]}
result = self.run(cmdSpec)
return result

def stopNxup(self):
""" 关闭主机多路径service nxup stop
example:
self.host.stopNxup()
"""

for i in range(60):
result = self.run({"command": ["sh", "-c", "service", "nxup", "stop"]})
if not re.search('successfully', result['stdout']):
self.logger.info("第 %s次关闭失败" % i)
sleep(2)
else:
break

def startNxup(self):
""" 开启主机多路径service nxup start
example:
self.host.startNxup()

return :
(bool):True、False
"""
result = self.run({"command": ["sh", "-c", "service", "nxup", "start"]})
if re.search('Y\|N', result['stdout']):
result = self.run({"command": ["sh", "-c", "service", "nxup", "start"],
"waitstr": "Y\|N", "input": ["y", "[#]"]})
if not re.search('successfully', result['stdout']):
return False
else:
return True

def scanScsiHost(self):
"""无多路径扫lun
example:
self.host.scanScsiHost()
"""
result = self.run(
{"command": ["sh", "-c", "ls", "//sys//class//scsi_host//"]})
hostList = result['stdout'].split('\n')
for host in hostList:
self.run(
{"command": ["sh", "-c", "echo", "\"- - -\"", ">", "/sys/class/scsi_host/%s/scan" % host]})

def getLunDriver(self, lunObj):
"""获取lun在主机上面的所有链路
arge:
lunObj(Lun):lun对象

return:
[list]:返回该lun在主机上面的所有链路列表

example:
self.host.getLunDriver(lunObj=lunList[0])
"""

# 获取所有链路
result = self.run({"command": ["sh", "-c", "fdisk", "-l"]})['stdout']
resultList = result.split('\n')
# 匹配Disk /dev/sdf: 10.7 GB, 10737418240 bytes
pattern1 = 'Disk( .+):(.+),(.+)bytes'
diskList = []
for item in resultList:
if re.search(pattern1, item):
diskList.append(re.search(pattern1, item).group(1))
# 根据传入lunObj的wwn查询归属该lun的链路
lunWwn = lunObj.getProperty("wwn")
lunDisk = []
pattern2 = 'Vendor Specific Identifier Extension: (.+)'
for disk in diskList:
result = self.run({"command": ["sh", "-c", 'cd', '/opt/sgTool/;./sg_inq -p 0X83', disk]})['stdout']
resultList = result.split('\n')
for line in resultList:
if re.search(pattern2, line):
diskWwn = re.search(pattern2, line).group(1).split('0x')[1]
if re.search(diskWwn, lunWwn):
lunDisk.append(disk)
return lunDisk

def lunReservation(self, lunDriver, reservation):
"""链路下发对lun预留或去预留命令
arg:
lunDriver(str):lun映射到主机上面的链路
reservation(bool):True(预留)，False(去预留)

return:
命令下发回显
"""
# 执行命令，固定格式
if reservation == True:
cmd = 'cd /opt/sgTool/;./sg_raw %s 16 00 00 00 00 00' % lunDriver
if reservation == False:
cmd = 'cd /opt/sgTool/;./sg_raw %s 17 00 00 00 00 00' % lunDriver
cmdSpec = {"command": ["sh", "-c", cmd]}
result = self.run(cmdSpec)
return result

def sgVaaiData(self, lunObj, lba):
""" 将lun的lba数据读取出来和指定文件的512字节的数据进行比较，比较后写入指定文件的后512个字节
arg:
lunObj(Lun):lun对象
lba(str):校验起始位置

return:
命令下发回显

example:
hostlinux.sgVaaiData(lunObj=lunList[0], lba='1MB')
"""
# 获取lun盘符
device = self._getDiskDevice(lunObj)
# 校验单位是否合法
if not Units.isSize(lba) == True:
raise CommandException("Plese input innocent Size,like '1B,1GB,'100TB','2E-5PB'")
# 转换单位为B
lbaBt = Units.convert(lba, 'B')
# 获取Bt单位前面的数值除以扇区大小512
parserLba = int(Units.parse(lbaBt)[0]) / 512
# KB数值转换为16进制
startLba = int(hex(parserLba).split('0x')[1])

# 查询LBA和data的长度
lenLba = len(str(startLba))
totalLbaLen = 16
LBA = '0' * (totalLbaLen - lenLba) + str(startLba)
# 每隔两位空一格
pattern = re.compile('.{1,2}')
LBA = (' '.join(pattern.findall(LBA))) + ' 00 00 00 01 00 00'
cmd = 'cd /opt/sgTool/;./sg_raw' + ' -i vaai_data_caw ' + ' -s 1024 ' + device + ' 89 00 ' + LBA
cmdSpec = {"command": ["sh", "-c", cmd]}
result = self.run(cmdSpec)
return result

def statFile(self, file):
"""查询文件权限和保护期
arg:
file(str):需要查询的文件
return:
(dict):命令回显信息
{'Access': '2080-03-14 05:05:24',
'Modify': '2080-03-14 05:05:24',
'Change': '2080-03-14 05:05:24',
'File': "/tmp/tt/1.txt'"}
example:
self.hostlinux = self.getHost(role='io', platform='linux')[0]
info = self.hostlinux.statFile(file='/tmp/tt/1.txt')
"""
rst = self.run({"command": ["sh", "-c", "stat", "%s" % file]})
rstList = rst['stdout'].split('\n')
info = {}
# 匹配Access: 2080-03-14 05:05:24.000000000 +0800
pattern = '(\w+):\s+(\d+-\d+-\d+\s+\d+:\d+:\d+).(.+)'
for item in rstList:
if re.search('File: `', item):
info['File'] = item.split('`')[1]
if re.search(pattern, item):
ret = re.search(pattern, item)
info[ret.group(1)] = ret.group(2)
return info

def setUpadminHyperMetroLoadBalanceMode(self, loadbalancemode='split-size'):
"""主机测设置主机多路径双活负载均衡模式

Args:
loadbalancemode (str): 负载均衡模式,{split-size|round-robin}默认为split-size

Raises:
CommandException: 命令执行失败.

Examples:
host.setUpadminHyperMetroLoadBalanceMode(loadbalancemode = "round-robin")


"""
command = ["sh", "-c", "upadmin", "set", "hypermetro", "loadbalancemode=%s" % loadbalancemode]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
self.logger.debug("HyperMetro loadbalancemode set succeeded.")
else:
raise CommandException("HyperMetro loadbalancemode set failed.")

def setUpadminLoadBalanceMode(self, loadbalancemode='split-size'):
"""主机测设置主机多路径双活负载均衡模式

Args:
loadbalancemode (str): 负载均衡模式,{split-size|round-robin}默认为split-size

Raises:
CommandException: 命令执行失败.

Examples:
host.setUpadminLoadBalanceMode(loadbalancemode = "round-robin")


"""
command = ["sh", "-c", "upadmin", "set", "loadbalancemode=%s" % loadbalancemode]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
self.logger.debug("Loadbalancemode set succeeded.")
else:
raise CommandException("Loadbalancemode set failed.")

# huangxu hwx639576
def setUpadminlb_io_threshold(self, lb_io_threshold='100'):
"""设置qos在round-robin模式下的阈值

Args:
lb_io_threshold (str):-- Set the number of I/O to route to a path before switching to the next path.
-- number is in the range 1-10000.
-- Default is 100.

Raises:
CommandException: 命令执行失败.

Examples:
host.setUpadminlb_io_threshold(workingmode = "1")


"""
command = ["sh", "-c", "upadmin", "set", "lb_io_threshold=%s" % lb_io_threshold]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
self.logger.debug("lb_io_threshold set succeeded.")
else:
raise CommandException("lb_io_threshold set failed.")

def setUpadminworkingmode(self, workingmode='0'):
"""主机测设置主机多路径双活负载均衡模式

Args:
workingmode (str): 负载均衡模式,{'0'/'1'}

Raises:
CommandException: 命令执行失败.

Examples:
host.setUpadminworkingmode(workingmode = "0")


"""
command = ["sh", "-c", "upadmin", "set", "workingmode=%s" % workingmode]

cmdSpec = {"command": command}

result = self.run(cmdSpec)
if re.search(r'Succeeded in executing the command', result['stdout'], re.M):
self.logger.debug("Workingmode set succeeded.")
else:
raise CommandException("Workingmode set failed.")

def upadminShowUpconfig(self):
"""获取upadmin show upconfig的回显

Returns:
targets (list): 所有查询到的主机多路径信息,.

Output:
arrayOutput:
Basic Configuration
Working Mode : load balancing within controller
LoadBalance Mode : min-queue-depth
Loadbanlance io threshold : 100
LUN Trespass : on

Advanced Configuration
Io Retry Times : 10
Io Retry Delay : 0
Faulty path check interval : 10
Idle path check interval : 60
Failback Delay Time : 600
Io Suspension Time : 60
Max io retry timeout : 1800
Performance Record : off
returnResult:
{'AdvancedConfiguration': {'PerformanceRecord': 'off', 'IoSuspensionTime': '60', 'Faultypathcheckinterval': '10', 'FailbackDelayTime': '600', 'IoRetryDelay': '0', 'IoRetryTimes': '10', 'Maxioretrytimeout': '1800', 'Idlepathcheckinterval': '60'}, 'BasicConfiguration': {'LUNTrespass': 'on', 'Loadbanlanceiothreshold': '100', 'LoadBalanceMode': 'min-queue-depth', 'WorkingMode': 'load balancing within controller'}}

example:
字典key值为项目名去除空格
info = self.host1.upadminShowUpconfig()
print(info['AdvancedConfiguration']['PerformanceRecord'])
"""

cmd = ['sh', '-c', 'upadmin', 'show', 'upconfig']
ret = self.run({"command": cmd})
retlist = re.split('\x0d?\x0a|\x0d', ret['stdout'])
cmdresult = {}
for i in range(len(retlist)):
if 'Basic Configuration' in retlist[i]:
basicline = i
if 'Advanced Configuration' in retlist[i]:
advancedline = i
if 'Path reliability configuration' in retlist[i]:
pathline = i
if 'HyperMetro configuration' in retlist[i]:
hyperline = i
basicinfo = retlist[basicline + 1:advancedline - 1]
advancedinfo = retlist[advancedline + 1:pathline - 1]
pathinfo = retlist[pathline + 1:hyperline - 1]
hyperinfo = retlist[hyperline + 1:-2]

def parser(info):
result = {}
for line in info:
result[line.split(':')[0].replace(' ', '')] = line.split(':')[1].lstrip()
return result

cmdresult[retlist[basicline].replace(' ', '')] = parser(basicinfo)
cmdresult[retlist[advancedline].replace(' ', '')] = parser(advancedinfo)
cmdresult[retlist[pathline].replace(' ', '')] = parser(pathinfo)
cmdresult[retlist[hyperline].replace(' ', '')] = parser(hyperinfo)
return cmdresult

def getMountSnapshotPathList(self):
"""快照目录自动挂载的路径
Example:
self.host.getMountSnapshotPathList()

Return:
(list): 快照目录自动挂载的路径
"""
rst = self.run({"command": ["sh", "-c", "cat /proc/self/mountinfo"]})
snapMountList = []
for i in rst['stdout'].split('\n'):
# 匹配'nfs 128.46.115.44:/f_7g648e06/.snapshot/was'
pattern = '.+nfs\d?\s+\d+.\d+.\d+.\d+:(\S+)\s+'
if re.search(pattern, i):
ret = re.search(pattern, i)
snapMountList.append(ret.group(1))
if len(snapMountList) == 0:
return None
else:
return snapMountList

def removeUniBlkIoLogFile(self, day=10):
"""删除UniBlkIo日志文件

Args:
day type(int): 删除多少天以上的日志
Example:
self.host.removeUniBlkIoLogFile()

"""
logFilePath = ''
try:
# 获取UniBlkIo日志文件所在路径
result = self.run({"command": ["sh", "-c", "which", "UniBlkIo"]})
if result:
if result['stdout']:
logFilePath = result['stdout'].rsplit('/', 1)[0]
if logFilePath:
# 清理日志文件
self.run({"command": ['sh', '-c', 'find', '%s' % logFilePath, '-mtime', '+%s' % str(day), '-type', 'd',
'-name',
'"UniBlkIoLog*"', '-prune', '-exec', 'rm', '-rf', '{}', '\;']})
self.logger.debug('remove UniBlkIo logFile successfully, log file path: %s, remove date: %s' % (
logFilePath, str(day)))
except:
self.logger.warn(
'remove UniBlkIo logFile faild, log file path: %s, remove date: %s' % (logFilePath, str(day)))

def sgSCSITest(self, command, params):
"""
use sg to verify scsi， this is just a short cut for command verification, more scsi sg test could be found in SgUtil
:param command: the SCSI command to test
:param params: the command params , type: dict
:return:
"""
from UniAutos.Io.sg_utils import SgUtil

utils = SgUtil(self)
if command == 'MODE SELECT(6)':
utils.mode_select_6(**params)
elif command == 'UNMAP':
utils.unmap(**params)
elif command == 'RESERVE(10)':
utils.reserve_10(**params)
elif command == 'RELEASE(10)':
utils.release_10(**params)
elif command == 'MODE SENSE(10)' or command == "FORMAT":
utils.format(**params)
elif command == 'WRITE AND VERIFY(16)':
utils.write_and_verify_16(**params)
elif command == 'MAINTENANCE IN':
utils.maintenance_in(**params)
elif command == 'MAINTENANCE OUT':
utils.maintenance_out(**params)
elif command == 'WRITE AND VERIFY(10)':
utils.write_and_verify_10(**params)
elif command == 'COMPARE AND WRITE':
utils.compare_and_write(**params)
elif command == 'REQUEST SENSE':
utils.request_sense(**params)
elif command == "VERIFY(16)":
params["verify_16"] = True
utils.verify_10or16(**params)
elif command == "VERIFY(10)":
params["verify_16"] = False
utils.verify_10or16(**params)
elif command == "READ(6)":
utils.read_6(**params)
elif command == "WRITE(6)":
utils.write_6(**params)
elif command == "READ(10)":
utils.read_10(**params)
elif command == "WRITE(10)":
utils.write_10(**params)
elif command == "READ(16)":
utils.read_16(**params)
elif command == "WRITE(16)":
utils.write_16(**params)
elif command == "COMPARE AND WRITE":
utils.compare_and_write(**params)
elif command == "WRITE SAME(16)":
utils.write_same_16(**params)
elif command == "Third-party Copy IN commands":
utils.third_party_copy_in(**params)
elif command == "Third-party Copy OUT commands":
utils.third_party_copy_out(**params)
elif command == "START STOP UNIT":
utils.start_stop_unit(**params)

def sftpGet(self, ip, port, user, password, files, target, timeout=1200):
"""获取指定sftp服务器上的文件到主机
"""
cmd = "sftp -o StrictHostKeyChecking=no -P {0} {1}@{2}".format(port, user, ip)
params = {
"command": [cmd],
"input": [password, "sftp>"],
"waitstr": "password:",
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

def listAllUser(self):
"""返回当前主机上的所有用户的信息列表

"""
ret = self.run({"command": ["cat /etc/passwd"]})
if not ret.get('stdout'):
return None
lines = self.split(ret.get('stdout'))
keys = ['name', 'password', 'uid', 'gid', 'comment', 'home', 'shell']

users = {}
for l in lines:
info = l.split(":")
if 7 == len(info):
user = dict(zip(keys, info))
users.update({user['uid']: user})
return users

def create_lv(self, lun, vg_name, lv_name, capacity):
"""创建LV流程，通过创建pv-创建vg-创建LV

Args:
lun (PoolLun): lun component object
vg_name (str): vg name
lv_name (str): lv name
capacity (str): lv capacity
"""
disk_device = self.getDiskDeviceName(lun)
self.logger.info('create pv on disk %s' % disk_device)
self.run({"command": ['pvcreate', disk_device], "checkrc": 1})
self.logger.info('create vg on disk %s' % disk_device)
self.run({"command": ['vgcreate', vg_name, disk_device], "checkrc": 1})
self.logger.info('create lv on vg %s' % vg_name)
self.run({"command": ['lvcreate -L %s -n %s %s' % (capacity, lv_name, vg_name)], "checkrc": 1})
result = '/dev/%s/%s' % (vg_name, lv_name)
return result

def create_fs(self, fs_type, lv_path):
"""
基于LV创建Linux文件系统

Args:
fs_type (str): 文件系统类型，ext3,ext4,xfs等
lv_path (str): LV的路径

Returns:
lv_path (str): LV的路径
"""
self.logger.info('将%s创建文件系统%s' % (lv_path, fs_type))
if fs_type in ['ext4', 'xfs']:
cmd = ["sh", "-c", "mkfs", "-t", fs_type, lv_path]
self.run({"command": cmd,
"timeout": 3600, "checkrc": 1})
elif fs_type in ['gfs2']:
cmd = ['sh -c mkfs.%s -p lock_dlm -t ha_cluster:gfs2_fs -j 8 %s' % (fs_type, lv_path)]
self.run({"command": cmd, "waitstr": "[y/n]", "input": ["y", "~]#"], "timeout": 3600, "checkrc": 1})
else:
raise UniAutosException('the %s filesystem does not support creation' % fs_type)

return lv_path

def mount_fs(self, lv_path, dir_path):
"""
mount 文件系统到指定路径

Args:
lv_path (str): LV的路径
dir_path (str): mount的路径

Returns:
lv_path (str): LV的路径
"""
self.logger.info('mount 文件系统%s到指定路径%s' % (lv_path, dir_path))
cmd = ["sh", "-c", "mount", "-o", "discard", lv_path, dir_path]
self.run({"command": cmd, "checkrc": 1})
return lv_path

def mount_rhcs(self, fs_type, lv_path, dir_path):
"""
mount rhcs文件系统到指定路径

Args:
fs_type (str): 文件系统类型
lv_path (str): LV的路径
dir_path (str): mount的路径

Returns:
lv_path (str): LV的路径
"""
self.logger.info('mount %s文件系统%s到指定路径%s' % (fs_type, lv_path, dir_path))
cmd = ['sh -c pcs resource create gfs2_res ocf:heartbeat:Filesystem device="%s" '
'directory="%s" fstype="%s" options="noatime,nodiratime,discard" '
'op monitor interval=10s on-fail=fence clone interleave=true' % (
lv_path, dir_path, fs_type)]
self.run({"command": cmd, "checkrc": 1})
return lv_path

def resize_lv(self, lun):
"""
resize lv的大小

Args:
lun (PoolLun): lun component object

"""
disk_device = self.getDiskDeviceName(lun)
self.logger.info('resize lv on disk %s' % disk_device)
self.run({"command": ['sh', '-c', 'partprobe'], "checkrc": 1})
self.run({"command": ['sh', '-c', 'pvresize', disk_device], "checkrc": 1})

def extend_lv(self, capacity, lv_path):
"""
扩容 lv

Args:
lv_path (str): LV的路径
capacity(int): 扩容LV的大小
"""

self.logger.info('extend %s to %s' % (capacity, lv_path))
self.run({"command": ['sh', '-c', 'lvextend -L +%s %s' % (capacity, lv_path)], "checkrc": 1})

def extend_ext4(self, lv_path):
"""
扩容 ext4文件系统

Args:
lv_path (str): LV的路径
"""

self.logger.info('extend ext4 on %s' % lv_path)
self.run({"command": ['sh', '-c', 'resize2fs %s' % lv_path], "checkrc": 1})

def extend_xfs(self, lv_path):
"""
扩容 xfs文件系统

Args:
lv_path (str): LV的路径
"""

self.logger.info('extend xfs on %s' % lv_path)
self.run({"command": ['sh', '-c', 'xfs_growfs %s' % lv_path], "checkrc": 1})

def extend_gfs2(self, lv_path):
"""
扩容 gfs2文件系统

Args:
lv_path (str): LV的路径
"""

self.logger.info('extend gfs2 on %s' % lv_path)
self.run({"command": ['sh', '-c', 'gfs2_grow %s' % lv_path], "checkrc": 1})

def delete_files(self, file_path, free_space=None):
"""
删除指定目录下的文件，保留最后修改时间在24小时内的文件

Args:
file_path (str): file路径
free_space (str): 磁盘剩余空间,达到该值会触发删除文件的,如果不传则删除全部
"""

def transformSpaceSize(size):
result = None
if "g" == size[-1].lower():
result = int(size[:-1]) * 1024 * 1024 * 1024
elif "m" == size[-1].lower():
result = int(size[:-1]) * 1024 * 1024
elif "k" == size[-1].lower():
result = int(size[:-1]) * 1024
return result

if free_space:
now_time = time.time()
files_info = self.listFile(file_path, isModifyTimeStamp=True)
local_free_space = transformSpaceSize(self.getDiskSpace(path=file_path).values()[0].get('Avail'))
if local_free_space < transformSpaceSize(free_space):
self.logger.info("The space left of this disk is not enough, delete some file to release.")
for file in files_info:
timestamp = now_time - files_info[file].get('modifyTimeStamp')
if int(timestamp) > 86400:
cmd = ["sh", "-c", "rm", "-rf", file_path + file]
try:
self.run({"command": cmd, "timeout": 10})
except Exception as ex:
self.logger.error("Delete file fail: %s" % ex)
else:
self.logger.info('delete all file in %s' % file_path)
self.run({"command": ['sh', '-c', 'cd %s' % file_path]})
cmd = ["sh", "-c", "rm", "-rf", "*"]
self.run({"command": cmd,
"timeout": 3600})

def clear_fs(self, fs_type, lun, vg_name, lv_name, dir_path=None):
"""
基于清理文件系统

Args:
fs_type (str): 文件系统类型，ext3,ext4,xfs等
lun (PoolLun): lun component object
vg_name (str): vg name
lv_name (str): lv name
dir_path (str): mount的路径

"""
self.logger.info('获取%s的device' % fs_type)
disk_device = self.getDiskDeviceName(lun)
self.logger.info('清理%s创建的%s文件系统' % (vg_name, fs_type))
if fs_type in ['ext4', 'xfs']:
self.logger.info('umount %s文件系统' % fs_type)
self.run({"command": ["sh", "-c", "umount", "-l", dir_path],
'directory': '/root/'})
sleep(5)
self.logger.info('移除%s' % lv_name)
cmd = ['sh -c lvremove %s' % lv_name]
self.run({"command": cmd, "waitstr": "[y/n]:", "input": ["y", "~]#"], "timeout": 600})
self.logger.info('移除%s' % vg_name)
cmd = ['sh -c vgremove %s' % vg_name]
self.run({"command": cmd, "timeout": 600})
self.logger.info('移除%s' % disk_device)
self.run({"command": ["sh", "-c", "pvremove", disk_device]})

elif fs_type in ['gfs2']:
self.logger.info('umount %s文件系统' % fs_type)
self.run({"command": ["sh", "-c", "pcs resource delete gfs2_res"],
'directory': '/root/'})
sleep(5)
self.logger.info('移除%s' % lv_name)
cmd = ['sh -c lvremove %s' % lv_name]
self.run({"command": cmd, "waitstr": "[y/n]:", "input": ["y", "~]#"], "timeout": 600})
self.logger.info('移除%s' % vg_name)
cmd = ['sh -c vgremove %s' % vg_name]
self.run({"command": cmd, "timeout": 600})
self.logger.info('移除%s' % disk_device)
self.run({"command": ["sh", "-c", "pvremove", disk_device]})
else:
raise UniAutosException('the %s filesystem does not support creation' % fs_type)

def upgradeQuorumServer(self, ip, user, password, srcPath, destPath="/root/quorumServer/"):
"""
升级仲裁服务器

Args:
ip Type(str) : sftp服务器IP
user Type(str) : sftp服务器用户名
password Type(str) : sftp服务器密码
srcPath Type(str) : sftp服务器上的取包路径
destPath Type(str) : 控制器上存放从sftp服务器取下来的包的路径

"""
# 检查当前存放路径是否存在
temp = self.run({"command": ["sh -c cd %s" % destPath]})
if temp['stderr'] is not None and "-bash:" in temp['stderr']:
self.run({"command": ["sh -c mkdir -p %s" % destPath]})
# 获取包名
packageName = srcPath.split("/")[-1]
self.logger.info("current pakage is %s" % packageName)
# 切换当前目录到存放包的目录下
self.run({"command": ["sh -c cd %s" % destPath]})
# 从sftp服务器上获取包到当前目录下
self.logger.info("get package from sftp")
cmd = ["sh -c sftp %s@%s" % (user, ip)]
input = [password, "sftp>",
"get %s" % srcPath, "100%",
"quit", "#"]
self.run({"command": cmd,
"waitstr": "Password|password",
"input": input,
"timeout": 600})
# 解压升级
self.logger.info("start to upgrade quorumServer")
self.run({"command": ["sh -c unzip %s" % packageName]})
temp = self.run({"command": ["sh -c ls"]})
if "package" in temp['stdout']:
self.run({"command": ["sh -c cd package"]})
self.run({"command": ["sh -c ./quorum_server.sh -upgrade"],
"waitstr": "QuorumServer upgrade success completed",
"timeout": 600})
else:
raise UniAutosException('can not find dir named package')

# 清理当前环境
self.run({"command": ["sh -c cd %s" % destPath]})
self.run({"command": ["sh -c rm -f -R package"]})
self.run({"command": ["sh -c rm -f %s" % packageName]})

def upgrade_quorum_server_by_url(self, url, dest_path='/root/quorumServer/'):
"""
升级仲裁服务器

Args:
url Type(str) : 安装包url地址
dest_path Type(str) : 控制器上存放从sftp服务器取下来的包的路径

"""
# 检查当前存放路径是否存在
temp = self.run({"command": ["sh -c cd %s" % dest_path]})
if temp['stderr'] is not None and "-bash:" in temp['stderr']:
self.run({"command": ["sh -c mkdir -p %s" % dest_path]})
# 获取包名
packageName = url.split("/")[-1]
self.logger.info("current pakage is %s" % packageName)
# 切换当前目录到存放包的目录下
self.run({"command": ["sh -c cd %s" % dest_path]})
# 从sftp服务器上获取包到当前目录下
self.logger.info("get package from sftp")
cmd = ["sh -c wget %s" % url]
self.run({"command": cmd,
"timeout": 600})
# 解压升级
self.logger.info("start to upgrade quorumServer")
self.run({"command": ["sh -c unzip %s" % packageName]})
temp = self.run({"command": ["sh -c ls"]})
if "package" in temp['stdout']:
self.run({"command": ["sh -c cd package"]})
self.run({"command": ["sh -c ./quorum_server.sh -upgrade"],
"waitstr": "QuorumServer upgrade success completed",
"timeout": 600})
else:
raise UniAutosException('can not find dir named package')

# 清理当前环境
self.run({"command": ["sh -c cd %s" % dest_path]})
self.run({"command": ["sh -c rm -f -R package"]})
self.run({"command": ["sh -c rm -f %s" % packageName]})

def rescan_disk_dmp(self):
"""
扫描dmp接管的磁盘

"""
self.logger.info('扫描存储磁盘')
self.rescanDiskNoUltraPath()
self.run({"command": ["sh", "-c", "vxdisk scandisks"]})
self.run({"command": ["sh", "-c", "vxdctl -f enable"]})

def get_vxfs_disk_device(self, lunComponent):
"""获取指定Lun对象映射到主机的设备名称

Args:
lunComponent (instance | list): lun对象或者lun对象列表

Returns:
dmpdev (str|None): 映射的Lun对象的设备名称.

Raises:
CommandException: 命令执行失败.

"""
self.logger.info('获取%s在VXFS上的dmpdev' % lunComponent)
LunWwn = self.getLunWwn(lunComponent)
self.rescan_disk_dmp()
response = self.run(
{"command": ["sh", "-c", "vxdmpadm list dmpnode all | grep -E 'dmpdev|lun-sno' | cut -f 2 -d ' '"]})
if response["rc"] != 0 and not re.match(r'ls:\s+cannot\s+access\s+.*:\s+No\s+such\s+file\s+or\s+directory',
response["stderr"]):
raise CommandException(response["stderr"])

lines = re.compile(r'\S.*\r\n').findall(response['stdout'])
device_names = []
lun_wwns = []
lines_len = len(lines)
counts = range(0, lines_len)
for count in counts:
if count % 2 == 0:
device_name = lines[count].split('\r\n')[0]
device_names.append(device_name)
elif count % 2 == 1:
lun_wwn = lines[count].split('\r\n')[0]
lun_wwns.append(lun_wwn)
device_lun = dict(zip(lun_wwns, device_names))
new_LunWwn = LunWwn.upper()
dmpdev = device_lun[new_LunWwn]
return dmpdev

def create_lv_vxfs(self, dmpdev, dmpdg, dmplv, capacity):

"""获取指定参数创建lv

Args:
dmpdev (str|None): 映射的Lun对象的设备名称.
dmpdg (str|None): vg name
dmplv (str|None): lv name
capacity (str|None): lv capacity
Examples:
host.create_lv_vxfs(dmpdev, dmpdg, dmplv, '80g')

"""
self.logger.info('根据%s创建pv' % dmpdev)
self.run({"command": ["sh", "-c", "vxdisk", "init", dmpdev, "format=cdsdisk"], "checkrc": 1})
self.run({"command": ["sh", "-c", "/etc/vx/bin/vxdisksetup -i", dmpdev], "checkrc": 1})
self.logger.info('根据%s创建dg' % dmpdev)
self.run({"command": ["sh", "-c", "vxdg init", dmpdg, dmpdev], "checkrc": 1})
self.logger.info('根据%s创建lv' % dmpdg)
self.run({"command": ["sh", "-c", "vxassist -g", dmpdg, "make", dmplv, capacity], "checkrc": 1})

def create_vxfs(self, dmpdg, dmplv):
"""获取指定Lun对象映射到主机的设备名称

Args:
dmpdg (str|None): vg name
dmplv (str|None): lv name

"""
self.logger.info('根据%s创建vxfs文件系统' % dmplv)
lv_path = '/dev/vx/rdsk/%s/%s' % (dmpdg, dmplv)
self.run({"command": ["sh", "-c", "vxdg", "deport", dmpdg]})
self.run({"command": ["sh", "-c", "vxdg", "-s", "import", dmpdg]})
self.run({"command": ["sh", "-c", "vxvol", "-g", dmpdg, "startall"]})
cmd = ["sh", "-c", "mkfs", "-t", "vxfs", lv_path]
self.run({"command": cmd,
"timeout": 3600, "checkrc": 1})

def mount_vxfs(self, dmpdg, dmplv, dir_path):
"""获取指定Lun对象映射到主机的设备名称

Args:
dmpdg (str|None): vg name
dmplv (str|None): lv name
dir_path (str|None): 文件系统挂载点

"""
self.logger.info('以%s挂载文件系统' % dir_path)
cmd = ["sh", "-c", "/opt/VRTS/bin/cfsmntadm", "add", dmpdg, dmplv, dir_path, "all=cluster"]
self.run({"command": cmd,
"timeout": 3600, "checkrc": 1})
cmd = ["sh", "-c", "/opt/VRTS/bin/cfsmount", dir_path]
self.run({"command": cmd,
"timeout": 3600, "checkrc": 1})

def unmap_vxfs(self, dir_path):
"""获取指定Lun对象映射到主机的设备名称

Args:
dir_path (str|None): 文件系统挂载点

"""
self.logger.info('delete all file in %s' % dir_path)
self.run({"command": ['sh', '-c', 'cd %s' % dir_path]})
cmd = ["sh", "-c", "rm", "-rf", "*"]
self.run({"command": cmd,
"timeout": 3600})
self.logger.info('手动对%s进行空间回收' % dir_path)
cmd = ["sh", "-c", "/opt/VRTS/bin/fsadm", "-t", "vxfs", "-R", dir_path]
self.run({"command": cmd,
"timeout": 3600, "checkrc": 1})

def clear_vxfs(self, dmpdev, dmplv, dmpdg, dir_path):

"""获取指定Lun对象映射到主机的设备名称

Args:
dmpdev (str|None): 映射的Lun对象的设备名称.
dmpdg (str|None): vg name
dmplv (str|None): lv name
dir_path (str|None): 文件系统挂载点

"""
self.logger.info('清理文件系统')
cmd = ["sh", "-c", "/opt/VRTS/bin/cfsumount", dir_path]
self.run({"command": cmd, "timeout": 3600})
cmd = ["sh", "-c", "/opt/VRTS/bin/cfsmntadm", "delete", "-f", dir_path, "all=cluster"]
self.run({"command": cmd, "timeout": 3600})
self.run({"command": ['sh', '-c', 'vxassist', '-g', dmpdg, 'remove', 'volume', dmplv]})
self.run({"command": ['sh', '-c', 'vxdg', 'deport', dmpdg]})
self.run({"command": ['sh', '-c', '/etc/vx/bin/vxdiskunsetup', '-f', dmpdev]})

def extend_vxfs(self, dmpdev, dmpdg, dmplv, capacity):
"""获取指定Lun对象映射到主机的设备名称

Args:
dmpdev (str|None): 映射的Lun对象的设备名称.
dmpdg (str|None): vg name
dmplv (str|None): lv name
capacity (str|None): 扩容LV的大小
Examples:
host.extend_vxfs(dmpdev, dmpdg, dmplv, '80g')

"""
sleep(120)
self.logger.info('扩容文件系统')
self.run({"command": ['sh', '-c', 'vxdisk', '-f', '-g', dmpdg, 'resize', dmpdev]})
self.run({"command": ['sh', '-c', '/etc/vx/bin/vxresize', '-F', 'vxfs', '-g', dmpdg, dmplv, '+%s' % capacity],
"checkrc": 1})

def killProcess(self, process_id=None, process_name=None):
"""kill进程

Args:
process_id (str)： 进程ID，与名称参数二选一
process_name (str)： 进程名称
Raises:
CommandException: kill进程失败.

Examples:
self.host.killProcess('123456')
"""
process_id = process_id if process_id else self.getProcessId(process_name)[0]
response = self.run(
{"command": ["kill -9 {process_id}".format(process_id=process_id)]})
if response["rc"] != 0:
if "No such process" in response['stderr']:
# 兼容这种场景: 刚好在下发杀进程的时候，进程自己退出了
return response['stderr']
else:
raise CommandException("send command kill failed.")
return response["stdout"]

def getFcPortName(self):
"""获取FC的端口名称
:return:
"""
port_list = []
response = self.run({"command": ["sh", "-c", "cat", "/sys/class/fc_host/host*/port_name"]})
if response["rc"] != 0:
raise FileNotFoundException("Could not found the Open FC_host port_name file. ")
lines = self.split(self.trim(response["stdout"]))
for line in lines:
if re.search(r'cat|linux', line):
continue
match = re.findall(r'\w{12,20}', line)
port_list.extend(match)
return port_list

def start_keep_session(self, interval=60):
"""
保持Linux SSH连接

Changes:
l00355383 liruiqi Created 2019-5-17 11:36:25
"""
self.keep_session = True

def _repeat_get_date():
while self.keep_session:
self.run({"command": ['sh', '-c', 'date']})
sleep(interval)

th = threading.Thread(target=_repeat_get_date)
th.setDaemon(True)
th.start()

def stop_keep_session(self):
"""
停止保持Linux SSH连接

Changes:
l00355383 liruiqi Created 2019-5-17 11:36:25
"""
self.keep_session = False

def is_x86(self):
"""
判断是x86还是arm
Returns:
True表示x86
False表示arm或者其他
"""
ret = self.run({'command': ['sh', '-c', 'uname -a']})
if ret['stdout']:
if 'aarch64' in ret['stdout']: # arm
return False
return True
return True
