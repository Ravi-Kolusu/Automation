
# !/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能：windows操作系统的基类
"""

import re
import os
import struct
import threading
import time
import random
import tarfile
import sys

from Libs.HostBase import HostBase
from Libs.ftpClient import ftpClient
from Libs.Units import Units, SECOND
from Libs.Exception.CustomExceptions import CommandException
from Libs.Exception.CustomExceptions import FileNotFoundException
from Libs.Exception.CustomExceptions import InvalidParamException
from UniAutos.Component.Filesystem.FilesystemBase import FilesystemBase
from Libs.Exception.UniAutosException import UniAutosException
from Libs.TypeCheck import validateParam
from UniAutos.Component.Lun.LunBase import LunBase
from Libs.Time import sleep
from UniAutos.Device.Host.Hypervisor.Utilities import HyperVAlias as hyperv_alias


class Windows(HostBase):
    """Windows主机类, 继承于HostBase类

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
    self.iscsiCli (bool): 主机是否安装Iscsi, 默认为False; False: 未安装，True: 已安装.
    self.version (str): 操作系统内核版本.
    self.networkInfo (dict): 主机网络配置信息.

    Returns:
    Windows (instance): Windows主机对象实例.

    Raises:
    None.

    Examples:
    None.
    """
    def __init__(self, username, password, params):
        super(Windows, self).__init__(username, password, params)
        self.Lock = threading.Lock()
        self.os = 'Windows'
        self.iscsiCli = False
        self.version = None
        self.diskInitSemaphore = threading.Semaphore()

    def pingAddress(self, ipAddress):
        """Ping the special ip address
        """
        try:
            response = self.run({"command": ["cmd", "/c", "ping", ipAddress], "timeout": 8})
            if re.search(r'0% loss', str(response.get('stdout', '')).lower()):
                return True
            else:
                return False
        except:
            return False

    def which(self, program):
        """检查指定的程序是否安装，并返回安装的路径

        Args:
        program (str):　需要查询的程序名称.

        Returns:
        path (str): 程序的全路径.

        Raises:
        CommandException: 程序不存在时抛出异常.

        Examples:
        hostObj.which("iscsicli.exe")

        Notes:
        需要查询的程序的路径必须添加到环境变量Path中，否则无法查询.

        """
        response = self.run({"command": ["cmd", "/c", "for %%i in (%s) do @echo. %%~$PATH:i" % program]})
        if response["stdout"] is None:
            host = self.getHostname()
            raise CommandException("Program was not found in %s's \$PATH" % host)
        if response["stdout"] is not None and re.search(r'' + str(program) + '', response["stdout"], re.I):
            self.logger.debug('stdout %s' % response["stdout"])
            return self.trim(response["stdout"])

    def getHostname(self, domainFlag=False):
        """获取Windows主机名称

        Args:
        domainFlag (Boolean): 可选参数，默认值为False， 如果为False就不包含主机所在域的信息

        Returns:
        hostname (str): Windows主机名.

        Raises:
        CommandException: 无法找到域名.

        Examples:
        hostObj.getHostname()
        Output:
        >"Cuty1"

        """
        infoDict = self.getNetworkInfo()
        hostname = infoDict["hostname"]
        if not domainFlag:
            return hostname
        if "dns_domain" not in infoDict or infoDict["dns_domain"]:
            raise CommandException("Could not find the dns domain for this host. "
                                   "Make sure it is specified in the hosts OS.")
        hostname += "." + infoDict["dns_domain"]
        return hostname

    def getPath(self):
        """获取当前路径

        Args:
        None

        Returns:
        currentPath (str): 当前路径

        Raises:
        None

        Examples:
        None

        Changes:
        None

        """
        response = self.run({"command": ['cmd', '/c', "cd"]})
        if response["rc"] != 0:
            raise CommandException("Get Current Path Failed.")
        lines = self.split(response["stdout"])
        for line in lines:
            if re.search(r'>cd', line):
                continue
        currentPath = line
        return currentPath

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
        None

        Examples:
        None

        Changes:
        None
        """
        cmdDict = {"command": ['cmd', '/c', 'if exist "%s" echo 1' % params["path"]]}
        if "username" in params and "password" in params:
            cmdDict["username"] = params["username"]
            cmdDict["password"] = params["password"]
        response = self.run(cmdDict)
        if response["stdout"] and re.search("1", response["stdout"]):
            return True
        return False

    def findString(self, string, path):
        """查询指定文件中是否包含string，包含则返回文件内容列表.

        Args:
        string (str): 需要在文件中查询的字符串.
        path (str): 需要查询的文件.

        Returns:
        lines (list): 文件内容.

        Raises:
        None.

        Examples:
        None.
        """
        resp = self.run({'command': ['cmd', '/c', 'findstr /C:\"' + string + '\" ' + path]})
        lines = []
        if 'rc' in resp and not resp['rc']:
            lines = self.split(resp['stdout'])
        return lines

    def getNetworkInfo(self):
        """获取Windows主机的网络信息

        Args:
        None.

        Returns:
        self.networkInfo (dict): 主机网络信息, 键值对说明如下:
        {hostname (str): 主机名称.
        dns_domain (str): 域名.
        : {
        : {
        {gateway (str): 网关.
        netmask (str): 子网掩码.
        ipv4_address (str): ipv4地址.
        ipv6_address (str): ipv6_地址.}
        }}
        Raises:
        None.

        Examples:
        None.
        """
        parsingGw = 0
        if not self.networkInfo:
            resp = self.run({'command': ['cmd', '/c', 'ipconfig', '/all']})
            lines = self.split(resp['stdout'])
            self.networkInfo["interface"] = {}
            currentInterface = None
            for line in lines:
                matcher = re.match('^\s*Host Name.+: (\S+)|^\s*主机名\s*.+: (\S+)', line)
                if matcher:
                    self.networkInfo['hostname'] = matcher.group(1) if matcher.group(1) else matcher.group(2)
                    continue
                matcher = re.match('^\s*Primary Dns Suffix.+:\s*(\S+)|^\s*主 DNS 后缀\s*.+:\s*(\S+)', line)
                if matcher:
                    self.networkInfo['dns_domain'] = matcher.group(1) if matcher.group(1) else matcher.group(2)
                    continue
                matcherEth = re.match('^\s*Ethernet adapter (.+):|^\s*以太网适配器 (.+):', line)
                matcherWire = re.match('^\s*Wireless LAN adapter (.+):|^\s*无线网络适配器 (.+):', line)
                if matcherEth:
                    currentInterface = matcherEth.group(1) if matcherEth.group(1) else matcherEth.group(2)
                    continue
                elif matcherWire:
                    currentInterface = matcherWire.group(1) if matcherWire.group(1) else matcherWire.group(2)
                    continue
                matcher = re.match('^\s*IPv4 Address.+: (\d+\.\d+\.\d+\.\d+)|^\s*IPv4 地址.+: (\d+\.\d+\.\d+\.\d+)', line)
                if matcher and currentInterface:
                    if currentInterface not in self.networkInfo['interface']:
                        self.networkInfo['interface'][currentInterface] = {}
                    self.networkInfo['interface'][currentInterface]['ipv4_address'] = matcher.group(1) if matcher.group(1) else matcher.group(2)
                    continue
                matcher = re.match('^\s*.*IPv6 Address.+:\s+(.+)\(Preferred\)|^\s*.*IPv6 地址.+:\s+(.+)\(首选\)', line)
                if matcher and currentInterface:
                    if currentInterface not in self.networkInfo['interface']:
                        self.networkInfo['interface'][currentInterface] = {}
                    self.networkInfo['interface'][currentInterface]['ipv6_address'] = matcher.group(1) if matcher.group(1) else matcher.group(2)
                    continue

                matcher = re.match('^\s*Subnet Mask.+: (\S+)|^\s*子网掩码.+: (\S+)', line)
                if matcher and currentInterface:
                    if currentInterface not in self.networkInfo['interface']:
                        self.networkInfo['interface'][currentInterface] = {}
                    self.networkInfo['interface'][currentInterface]['netmask'] = matcher.group(1) if matcher.group(1) else matcher.group(2)
                    continue

                matcher = re.match('^\s*Default Gateway.+:\s*(\S+)|^\s*默认网关.+:\s*(\S+)', line)
                if (matcher and currentInterface) or parsingGw:
                    matcher = re.match('^\s*Default Gateway.+:\s*(\S*:\S+)|^\s*默认网关.+:\s*(\S*:\S+)', line)
                    if matcher:
                        parsingGw = 1
                    else:
                        matcher = re.search('(\d+\.\d+\.\d+\.\d+)', line)
                        if matcher:
                            if currentInterface not in self.networkInfo['interface']:
                                self.networkInfo['interface'][currentInterface] = {}
                            self.networkInfo['interface'][currentInterface]['gateway'] = matcher.group(1)
                            parsingGw = 0
                            continue

                        matcher = re.match('(\S*:\S+)', line)
                        if matcher:
                            continue
                        else:
                            parsingGw = 0
        return self.networkInfo

    def _checkIscsiCli(self):
        """检查主机是否安装iscsi

        Raises:
        FileNotFoundException: 未安装iscsi时抛出.

        Examples:
        hostObj._checkIscsiCli()

        """
        if not self.iscsiCli:
            if not self.which("iscsicli.exe"):
                raise FileNotFoundException("iSCSI Initiator not installed on this Host.")
        self.iscsiCli = True

    def rescanInitiator(self, ipv4Address=None):
        """iscsicli ListInitiators，扫描已经有的启动器

        Args:
        ipv4Address (str): ipv4地址

        Raises:
        CommandException: 命令执行失败.
        """
        self._checkIscsiCli()
        self.run({"command": ["cmd", "/c", "iscsicli ListInitiators"]})


    def getRegistry(self, key, value=None, recursive=None):
        """获取注册表信息

        Args:
        key (str): 需要查询的注册表全路径(key, 键).
        value (str): 注册表key指定的值.
        recursive (bool): 是否搜寻子节点, 默认为None.

        Returns:
        reg (list): 注册表信息列表, 列表元素为字典，键值对说明如下：
        key (str): 注册表键路径.
        value (str): 值的名称.
        type (str): 值的类型.
        data (str): 值的数据.

        Examples:
        hostObj.getRegistry("HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\iSCSI\Discovery")
        """
        regCmd = ["cmd", "/c", "reg", "query", key]
        if recursive:
            regCmd.append("/s")
        if value:
            regCmd.append("/v")
        types = "REG_SZ|REG_MULTI_SZ|REG_EXPAND_SZ|REG_DWORD|REG_BINARY|REG_NONE"
        reg = []
        response = self.run({"command": regCmd})
        if 0 == response["rc"]:
            lines = self.split(response["stdout"])
            for line in lines:
                keyPathMatch = re.search(r'(.+\\.+)', line)
                regExMatch = re.search(r'^\s{4}(.*)\s{4}(' + str(types) + ')\s{4}(.*)$', line)
                if keyPathMatch:
                    keyPath = keyPathMatch.group(1)
                elif regExMatch and "keyPath" in dir():
                    reg.append({"key": keyPath,
                                "value": regExMatch.group(1),
                                "type": regExMatch.group(2),
                                "data": regExMatch.group(3)})
        return reg

    def getIqn(self):
        """获取主机的ISCSI iqn信息

        Returns:
        iqn (str): 本主机的iqn信息.

        Raises:
        CommandException: 命令未查询到iqn信息.

        Examples:
        hostObj.getIqn()

        """
        regArr = self.getRegistry("HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\iSCSI\Discovery")
        for iqn in regArr:
            if iqn["value"] == "DefaultInitiatorName":
                return iqn["data"]
        self._checkIscsiCli()
        response = self.run({"command": ["cmd", "/c", "iscsicli"], "input": [" "]})
        iqn = {}
        if re.search(r'iqn', response["stdout"]):
            iqnMatch = re.search(r'\[(\S+)\]\s*输入命令或|\[(\S+)\]\s*Enter command or', response["stdout"])
            iqn = iqnMatch.group(1) if iqnMatch.group(1) else iqnMatch.group(2)
        if not iqn:
            raise CommandException("Cannot get the IQN for this host!")
        return iqn

    def getVersion(self):
        """获取操作系统内核版本

        Returns:
        self.version (str): 操作系统版本号.

        Examples:
        hostObj.getVersion()

        """
        if self.version:
            return self.version
        response = self.run({"command": ["cmd", "/c", "VER"]})
        if response["stdout"]:
            verMatch = re.search(r'\[Version\s*(\S+)\]|\[版本\s*(\S+)\]', response["stdout"])
            if verMatch:
                self.version = verMatch.group(1) if verMatch.group(1) else verMatch.group(2)
        return self.version

    def addTargetPortal(self, ip, port="3260", chapUser=None, chapPassword=None, headerDigest=None, dataDigest=None):
        """添加ISCSI Target Portal

        iscsi目标器的ip地址和端口，通过该入口门户，发现映射的Lun.

        Args:
        ip (str): 目标器入口ip地址.
        port (str): 目标器入口端口, 默认为3260.
        chapUser (str): chap认证的用户名, 目标器配置了chap认证时使用, 默认为None.
        chapPassword (str): chap认证的密码, 默认为None.
        headerDigest (bool): headerDigest非零时, 以指示该target应使用header digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。
        dataDigest (bool): dataDigest非零时, 以指示该target应使用data digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。

        Raises:
        InvalidParamException: 操作系统版本小于5.0时, 使用了错误的参数.

        Examples:
        hostObj.addTargetPortal(ip="100.10.10.125")

        """
        osVersion = self.getVersion()
        tmpOsVerMatch = re.match(r'^(\d+.+\d+)\.', osVersion)
        ver = 0
        if tmpOsVerMatch:
            ver = tmpOsVerMatch.group(1)
        # 5.0 is Win2K. According to the document, addTargetPortal is supported after/including 5.0 .
        if 5.0 > float(ver):
            if headerDigest or dataDigest or port:
                raise InvalidParamException("Digest and port options are not "
                                            "supported by this Windows version.")
        else:
            self._qAddTargetPortal(ip, chapUser, chapPassword)
        self._addTargetPortal(ip, port, chapUser, chapPassword, headerDigest, dataDigest)

    def _qAddTargetPortal(self, ip, chapUser=None, chapPassword=None):
        """操作系统版本小于5.0时使用该接口添加Target Portal

        Args:
        ip (str): 目标器入口ip地址.
        chapUser (str): chap认证的用户名, 目标器配置了chap认证时使用, 默认为None.
        chapPassword (str): chap认证的密码, 默认为None.

        Raises:
        CommandException: 添加Target Portal失败时抛出.

        Examples:
        hostObj._qAddTargetPortal("100.125.140.10")

        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "QAddTargetPortal", ip]
        if chapUser and chapPassword:
            cmd.extend([chapUser, chapPassword])
        response = self.run({"command": cmd})
        if response["rc"] != 0:
            raise CommandException("Add Target Portal Failed.")

    def _addTargetPortal(self, ip, port="3260", chapUser=None, chapPassword=None, headerDigest=None, dataDigest=None):
        """操作系统版本大于等于5.0时使用该接口添加Target Portal

        iscsi目标器的ip地址和端口，通过该入口门户，发现映射的Lun.

        Args:
        ip (str): 目标器入口ip地址.
        port (str): 目标器入口端口, 默认为3260.
        chapUser (str): chap认证的用户名, 目标器配置了chap认证时使用, 默认为None.
        chapPassword (str): chap认证的密码, 默认为None.
        headerDigest (bool): headerDigest非零时, 以指示该target应使用header digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。
        dataDigest (bool): dataDigest非零时, 以指示该target应使用data digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。

        Raises:
        CommandException: 添加Target Portal失败时抛出.

        Examples:
        hostObj.addTargetPortal("100.10.10.125")

        """
        self._checkIscsiCli()
        if headerDigest is None:
            headerDigest = "*"
        if dataDigest is None:
            dataDigest = "*"
        cmd = ["cmd", "/c", "iscsicli", "AddTargetPortal", ip, port, "*", "*", "*", "2", headerDigest, dataDigest, "*",
               "*", "*"]
        if chapPassword and chapUser:
            cmd.extend([chapUser, chapPassword, "1"])
        else:
            cmd.extend(["*", "*", "*"])
        response = self.run({"command": cmd})
        if response["rc"] != 0:
            raise CommandException("Add Target Portal Failed.")

    def _service(self, name, action):
        """处理服务操作

        Args:
        name (str): 服务名称.
        action (str): 服务操作, 取值范围为: query|start|stop

        Raises:
        InvalidParamException: action非法.

        Examples:
        self._service("Automatos RPC Service (C#)", "status")

        """
        if re.match(r'query|start|stop', action) is None:
            raise InvalidParamException("Service action input Failed.")
        cmd = "cmd /c net"
        if action.lower() == "query":
            cmd = "cmd /c sc"
        response = self.run({"command": [cmd, action, name]})
        if response["rc"] != 0:
            raise CommandException("Service %s %s Failed" % (name, action))
        if action.lower() == "query":
            if re.search(r'STOPPED', response["stdout"]):
                return "stopped"
        if re.search(r'RUNNING', response["stdout"]):
            return "running"

    def startService(self, name):
        """打开指定服务

        Args:
        name (str): 服务名称.

        Returns:
        None.

        Raises:
        CommandException: 命令执行失败.

        Examples:
        hostObj.startService("SCardSvr")

        """
        self._service(name, "start")

    def stopService(self, name):
        """停止指定服务

        Args:
        name (str): 服务名称.

        Returns:
        None.

        Raises:
        CommandException: 命令执行失败.

        Examples:
        hostObj.stopService("SCardSvr")

        """
        self._service(name, "stop")

    def getServiceStatus(self, name):
        """获取指定Windows操作系统的服务状态

        Args:
        name (str): 服务名称.

        Returns:
        status (str): 服务状态信息， 返回值为"running"或"stopped".

        Raises:
        CommandException: 命令执行失败.

        Examples:
        hostObj.getServiceStatus("RPC")
        Output:
        >"running"

        """
        return self._service(name, "query")

    def getTargets(self):
        """获取主机的Target

        Args:
        None.

        Returns:
        targetDict (dict): 所有target信息， key为target， value为ip列表.

        Raises:
        None.

        Examples:
        hostObj.getTargets()

        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "ListTargets", "true"]
        response = self.run({"command": cmd})
        targets = []
        lines = self.split(response["stdout"])
        startRecording = 0
        for line in lines:
            if re.match(r'^The operation|操作成功完成', line):
                break
            elif re.match(r'^Targets List:|目标列表:', line):
                startRecording = 1
            elif re.search(r'(\S+)', line) and startRecording == 1:
                targets.append(re.search(r'(\S+)', line).group(1))
        targetDict = {}
        for target in targets:
            cmd = ["cmd", "/c", "iscsicli", "targetinfo", target]
            response = self.run({"command": cmd})
            lines = self.split(response["stdout"])
            startRecording = 0
            for line in lines:
                targetMatch = re.search(r'\"\S+\*(\S+) ', line)
                if targetMatch:
                    if target in targetDict:
                        targetDict[target].append(targetMatch.group(1))
                    else:
                        targetDict[target] = [targetMatch.group(1)]
        return targetDict

    def targetLogin(self, targetIqn, targetPortal, port="3260", chapUser=None, chapPassword=None,
                    headerDigest=None, dataDigest=None):
        """目标器登陆

        Args:
        targetIqn (str): target名称.
        targetPortal (str): 目标器入口ip地址.
        port (str): 目标器入口端口, 默认为3260.
        chapUser (str): chap认证的用户名, 目标器配置了chap认证时使用, 默认为None.
        chapPassword (str): chap认证的密码, 默认为None.
        headerDigest (bool): headerDigest非零时, 以指示该target应使用header digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。
        dataDigest (bool): dataDigest非零时, 以指示该target应使用data digest登录到目标器。
        -默认为None, 为None时用"*"替代, 此时将由启动内核模式驱动器来确定。

        Returns:
        None.

        Raises:
        InvalidParamException: 输入的target不存在时抛出.

        Examples:
        hostObj.targetLogin("iqn.1991-05.com.microsoft:ctu1000006554-testtarget-target", "10.183.125.234")
        """
        if headerDigest is None:
            headerDigest = "*"
        if dataDigest is None:
            dataDigest = "*"
        targets = self.getTargets()
        if targetIqn not in targets:
            raise InvalidParamException("Could not find the Target %s on this host." % targetIqn)
        sessionIds = []
        for tmpTargetPortal in targets[targetIqn]:
            if targetPortal and targetPortal != tmpTargetPortal:
                continue
            cmd = ["cmd", "/c", "iscsicli", "LoginTarget", targetIqn, "T", targetPortal,
                   port, "*", "*", "*", "2", headerDigest, dataDigest, "*", "*", "*"]
            if chapPassword and chapUser:
                cmd.extend([chapUser, chapPassword, "1", "*", "*"])
            else:
                cmd.extend(["*", "*", "*", "*", "*"])
            response = self.run({"command": cmd})
            lines = self.split(response["stdout"])
            for line in lines:
                if re.match(r'^The operation|操作成功完成', line):
                    break
                elif re.search(r'Session Id is 0x(\S+)|会话 ID 是 0x(\S+)', line):
                    match = re.search(r'Session Id is 0x(\S+)|会话 ID 是 0x(\S+)', line)
                    sessionID = match.group(1) if match.group(1) else match.group(2)
                    sessionIds.append(sessionID)
        return {"session_ids": sessionIds}

    def getSessionMappings(self):
        """获取所有会话的映射关系

        使用该方法来得到SCSI Device/Bus/Target_id/LUN Information.

        Args:
        None.

        Returns:
        sessionMaps (dict): 包含如下key和value的iscsi映射数据:
        {"session_ids": {"target": (str) # 目标器的Iqn, eg: "iqn.1991-05.com.microsoft:ctu1000006554-test01-target"
        "initiator": (str) # eg: "ROOT\\ISCSIPRT\\0000_0"
        "portal": (str) # 目标器的Ip, eg: "10.183.125.234"
        "scsi_device": (str) # eg: "\\\\.\\Scsi5:"
        "scsi_bus": (str) # eg: "0"
        "scsi_target_id" (str) # eg: "1"
        "luns": {target_lun: OS Lun} # eg: {"0": "0", "100": "1"}
        }}

        Raises:
        None.

        Examples:
        hostObj.getSessionMappings()
        Output:
        >{'ffffffff89c1346c-400001370000002e': {'initiator': 'ROOT\\ISCSIPRT\\0000_0',
        'luns': {'0': '0', '100': '1'},
        'portal': '10.183.125.234',
        'scsi_bus': '0',
        'scsi_device': '\\\\.\\Scsi5:',
        'scsi_target_id': '1',
        'target': 'iqn.1991-05.com.microsoft:ctu1000006554-test01-target'}}
        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "reporttargetmappings"]
        response = self.run({"command": cmd})
        sessionMaps = {}
        lines = self.split(response["stdout"])
        curSession = None
        for line in lines:
            if re.match(r'^The operation|操作成功完成', line):
                break
            sessionMatch = re.search(r'Session Id\s*:\s*(\S+)|会话 ID\s*:\s*(\S+)', line)
            if sessionMatch:
                curSession = sessionMatch.group(1) if sessionMatch.group(1) else sessionMatch.group(2)
                sessionMaps[curSession] = {}
                continue
            targetNameMatch = re.search(r'Target Name\s*:\s*(.+)|目标名称\s*:\s*(.+)', line)
            if targetNameMatch:
                sessionMaps[curSession]["target"] = targetNameMatch.group(1) if targetNameMatch.group(1) else targetNameMatch.group(2)
                continue
            initiatorMatch = re.search(r'Initiator\s*:\s*(.+)|发起程序\s*:\s*(.+)', line)
            if initiatorMatch:
                sessionMaps[curSession]["initiator"] = initiatorMatch.group(1) if initiatorMatch.group(1) else initiatorMatch.group(2)
                continue
            scsiDeviceMatch = re.search(r'Initiator Scsi Device\s*:\s*(.+)|发起程序 SCSI 设备\s*:\s*(.+)', line)
            if scsiDeviceMatch:
                sessionMaps[curSession]["scsi_device"] = scsiDeviceMatch.group(1) if scsiDeviceMatch.group(1) else scsiDeviceMatch.group(2)
                continue
            scsiBusMatch = re.search(r'Initiator Bus\s*:\s*(.+)|发起程序总线\s*:\s*(.+)', line)
            if scsiBusMatch:
                sessionMaps[curSession]["scsi_bus"] = scsiBusMatch.group(1) if scsiBusMatch.group(1) else scsiBusMatch.group(2)
                continue
            scsiTargetIdMatch = re.search(r'Initiator Target Id\s*:\s*(.+)|发起程序目标 ID\s*:\s*(.+)', line)
            if scsiTargetIdMatch:
                sessionMaps[curSession]["scsi_target_id"] = scsiTargetIdMatch.group(1) if scsiTargetIdMatch.group(1) else scsiTargetIdMatch.group(2)
                continue

            lunMatch = re.search(r'Target Lun\s*:\s*0x(\S+) OS Lun\s*:\s*0x(\S+)'r'|目标 Lun\s*:\s*0x(\S+) OS Lun\s*:\s*0x(\S+)', line)
            if lunMatch:
                tmpTargetLun = lunMatch.group(1) if lunMatch.group(1) else lunMatch.group(3)
                tmpOsLun = lunMatch.group(2) if lunMatch.group(2) else lunMatch.group(4)
                if "luns" in sessionMaps[curSession]:
                    sessionMaps[curSession]["luns"].update({tmpTargetLun: tmpOsLun})
                else:
                    sessionMaps[curSession]["luns"] = {tmpTargetLun: tmpOsLun}
                continue
        for sessionId in sessionMaps:
            cmd = ["cmd", "/c", "iscsicli", "sessionlist"]
            response = self.run({"command": cmd})
            startLooking = 0
            lines = self.split(response["stdout"])
            curSession = None
            for line in lines:
                if re.search(r'Session Id\s+:\s+' + str(sessionId) + '|会话 ID\s+:\s+' + str(sessionId) + '', line):
                    startLooking = 1
                targetMatch = re.search(r'Target Portal\s+:\s+(\S+)\/|目标门户\s+:\s+(\S+)\/', line)
                if targetMatch and startLooking == 1:
                    sessionMaps[sessionId]["portal"] = targetMatch.group(1) if targetMatch.group(1) else targetMatch.group(2)
                    break
        return sessionMaps

    def sessionLogout(self, sessionId):
        """注销特定目标器会话

        Args:
        sessionId (str): 目标器的会话ID, 如: "ffffffff89c1346c-400001370000002e"

        Returns:
        None.

        Raises:
        CommandException: 注销会话失败时抛出.

        Examples:
        hostObj.sessionLogout("ffffffff89c1346c-400001370000002e")
        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "logouttarget", sessionId]
        response = self.run({"command": cmd})
        if response["rc"] != 0:
            raise CommandException("Session %s logout failed." % sessionId)
        self.logger.debug("Session % logout Success." % sessionId)

    def getTargetPortal(self):
        """获取主机的所有Target Portal信息

        Args:
        None.

        Returns:
        targetInfo (dict): 主机上添加的target portal信息， 格式如下:
        {target_portal_ip (str): {"socket": socket (str)}
        eg:
        {'10.120.10.10': {'socket': '3260'},
        '10.183.125.234': {'socket': '3260'}}
        Raises:
        None.

        Examples:
        hostObj.getTargetPortal()
        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "ListTargetPortals"]
        response = self.run({"command": cmd})
        targetInfo = {}
        lines = self.split(response["stdout"])
        for line in lines:
            if re.match(r'^The operation|操作成功完成', line):
                break
            targetMatch = re.search(r'Address and Socket\s*:\s*(\S+)\s+(\S+)|地址和套接字\s*:\s*(\S+)\s+(\S+)', line)
            if targetMatch:
                ip = targetMatch.group(1) if targetMatch.group(1) else targetMatch.group(3)
                port = targetMatch.group(2) if targetMatch.group(2) else targetMatch.group(4)
                targetInfo[ip] = {"socket": port}
        return targetInfo

    def removeTargetPortal(self, ip, socket):
        """从主机的iSCSI配置中移除一个Target Portal

        Args:
        ip (str): target portal的Ip, 如："10.120.10.10".
        socket (str): target portal的端口, 如: "3260".

        Returns:
        None.

        Raises:
        None.

        Examples:
        hostObj.removeTargetPortal("10.120.10.10", "3260")
        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "RemoveTArgetPortal", ip, socket]
        response = self.run({"command": cmd})
        if response["rc"] != 0:
            self.logger.debug("Remove Target Portal %s:%s Failed. " % (ip, socket))
        else:
            self.logger.info("Remove Target Portal %s:%s Success. " % (ip, socket))

    def rescanIscsiTargets(self):
        """重新扫描主机上的Target, 更新主机的Target列表

        Args:
        None.

        Returns:
        None.

        Raises:
        None.

        Examples:
        hostObj.rescanIscsiTargets()
        """
        self._checkIscsiCli()
        cmd = ["cmd", "/c", "iscsicli", "ListTargets", "true"]
        self.run({"command": cmd})
        return

    def reboot(self, delay, wait=False, timeout=None):
        """
        """
        if Units.isTime(delay):
            delay = Units.getNumber(Units.convert(delay, SECOND))
        else:
            raise InvalidParamException("Delay %s is not time string. " % delay)
        rebootCmd = ["cmd", "/c", "shutdown", "/R", "/F", "/T", delay]
        response = self.run({"command": rebootCmd})
        # self.baseEnvironment = self._makeEnvironmentDict()
        if wait and timeout:
            self.waitForReboot(wait, timeout)

    def _makeEnvironmentDict(self):
        pass

    def shutdown(self):
        """
        """
        cmd = ["cmd", "/c", "shutdown", "/s", "/f", "/t 0"]
        th = threading.Thread(target=self.run, name="reboot", kwargs={"command": cmd})
        th.start()
        time.sleep(10)

    def createFilesystem(self, mount, filesystem="NTFS", quick=True, unitSize=None):
        """"""
        if len(mount) == 1:
            mount += ":"
        elif re.search(r'\s', mount):
            raise InvalidParamException("You cannot format to a path with spaces."
                                        "\nFor Example:\nGood: C:\\LunMounts\\1 \nBad: C:\\Lun Mounts\\1")
        self.logger.debug("Formatting mount: %s" % mount)
        cmd = "format %s /FS:%s /X /V:UniAuto " % (mount, filesystem)
        if unitSize and Units.isSize(unitSize) and re.match(r'^\d+B$', unitSize):
            unitSize = re.sub(r'B', "", unitSize)
            cmd += "/A:%s" % unitSize
        if quick:
            cmd += "/Q"
        response = self.run({"command": ["cmd", "/c", cmd], "input": ["y\r", ]})
        if response["rc"] != 0:
            raise CommandException("Formatting partition %s failed" % mount)

    def _getDiskNumber(self, lunComponent):
        """获取Lun映射给主机后的磁盘编号

        通过Lun对象获取Lun的id和阵列的SN, SN + lunId即为Lun在主机上的磁盘的SerialNumber, 通过SerialNumber可获取磁盘信息.

        Args:
        lunComponent (instance): Lun实例对象.

        Returns:
        diskNumber (str): Windows主机中对象Lun对象的磁盘编号, 不包含"PHYSICALDISK"前缀.

        Raises:
        CommandException: 获取磁盘编号失败.

        Examples:
        None.
        """
        response = self.run({"command": ["cmd", "/c", "wmic", "diskdrive", "GET", "SerialNumber,DEVICEID"]})
        if response["rc"] != 0:
            raise CommandException("Get Disk Number Failed, \n Error:\n%s" % response["stderr"])
        # 定义获取deviceName的方法
        def getDiskDeviceForLun(lun):
            if not isinstance(lun, LunBase):
                raise InvalidParamException("%s is not a Lun Component. ")
            lunId = str(lun.getProperty("id"))
            sn = str(lun.owningDevice.SN)
            wwn = str(lun.getProperty("wwn"))[16:]
            lunSnNumber = str(sn + (24 - len(sn) - len(lunId)) * '0' + lunId)
            compileString = re.compile(r'PHYSICALDRIVE(\S+)\s+(' + lunSnNumber + '|' + wwn + ')' + '')
            diskNumber = re.search(compileString, response["stdout"])
            if diskNumber is not None:
                return diskNumber.group(1)
            else:
                raise CommandException("Get DeviceID Failed ")
        # 添加传入list的场景，避免多次下发命令。
        if isinstance(lunComponent, list):
            result = []
            for lun in lunComponent:
                deviceName = getDiskDeviceForLun(lun)
                result.append(deviceName)
            return result
        # 传入单个lun对象时， 返回单个的对象
        elif isinstance(lunComponent, LunBase):
            deviceName = getDiskDeviceForLun(lunComponent)
            return deviceName
        else:
            raise InvalidParamException("%s is not a Lun Component. ")

    def writeToFile(self, path, line, append=True):
        """写一行数据到指定的文件

        Args:
        path (str): 文件全路径，包含文件名.
        line (str): 需要写入的字符串, 注：特殊字符无法写入，需要进过替换后写入.
        append (bool): 是否追加，True时为追加到文件末尾，False时为覆盖写.

        Returns:
        None.

        Raise:
        None.

        Examples:
        None.
        """
        re.sub(r'([\|\^\&\?\\"\'])', "\^", line)  # todo
        if not append:
            self.run({"command": ["cmd", "/c", "echo %s > %s" % (line, path)]})
        self.run({"command": ["cmd", "/c", "echo %s >> %s" % (line, path)]})

    @staticmethod
    def _buildDiskPartInput(cmd):
        """生成DiskPart命令的交互输入字符串

        Args:
        cmd (list): 需要交互输入的命令列表.

        Returns:
        string (str): cmd格式化后的字符串，可供run函数执行DiskPart交互执行.

        Raise:
        None.

        Examples:
        None.
        """
        return "\r".join(cmd) + "\r exit \r"

    def _buildDiskPartInputScript(self, cmdList):
        """生成DiskPart脚本文件

        该接口暂未使用, 默认生成的脚本文件在当前目录下，文件名为: "diskPartCmd.txt", DiskPart的调用方式为: "diskpart /s path".

        Args:
        cmdList (list): 命令列表.

        Returns:
        filePath (str): diskPartCmd.txt文件全路径.

        Raises:
        None.

        Examples:
        None.
        """
        self.logger.info(str(cmdList))
        filePath = self.getPath() + "\\diskPartCmd.txt"
        self.createFile(filePath)
        for cmd in cmdList:
            self.writeToFile(filePath, cmd)
        return filePath

    def _deleteDiskPartInputScript(self, scriptFile):
        """删除DiskPart脚本文件

        该接口暂未使用, 默认生成的脚本文件在当前目录下，文件名为: "diskPartCmd.txt".

        Args:
        scriptFile (str): diskPartCmd.txt文件全路径.

        Returns:
        None.

        Raises:
        None.

        Examples:
        None.
        """
        if self.doesPathExist({"path": scriptFile}):
            self.deleteFile(scriptFile)
        return

    def deleteFile(self, filePath):
        """删除指定的文件

        Args:
        filePath (str): 需要删除的文件全路径, 注: "C:\del.txt" 中"\d"会被转义, 需要写为: "c:\\del.txt", 其他情况类似.

        Returns:
        None.

        Raises：
        CommandException:　命令执行失败.

        Examples:
        None.

        """
        if not self.doesPathExist({"path": filePath}):
            return
        response = self.run({"command": ["cmd", "/c", 'del "%s" /F/Q' % filePath]})
        if response["rc"] != 0:
            raise CommandException("Unable to delete %s" % filePath)

    def deleteDir(self, dirPath):
        """删除指定的文件夹

        Args:
        dirPath (str): 需要文件夹全路径

        Returns:
        None.

        Raises：
        CommandException:　命令执行失败.

        Examples:
        None.
        """
        if not self.doesPathExist({"path": dirPath}):
            return
        response = self.run({"command": ["cmd", "/c", 'rd "%s" /S/Q' % dirPath]})
        if response["rc"] != 0 or response['stderr'] is not None:
            raise CommandException("Unable to delete %s\nerror message:%s"
                                   % (dirPath, response['stderr']))

    def createFile(self, filePath, username=None, password=None):
        """创建指定的文件

        Args:
        filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.

        Returns:
        None.

        Raises:
        CommandException: 创建文件失败.

        Examples:
        hostObj.createFile("C:\\root\\1.txt")
        """
        cmd = {"command": ["cmd", "/c", "type nul >> %s" % filePath]}
        pathExitParams = {"path": filePath}
        if (username is None and password is not None) or (username is not None and password is None):
            raise InvalidParamException("username and password must be depends.")
        if username and password:
            cmd.update({"username": username, "password": password})
            pathExitParams.update({"username": username, "password": password})
        response = self.run(cmd)
        if response["rc"] != 0 or not self.doesPathExist(pathExitParams):
            raise CommandException("Unable to create given file: %s" % filePath)

    def getPartitions(self, lunComponent=None, disk=None, raw=False):
        """获取分区信息

        Args:
        lunComponent (instance): Lun实例对象，lunComponent和disk都未指定时获取全部分区.
        disk (str): 磁盘名称或磁盘编号, 如: "\\.\PHYSICALDRIVE0", 特殊字符需要转义.
        raw (bool): 是否只获取文件系统类型为raw的分区, True为只获取raw分区，False获取全部.

        Returns:
        volumeArray (list): 分区列表.

        Raises:
        None.

        Examples:
        hostObj.getPartition()
        Output:
        >[{"size": "59 GB", "status": "Healthy", "fs": "NTFS",
        "letter": "C", "mounts": [], "info": "Boot",
        "partition": "2", "type": "Partition", "label": null},
        {"size": "89 GB", "status": "Healthy", "fs": "NTFS",
        "letter": "D", "mounts": [], "info": null,
        "partition": "3", "type": "Partition", "label": "aaaaaaaaaaa"}]
        """
        if lunComponent:
            disk = self._getDiskNumber(lunComponent)
        diskPartCmd = []
        if disk:
            disk = self._extractDiskNumber(disk)
            diskPartCmd.append("select disk %s" % disk)
            diskPartCmd.append("detail disk")
        else:
            diskPartCmd.append("list volume")
        inputScript = self._buildDiskPartInput(diskPartCmd)
        # todo lock
        response = self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputScript]})
        if re.search(r'卷', response["stdout"]):
            return self._getCnVolume(response["stdout"], raw)
        return self._getVolumeArray(response["stdout"], raw)

    @staticmethod
    def _extractDiskNumber(diskName):
        """获取指定磁盘的磁盘编号

        Args:
        diskName (str): 磁盘名称包含磁盘编号, 如: "\\.\PHYSICALDRIVE0", 特殊字符需要转义.

        Returns:
        diskNumber (str): 磁盘编号, 如: "\\.\PHYSICALDRIVE0" 后的"0".

        Raises:
        InvalidParamException: 输入的磁盘名称为非磁盘格式的.

        Examples:
        None.
        """
        diskNameMatch = re.match(r'\D*(\d+)', diskName)
        if diskNameMatch:
            return diskNameMatch.group(1)
        else:
            raise InvalidParamException("Couldn't extract drive # from: %s" % diskName)

    def _getVolumeArray(self, diskPartOutPut, raw=False):
        """从DiskPart命令的输出中解析分区信息

        Args:
        diskPartOutPut (str): DiskPart命令的输出信息.
        raw (bool): 是否只获取文件系统类型为raw的分区, True为只获取raw分区，False获取全部.

        Returns:
        volumeArray (list): 分区列表.

        Raises:
        None.

        Examples:
        hostObj.getPartition()
        Output:
        >[{"size": "59 GB", "status": "Healthy", "fs": "NTFS",
        "letter": "C", "mounts": [], "info": "Boot",
        "partition": "2", "type": "Partition", "label": null},
        {"size": "89 GB", "status": "Healthy", "fs": "NTFS",
        "letter": "D", "mounts": [], "info": null,
        "partition": "3", "type": "Partition", "label": "aaaaaaaaaaa"}]

        Notes:
        该函数只能处理英文windows操作系统.
        """
        currentVol, values, volumeArray = None, None, []
        lines = self.split(diskPartOutPut)
        fmt = "2x 10s 2x 3s 2x 11s 2x 5s 2x 10s 2x 7s 2x 9s 2x 8s"
        for line in lines:
            if len(line) < 79:
                line += ((79 - len(line)) * " ")
            infoTuple = struct.unpack(fmt, line)
            if re.search(r'[A-Z][:].+\\.+', line) and currentVol:
                # todo mount
                pass
            elif infoTuple:
                (partition, letter, label, fs, types, size, status, info) = infoTuple
                partitionMatch = re.search(r'Volume (\d+)', partition, re.I)
                if partitionMatch is None:
                    continue
                partition = partitionMatch.group(1)
                if re.search(r'system', info, re.I):
                    continue
                if re.search(r'healthy|rebuild', status, re.I) is None or re.search(r'removable', types, re.I):
                    continue
                if re.search(r'raw', fs, re.I) is None and raw:
                    continue
                currentVol = partition
                tmpInfo = {"partition": partition,
                           "letter": letter,
                           "label": label,
                           "fs": fs,
                           "type": types,
                           "size": size,
                           "status": status,
                           "info": info,
                           "mounts": []}
                for key in tmpInfo:
                    if isinstance(tmpInfo[key], list):
                        continue
                    elif "" == self.trim(tmpInfo[key]):
                        tmpInfo[key] = None
                    else:
                        tmpInfo[key] = self.trim(tmpInfo[key])
                volumeArray.append(tmpInfo)
        return volumeArray

    def _getCnVolume(self, diskPartOutPut, raw):
        """从DiskPart命令的输出中解析分区信息

        Args:
        diskPartOutPut (str): DiskPart命令的输出信息.
        raw (bool): 是否只获取文件系统类型为raw的分区, True为只获取raw分区，False获取全部.

        Returns:
        volumeArray (list): 分区列表.

        Raises:
        None.

        Examples:
        hostObj.getPartition()
        Output:
        >[{"size": "89 GB", "status": "正常", "fs": "NTFS",
        "letter": "D", "mounts": [], "info": null,
        "partition": "0", "type": "简单", "label": null},
        {"size": "59 GB", "status": "正常", "fs": "NTFS",
        "letter": "C", "mounts": [], "info": "启动",
        "partition": "3", "type": "磁盘分区", "label": null},
        {"size": "9 GB", "status": "正常", "fs": "RAW",
        "letter": "F", "mounts": [], "info": null,
        "partition": "4", "type": "磁盘分区", "label": null}]
        Notes:
        该函数处理中文Windows系统DiskPart输出.

        """
        currentVol, values, volumeArray = None, None, []
        lines = self.split(diskPartOutPut)
        for line in lines:
            if len(unicode(line, "utf-8")) < 79:
                line += ((79 - len(unicode(line, "utf-8"))) * " ")
            if re.search(r'[A-Z][:].+\\.+', line) and currentVol:
                # todo mount
                pass
            match = re.match(r'^\s{2}(.{9})\s{2}(.{3})\s{2}(.{11})\s{2}(.{5})\s{2}'
                         r'(.{10})\s{2}(.{7})\s{2}(.{9})\s{2}(.{8})', unicode(line, "utf-8"))
            # match = re.match(r'^\s{2}(.{10})\s{2}(.{3})\s{2}(.{11})\s{2}(.{5})'
            # r'\s{2}(.{10})\s{2}(.{7})\s{2}(.{9})\s{2}(.{8})', line) # match english
            if match:
                (partition, letter, label, fs, types, size, status, info) = match.groups()
                partitionMatch = re.search(ur'卷\s+(\d+)', partition, re.I)
                if partitionMatch is None:
                    continue
                partition = partitionMatch.group(1)
                if re.search(ur'系统', info, re.I):
                    continue
                if re.search(ur'正常|rebuild', status, re.I) is None or re.search(r'removable', types, re.I):
                    continue
                if re.search(ur'raw', fs, re.I) is None and raw:
                    continue
                currentVol = partition
                tmpInfo = {"partition": partition,
                           "letter": letter,
                           "label": label,
                           "fs": fs,
                           "type": types,
                           "size": size,
                           "status": status,
                           "info": info,
                           "mounts": []}
                for key in tmpInfo:
                    if isinstance(tmpInfo[key], list):
                        continue
                    elif "" == self.trim(tmpInfo[key]):
                        tmpInfo[key] = None
                    else:
                        tmpInfo[key] = self.trim(tmpInfo[key])
                volumeArray.append(tmpInfo)
        return volumeArray

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

    def rescanDisk(self):
        """重新扫描映射的LUN

        Examples:
        hostObj.rescanDisk()
        """
        diskPartCmd = []
        cmd = "rescan"
        diskPartCmd.append(cmd)
        inputCmd = self._buildDiskPartInput(diskPartCmd)
        # todo lock
        self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})

    def rescanDiskNoUltraPath(self, onlineDiskId=None):
        """不安装华为自研多路径的情况下重新扫描映射的LUN

        Args:
        onlineDiskId type(list ,int):需要将状态更改为Online的disk id，默认更改所有disk状态为Online

        Example1:
        self.host.rescanDiskNoUltraPath()

        Example2:
        self.host.rescanDiskNoUltraPath(onlineDiskId=[2, 3])

        Example3:
        self.host.rescanDiskNoUltraPath(onlineDiskId=2)
        """
        diskPartCmd = []
        cmd = "rescan"
        diskPartCmd.append(cmd)
        inputCmd = self._buildDiskPartInput(diskPartCmd)
        self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})
        self.logger.debug('扫lun成功，等待15秒。')
        sleep(15)

    def myParser(rawOutput):
        '''对list disk命令回显进行解析
        Args:
        rawOutput (str): 回显信息

        Return:
        result= [{"disk": 'disk', "id": 1, "status": Online, "size": 1, "size_company": GB, "free": 1, "free_company": GB},
        {"disk": 'disk', "id": 2, "status": Offline, "size": 1024, "size_company": MB, "free": 1024, "free_company": MB},
        {"disk": 'disk', "id": 3, "status": Offline, "size": 1024, "size_company": MB, "free": 1024, "free_company": MB}
        ]

        '''
        # 使用换行符对回显进行切割
        rawOutput = re.split("\x0d?\x0a|\x0d", rawOutput)
        if not rawOutput:
            return None
        # 剔除不解析的行
        rawOutput = rawOutput[7:-3]
        result = []
        # 使用正则，对回显进行格式化,格式参照注释Return
        for line in rawOutput:
            line = re.sub("(^\s+|\s+$)", "", line)
            pattern = "(\w+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(\w+)\s+(\d+)\s+(\w+)"
            match = re.match(pattern, line, re.I)
            if match:
                disk = {"disk": match.group(1),
                        "id": match.group(2),
                        "status": match.group(3),
                        "size": match.group(4),
                        "size_company": match.group(5),
                        "free": match.group(6),
                        "free_company": match.group(7)}
                result.append(disk)
        return result

    def myOnlineDisk(self, onlineDiskId):
        '''将disk状态更改为Online
        Args:
        onlineDiskId type(list ,int):需要将状态更改为Online的disk id，默认更改所有disk状态为Online

        '''
        if isinstance(onlineDiskId, list):
            for id in onlineDiskId:
                diskPartCmd = ["select disk %s" % str(id), "online disk"]
                inputCmd = self._buildDiskPartInput(diskPartCmd)
                self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})
        else:
            diskPartCmd = ["select disk %s" % str(onlineDiskId), "online disk"]
            inputCmd = self._buildDiskPartInput(diskPartCmd)
            self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})
        # 如果传递了需要将状态更改为Online的disk id，则使用传递的id，更改disk状态
        if onlineDiskId is not None:
            if isinstance(onlineDiskId, list) or isinstance(onlineDiskId, int):
                myOnlineDisk(onlineDiskId)
        # 如果没有传递需要将状态更改为Online的disk id，则获取所有disk id，更改所有disk状态为Online
        else:
            diskPartCmd = ["list disk"]
            inputCmd = self._buildDiskPartInput(diskPartCmd)
            # 下发获取所有disk的命令
            result = self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})
            # 对回显进行解析
            onlineDisks = myParser(result['stdout'])
            # 将所有状态为Offline的更改为Online
            if onlineDisks:
                for onlineDisk in onlineDisks:
                    if onlineDisk['status'] == 'Offline':
                        myOnlineDisk(onlineDisk['id'])

    def getDiskDeviceName(self, lunComponent):
        """获取映射Lun的磁盘设备名称

        Args:
        lunComponent (instance): Lun实例对象.

        Returns:
        prefix + number (str): Windows主机中对象Lun对象的磁盘设备全称, 包含"PHYSICALDISK"前缀.

        Raises:
        None.

        Examples:
        None
        """
        result = []
        number = self._getDiskNumber(lunComponent)
        if isinstance(number, str):
            prefix = r"\\.\PHYSICALDRIVE"
            return prefix + str(number)
        elif isinstance(number, list):
            for item in number:
                prefix = r"\\.\PHYSICALDRIVE" + str(item)
                result.append(prefix)
            return result
        else:
            return result

    def getNasMountPoints(self, fileComponent):
        """Get the Filesystem mount point in linux environment

        Args:
        fileComponent Type(FilesystemBase): FileSystem component object

        Returns:
        mountPoint Type(str): The file system mount point in Windows environment

        Raises:
        InvalidParamException, CommandException

        Changes:
        2015/12/24 y00305138 Created
        """
        fileName = ""
        if isinstance(fileComponent, FilesystemBase):
            fileName = fileComponent.getProperty("name")
        else:
            raise InvalidParamException("%s is not a filesystem Component. " % fileComponent)
        response = self.run({"command": ["cmd", "/c", "net", "use"]})
        if response["rc"] != 0:
            raise CommandException(response["stderr"])
        lines = self.split(response["stdout"])
        for line in lines:
            if re.search(r'' + str(fileName) + '', line):
                tmpStr = self.trim(line)
                tmpMatch = re.search(r'(\S+)\s+(\S+)', tmpStr)
                if tmpMatch and tmpMatch.groups()[0] == 'OK':
                    return self.trim(tmpMatch.groups()[1])
                elif tmpMatch and tmpMatch.groups()[0] == 'Disconnected':
                    path = self.trim(tmpMatch.groups()[1])
                    self.umountCifsFileSystem(path)
        raise InvalidParamException("can not find a filesystem Component. " % fileComponent)

    def getFileShareIoPath(self, fileComponent):
        """Get the IO path for special file share directory

        Args:
        fileComponent Type(FilesystemBase): FileSystem component object

        Returns:
        ioFile Type(str): IO file for file share directory

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

    def bringDiskOffline(self, lunComponent=None, disk=None):
        """将指定的Lun对象或磁盘Offline

        Args:
        lunComponent (instance): 需要进行Offline的Lun的Component对象，可选参数，默认: None,
        -lunComponent和disk必须指定一个值.
        disk (str): 需要进行Offline的硬盘id，如:"0"或"\\.\PHYSICALDRIVE0", 可选参数, 默认: None.

        Returns:
        None.

        Raises:
        InvalidParamException: 两个参数都为空时抛出异常.

        Examples:
        hostObj.bringDiskOnline(disk="1")
        """
        if lunComponent:
            disk = self._getDiskNumber(lunComponent)
        if disk is None:
            raise InvalidParamException("A LUN Object or a disk number must be provided")
        diskId = self._extractDiskNumber(disk)
        diskPartCmd = ['select disk ' + diskId, "offline disk"]
        inputCmd = self._buildDiskPartInput(diskPartCmd)
        # todo lock
        self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})

    def bringDiskOnline(self, lunComponent=None, disk=None):
        """将指定的Lun对象或磁盘Online

        Args:
        lunComponent (instance): 需要进行Online的Lun的Component对象，可选参数，默认: None,
        -lunComponent和disk必须指定一个值.
        disk (str): 需要进行Online的硬盘id，如:"0"或"\\.\PHYSICALDRIVE0", 可选参数, 默认: None.

        Returns:
        None.

        Raises:
        InvalidParamException: 两个参数都为空时抛出异常.

        Examples:
        hostObj.bringDiskOnline(disk="1")
        """
        if lunComponent:
            disk = self._getDiskNumber(lunComponent)
        if disk is None:
            raise InvalidParamException("A LUN Object or a disk number must be provided")
        diskId = self._extractDiskNumber(disk)
        diskPartCmd = ['select disk ' + diskId, "attributes disk clear readonly", "online disk",
                       'select disk ' + diskId, "detail disk"]
        inputCmd = self._buildDiskPartInput(diskPartCmd)
        # todo lock
        self.run({"command": ["cmd", "/c", "diskpart"], "input": [inputCmd]})
        # todo assign driveLetter

    def getSystemInfo(self):
        pass

    def getDomainInfo(self):
        pass

    def getProcessInfo(self, pid):
        pass

    def createDirectory(self, path):
        """创建目录

        Args:
        path (str): 需要创建的目录路径.

        Returns:
        None.

        Raises:
        CommandException: 创建目录失败.

        Examples:
        hostObj.createDirectory("C:\my")

        Notes:
        如果目录的名称中包含特殊字符需要将路径符号转义, 如: "c:\t" 需要写为:"c:\\t"
        """
        if self.doesPathExist({"path": path}):
            return
        response = self.run({"command": ["cmd", "/c", 'mkdir "%s"' % path]})
        if response["rc"] != 0:
            raise CommandException("Unable to create given directory: %s" % path)

    def createPartition(self, params):
        """
        Args:
        params (dict): 创建分区的参数, 键值对说明如下:
        lun (instance): 需要进行初始化的Lun的Component对象，可选参数，默认: None,
        -lunComponent和disk必须指定一个值.
        size (str): 需要创建的分区的大小, 可选参数, 不指定时将选择整个磁盘创建分区.
        disk (str): 需要进行初始化的硬盘id，如:"0"或"\\.\PHYSICALDRIVE0", 可选参数, 默认: None.
        mount (str): 初始化后磁盘的挂载点, 不能包含空格, 当mount和letter同时指定时mount优先级高,可选参数，默认: None.
        filesystem (str): 磁盘创建的文件系统, 取值范围为: (FAT, FAT32, exFAT, NTFS), 默认: NTFS.
        letter (str): 初始化后磁盘的驱动器号, 当mount和letter同时指定, mount优先级高, 可选参数，默认: None.
        unit_size (str): UniAuto Size 单位类型, 取值范围为:
        -NTFS: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -FAT: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -FAT32: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -exFAT: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB
        64 KB, 128 KB, 256 KB, 512 KB, 1 MB, 2 MB, 4 MB, 8 MB, 16 MB, 32 MB.

        Returns:
        mount (str): 创建的分区挂载点.

        Raises:
        InvalidParamException: 参数错误.
        CommandException: 执行命令失败.

        Examples:
        hostObj.createPartition({"disk": "1", "size": "1GB", })
        Output:
        > "F"

        Notes:
        1、该方法当前仅支持英文版的windows操作系统.
        2、当mount和letter都不指定时将自动分配一个letter.
        """
        if "lun" in params and params["lun"]:
            params["disk"] = self._getDiskNumber(params["lun"])
        if "disk" not in params or not params["disk"]:
            raise InvalidParamException("A LUN Object or a disk number must be provided.")
        size = None
        if "size" in params and params["size"] and Units.isSize(params["size"]):
            size = Units.getNumber(Units.convert(params["size"], "MB"))
        drive = self._extractDiskNumber(params["disk"])
        diskPartCmd = ["select disk %s" % drive, 'online disk', 'ATTRIBUTES DISK CLEAR READONLY',
                       'create partition primary ', 'assign ', 'detail disk']
        if size:
            diskPartCmd[3] += "size=%s" % size
        if "mount" in params and params["mount"]:
            if re.search(r'\s', params["mount"]):
                raise InvalidParamException("You cannot format to a path with spaces."
                                            "\nFor Example:\nGood: C:\\LunMounts\\1 \nBad: C:\\Lun Mounts\\1")
            self.createDirectory(params["mount"])
            diskPartCmd[4] += "mount=%s" % params["mount"]
        elif "letter" in params and params["letter"]:
            diskPartCmd += "letter=%s" % params["letter"]
        inputCmd = self._buildDiskPartInput(diskPartCmd)
        # todo lock
        response = self.run({"command": ["diskpart"], "input": [inputCmd]})
        if re.search(r'The disk you specified is not valid', response["stdout"]):
            raise CommandException("Disk number does not exist on host: %s" % drive)
        elif re.search(r'The directory is not empty', response["stdout"]):
            if "mount" in params and params["mount"]:
                raise CommandException("The mount directory you have specified is not empty: %s" % params["mount"])
            elif "letter" in params and params["letter"]:
                raise CommandException("The letter you have specified is already taken: %s" % params["letter"])
            else:
                raise CommandException("The directory is not empty.")
        elif re.search(r'There is insufficient free space', response["stdout"]):
            raise CommandException("Insufficient space on disk %s for %s megabytes")
        elif re.search(r'The disk management services could not complete the operation', response["stdout"]):
            raise CommandException("Failed to create partition on drive #: %s" % drive)
        elif re.search(r'DiskPart succeeded in creating the specified partition', response["stdout"]) is None:
            raise CommandException("Failed to create partition on drive #: %s" % drive)
        elif re.search(r'DiskPart successfully assigned', response["stdout"]) is None:
            raise CommandException("Failed to create partition on drive #: %s" % drive)
        mount = None
        if "letter" in params and params["letter"]:
            mount = params["letter"]
        if "mount" in params and params["mount"]:
            mount = params["mount"]
        if mount is None:
            partitions = self._getVolumeArray(response["stdout"])
            mount = partitions[len(partitions) - 1]["letter"]
        if "filesystem" in params and params["filesystem"]:
            unitSize = None
        if "unit_size" in params and params["unit_size"]:
            unitSize = params["unit_size"]
        self.createFilesystem(mount, filesystem=params["filesystem"], unitSize=unitSize)
        return mount

    def getDateAndTime(self):
        """获取系统时间

        Args:
        None.

        Returns:
        dateTime (dict): 包含当前时间的字典.
        year (str): 当前时间的年份, 如: 1990, 2012.
        month (str): 当前时间的月份，如: 01, 12.
        day (str): 当前时间的日前，如: 01, 20.
        hour (str): 当前时间的小时，如: 01, 23.
        minute (str): 当前时间的分钟，如: 00, 02, 59.
        second (str): 当前时间的秒数，如: 00, 02, 59.

        Raises:
        CommandException: 获取当前时间失败.

        Examples:
        hostObj.getDateAndTime()
        """
        dateTime = {}
        # 获取系统日期
        response = self.run({"command": ["cmd", "/c", "date"], "input": ["", ">"], "waitstr": ":"})
        if response["rc"] != 0:
            raise CommandException("get host date failed.")
        dateLine = self.split(response["stdout"])
        for item in dateLine:
            dates = re.match('.*\s+(\d+)/(\d+)/(\d+)', item)
            if dates:
                if len(dates.groups()[0]) == 4:
                    dateTime = {"year": dates.groups()[0],
                                "month": dates.groups()[1],
                                "day": dates.groups()[2]}
                else:
                    dateTime = {"year": dates.groups()[2],
                                "month": dates.groups()[0],
                                "day": dates.groups()[1]}
        # 获取系统时间
        response = self.run({"command": ["cmd", "/c", "time"], "input": ["", ">"], "waitstr": ":"})
        if response["rc"] != 0:
            raise CommandException("get host time failed.")
        timeLine = self.split(response["stdout"])
        for item in timeLine:
            times = re.match('.*\s+(\d+):(\d+):(\d+)', item)
            if times:
                dateTime.update({"hour": times.groups()[0],
                                 "minute": times.groups()[1],
                                 "second": times.groups()[2]})
        return dateTime

    def initializeDisk(self, lunComponent=None, disk=None, mount=None, filesystem=None, letter=None, unitSize=None):
        """对指定的已映射的磁盘或Lun对象进行初始化

        初始化包含将整个磁盘或Lun对象创建为一个分区, 并格式化为指定的文件系统, 挂载到指定的mount点或指定的驱动器号.

        Args:
        lunComponent (instance): 需要进行初始化的Lun的Component对象，可选参数，默认: None,
        -lunComponent和disk必须指定一个值.
        disk (str): 需要进行初始化的硬盘id，如:"0"或"\\.\PHYSICALDRIVE0", 可选参数, 默认: None.
        mount (str): 初始化后磁盘的挂载点, 不能包含空格, 当mount和letter同时指定时mount优先级高,可选参数，默认: None.
        filesystem (str): 磁盘创建的文件系统, 取值范围为: (FAT, FAT32, exFAT, NTFS), 默认: NTFS.
        letter (str): 初始化后磁盘的驱动器号, 当mount和letter同时指定, mount优先级高, 可选参数，默认: None.
        unitSize (str): UniAuto Size 单位类型, 取值范围为:
        -NTFS: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -FAT: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -FAT32: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB, 64 KB
        -exFAT: 512 B, 1024 B, 2048 B, 4096 B, 8192 B, 16 KB, 32 KB
        64 KB, 128 KB, 256 KB, 512 KB, 1 MB, 2 MB, 4 MB, 8 MB, 16 MB, 32 MB.

        Returns:
        None.

        Raises:
        None.

        Examples:
        hostObj.initializeDisk(disk="1", filesystem="FAT32", letter="C")

        """
        mount = self.createPartition({"lun": lunComponent,
                                      "disk": disk,
                                      "mount": mount,
                                      "filesystem": filesystem,
                                      "letter": letter,
                                      "unit_size": unitSize})
        if not filesystem:
            self.createFilesystem(mount=mount, unitSize=unitSize)
        pass

    @validateParam(baseDir=str, template=str)
    def _createRandomDirectory(self, baseDir, template):
        """创建一个随机的目录
        Args:
        baseDir (str): 随机目录的基础路径.
        template (str): 随机目录的格式.

        Returns:
        randomDir (str): 根据随机目录的格式，在基础路径中创建的随机目录绝对路径.

        Raises:
        InvalidParamException: baseDir不存在.

        Examples:
        None.

        """
        if not self.doesPathExist({"path": baseDir}):
            raise InvalidParamException("Tried creating a random folder in %s , but %s does not exist!" % (baseDir, baseDir))
        output, var, oldVar = "", 0, 0
        alphabet = map(chr, range(97, 123))
        alphabet.extend(map(chr, range(65, 91)))
        for letter in template:
            if var == oldVar + 1:
                if re.match(r'^d$', letter):
                    output += str(random.randrange(10))
                elif re.match(r'^c$', letter):
                    output += alphabet[random.randrange(len(alphabet))]
                else:
                    output += "%%%s" % letter
                oldVar = var
            elif letter == "%":
                var += 1
            else:
                output += letter
        if self.doesPathExist({"path": output}) and var > 0:
            return self._createRandomDirectory(baseDir, template)
        elif self.doesPathExist({"path": output}):
            intendedDir = self.catDir(baseDir, output)
            raise UniAutosException("There is no randomness in template, and %s is taken." % intendedDir)
        else:
            randomDir = self.catDir(baseDir, output)
            self.createDirectory(randomDir)
        return randomDir

    def isPowercliInstalled(self):
        """Check if powercli is installed

        Args:
        None

        Returns:
        None

        Raises:
        Boolean - To return 1 means powercli is installed

        Examples:
        None.
        """
        response = self.run({"command": ["cmd", "/c", 'powershell', '1+1'],
                             "checkrc": 0})
        if 'rc' in response and response['rc'] != 0:
            return 0
        return 1

    def niPxi2510SwitchSetTopologyAndReset(self, deviceName, newTopology):
        """切换设备的Topo，并重置
        Args:
        deviceName (str)： 设备名称.
        newTopology (str): 设备Topo.
        """
        return self.sendNiPxi2510Command('SwitchSetTopologyAndReset',
                                         deviceName,
                                         newTopology)

    def niPxi2510SwitchConnect(self, ch, dut, BoolStatus):
        """打开开关
        Args:
        ch (str): 开关ch端口.
        dut (str): 开关dut端口.
        BoolStatus (bool): 开关状态.
        """
        return self.sendNiPxi2510Command('SwitchConnect', ch, dut, BoolStatus)

    def niPxi2510SwitchDisconnect(self, ch, dut, BoolStatus):
        """关闭开关
        Args:
        ch (str): 开关ch端口.
        dut (str): 开关dut端口.
        BoolStatus (bool): 开关状态.
        """
        return self.sendNiPxi2510Command('SwitchDisconnect', ch, dut, BoolStatus)


    def niPxi2510AllSwitchDisconnect(self):
        """打开所有开关
        """
        return self.sendNiPxi2510Command('AllSwitchDisconnect')

    def niPxi2510SwitchWait(self, overtime):
        """开关等待
        Args:
        overtime (int): 开关等待时间.
        """
        return self.sendNiPxi2510Command('SwitchWait', overtime)

    def niPxi2510SwitchFindPath(self, ch, dut, path, pathBufferSize, pathStatus):
        """打开开关
        Args:
        ch (str): 开关ch端口.
        dut (str): 开关dut端口.
        path (str): 开关路径.
        pathBufferSize (bool): 开关buffer.
        pathStatus (bool): 开关状态.
        """
        return self.sendNiPxi2510Command('SwitchFindPath', ch, dut, path, pathBufferSize, pathStatus)

    def niPxi2510SwitchClose(self):
        """关闭开关
        """
        return self.sendNiPxi2510Command('SwitchClose')

    def sendNiPxi2510Command(self, action, *args):
        """通过串口发送命令,host上需要安装pyserial，目前手动安装；

        Args:
        action (str):下发的命令（支持[SwitchSetTopologyAndReset\SwitchConnect\SwitchDisconnect\
        AllSwitchDisconnect\SwitchWait\SwitchFindPath\SwitchClose])
        args action方法参数.

        Returns:
        stdout，命令原始回显，需解析

        Examples:
        1、执行命令:
        ret= host.sendNiPxi2510Command("SwitchSetTopologyAndReset","device","Topo1")

        """
        # Copy File :NiPxi2510.py
        tmp = os.path.split(os.path.realpath(__file__))[0]
        ni_pxi_py = os.path.join(tmp.split('Device')[0], 'Util', 'NiPxi2510', 'NiPxi2510.py')
        ni_pxi_dll = os.path.join(tmp.split('Device')[0], 'Util', 'NiPxi2510', 'NI_PXI2510.dll')
        if not self.doesPathExist({'path': "C:/NiPxi2510.py"}):
            self.putFile({'source_file': ni_pxi_py,
                          'destination_file': "C:/NI_PXI2510.py"})
        if not self.doesPathExist({'path': ni_pxi_dll}):
            self.putFile({'source_file': ni_pxi_dll,
                          'destination_file': "C:/NI_PXI2510.dll"})
        params = {}
        commands = ""
        if len(args) >= 1:
            args = [str(tmp) for tmp in args]
            commands = ' '.join(args)
        params['command'] = ["cmd", "/c", "python NI_PXI2510.py %s %s" % (action, commands)]
        params["directory"] = "C:/"
        response = self.run(params)
        if response['stdout'] == None:
            raise CommandException(response['stderr'])
        return response['stdout']

    def sendSerial(self, mode, user, pwd, *args, **kwargs):
        """通过串口发送命令,host上需要安装pyserial，目前手动安装；

        Args:
        mode (str):阵列的模式（目前仅支持PANGEA_SES/SUPER_ADMIN/IBMC(需下电)/PCIE_DSW/ADMIN_CLI)
        user (str): 登录user
        pwd (str): 登录pwd
        cmd (str): 发送命令,可传多条

        Returns:
        stdout，命令原始回显，需解析

        Raises:

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
        self.putFile({'source_file': src_file, 'destination_file': "C:/runSerial.py"})
        params = {}
        cmds = ""
        for cmd in args:
            cmds = cmds + '\"' + cmd + '\"' + ' '
        # 串口登陆Dorado 3U IBMC 时需要传入控制器的ID， 小写字母, 默认情况下不需要传入.
        ctrl = kwargs.get('ctrl')
        if ctrl is None:
            params['command'] = ["cmd", "/c", "python runSerial.py", mode, user, pwd, waitTime, cmds]
        else:
            params['command'] = ["cmd", "/c", "python runSerial.py", mode, user, pwd, waitTime, ctrl, cmds]
        params["directory"] = "C:/"
        response = self.run(params)
        if response['stdout'] == None:
            raise CommandException(response['stderr'])
        return response['stdout']

    def mountCifsFileSystem(self, logicIp, share, user=None, pwd=None, mountPoint=None):
        """对阵列的Cifs共享文件夹进行挂载操作
        Args:
        logicIp (str): 阵列的逻辑端口IP
        share (str): cifs共享
        user (str)：(可选参数)认证用户名
        pwd (str): (可选参数)认证用户的密码

        Returns:
        挂载点盘符号.如 H:

        Raises:

        Examples:
        hostObj.mountCifsFileSystem('129.91.57.12', 'test', 'tester11', 'Admin@storage')
        """
        try:
            self.Lock.acquire()
            # 查看系统当前存在的盘符号
            diskpartResult = self.run({"command": ["cmd", "/c", "diskpart"], "input": ["list volume"]})
            systemVolumInfos = diskpartResult['stdout'].split('\r\n')[7:]
            volumes = []
            for systemVolumInfo in systemVolumInfos:
                systemVolumInfoList = systemVolumInfo.split()
                volumes.append(systemVolumInfoList[2])
            # 查看已经存在的网络映射盘符
            netVolumInfos = self.run({"command": ["cmd", "/c", r"net use"]})['stdout'].split('\r\n')[6:-1]
            for netVolumInfo in netVolumInfos:
                netVolumInfoList = netVolumInfo.split()
                for i in netVolumInfoList:
                    if ':' in i:
                        volumes.append(i[0])
            # 定义一个空闲的可用盘符做为cifs共享挂载点
            if mountPoint is None:
                for i in xrange(72, 91):
                    if chr(i) not in volumes:
                        mountPoint = chr(i)
                        break

            # 准备执行挂载操作
            if mountPoint is None:
                raise UniAutosException('There is no available driver letter')
            params = {}
            mountPoint = mountPoint + ':'
            sharePath = '\\\\' + logicIp + '\\' + share
            params['command'] = ["cmd", "/c", "net use", mountPoint, sharePath]
            if pwd is not None:
                params['command'].append(pwd)
            if user is not None:
                params['command'].append('/user:' + user)
            response = self.run(params)
            if response["rc"] != 0:
                raise CommandException(response['stderr'])
        finally:
            self.Lock.release()
        return mountPoint

    def umountCifsFileSystem(self, mountPoint='all'):
        """对阵列的Cifs共享文件夹进行取消挂载操作
        Args:
        mountPoint (str): 待取消的挂载点

        Returns:
        None.

        Raises:

        Examples:
        hostObj.mountCifsFileSystem('H:')

        """
        if mountPoint is not 'all':
            response = self.run({"command": ["cmd", "/c", r"net use %s /delete /y" % mountPoint]})
        else:
            response = self.run({"command": ["cmd", "/c", "net use * /delete /y"]})
        if response["rc"] != 0:
            raise CommandException(response['stderr'])

    def wipe(self):
        """清除Linux上的所有业务

        Args:
        None

        Returns:
        None

        Raises:
        None

        Examples:
        host.wipe()

        """
        matcher = None
        # Stop SDTester
        # sdTester = self.run({'command': ['ps', '-aux', '|', 'grep', 'sdtester']})
        # for line in re.split('\r|\n', sdTester['stdout']):
        # matcher = re.search('root\s+(\d+).*/sdtester', line)
        # if matcher:
        # self.run({'command': ['kill', '-9', matcher.groups()[0]]})

    def sendCmd(self, cmd):
        """创建目录

        Args:
        path (str): 需要下发的命令.

        Returns:
        None.

        Raises:
        CommandException: 命令不可执行.

        Examples:
        hostObj.sendCmd("ipconfig")

        Notes:
        """
        response = self.run({"command": ["cmd", "/c", "%s" % cmd], "timeout": 240})
        return response['stdout']

    def getFileShareIoDirectory(self, fileComponent, directory='ioDir'):
        """Get the IO path for special file share directory

        Args:
        fileComponent Type(FilesystemBase): FileSystem component object
        directory : path name
        Returns:
        ioDirectory Type(str): IO file share directory

        Raises:
        None

        Changes:
        2015/12/24 y00305138 Created

        """
        fileMountPoint = self.getNasMountPoints(fileComponent)
        if fileMountPoint is not None:
            ioDirectory = "%s\\%s" % (fileMountPoint, directory)
            self.createDirectory(ioDirectory)
            return ioDirectory
        else:
            raise CommandException("%s has no share directory" % fileComponent)

    def setIpAddress(self, kwargs):
        """设置IP地址

        Args:
        *ipv4 (str) 第四版ip 例：192.168.1.2
        *ipv6 (str) 第六版ip 例：AD80:0000:0000:0000:ABAA:0000:00C2:0002
        *gateway (str) 网关地址 例：192.168.1.1
        *mask (str) 子网掩码 例：255.255.255.0

        ipv4和ipv6不能同时写入
        使用小写ip

        Returns:
        None.

        Raises:
        CommandException("No ip information in the params.")
        CommandException("Error: ipv4 and ipv6 couldn`t write at the same time.")
        CommandException("Get Keyword failed. Please Check the Keywords whose lost.")
        CommandException("Get KeyValue is Failed. ip: %s, mask: %s" %(ipValue, maskValue))
        InvalidParamException("The value of ip or value of mask is invalid. ip: %s, mask: %s" % (ipValue, maskValue))
        CommandException("Execute Command Failed.")

        Examples:
        params = {"ipv4":"192.168.1.1", "mask":"255.255.255.0", "gateway":"192.168.1.1"}
        hostObj.setIpAddress(params)

        Notes:
        """
        ipValue = ""
        # 判断获得的参数表中是否有name关键字,若没有，添加一个name，值为"local area connection"
        if "name" not in kwargs:
            kwargs["name"] = "local"
        # 判断获得的参数表中是否有ip
        if ("ipv4" or "ipv6") not in kwargs:
            raise CommandException("No ip information in the params.")
        # 判断获得参数表中是否同时有IPv4和IPv6
        elif ("ipv4" and "ipv6") in kwargs:
            raise CommandException("Error: ipv4 and ipv6 couldn`t write at the same time.")
        elif "ipv4" in kwargs:
            ipValue = kwargs["ipv4"]
        elif "ipv6" in kwargs:
            ipValue = kwargs["ipv6"]
        # 判断获取的kwargs中是否存其他关键字
        if ("mask" or "gateway") not in kwargs:
            raise CommandException("Get Keyword failed. Please Check the Keywords(mask and gateway) whose lost.")
        # 判断关键字”ip“或”mask“的值是否合法
        if not (isinstance(ipValue, str)) or not (isinstance(kwargs["mask"], str)):
            raise InvalidParamException("The value of ip or value of mask is invalid. ip: %s, mask: %s" % (ipValue, kwargs["mask"]))
        # 拼接cmd命令
        cmd2 = "source=static"
        cmd3 = "gwmetric=auto"
        ipcmd = "addr=%s" % ipValue
        maskcmd = "mask=%s" % kwargs["mask"]
        gatewaycmd = "gateway=%s" % kwargs["gateway"]
        namecmd = "name=%s" % kwargs["name"]
        # 执行命令
        response = self.run({"command": ["cmd", "/c", "netsh", "interface", "ip", "set", "address", namecmd, cmd2, ipcmd, maskcmd, gatewaycmd, cmd3]})
        # 判断命令是否执行成功
        if response["rc"] != 0:
            raise CommandException("Execute Command Failed.")

    def setAgentConfigPwd(self, passwd):
        """windows主机端修改防病毒服务器共享密匙
        修改文件:C:\Program Files(x86)\Huawei\Antivirus Agent\cfg\agentConfig.ini
        arg:
        passwd str:(必选)防病毒服务器共享密码

        example:
        self.hostwin.setAgentConfigPwd(passwd='123456')
        """
        path = 'c:\\Program Files (x86)\\Huawei\\Antivirus Agent\\cfg\\agentConfig.ini'
        # 读取文件内容
        detail = self.run({"command": ["cmd", "/c", "type", '\"' + path + '\"']})
        # 备份文件至C:\usr目录下
        rst = self.run({"command": ["cmd", "/c", "move", '\"' + path + '\"', 'C:\\usr']})
        if not re.search('moved', rst['stdout']):
            raise CommandException("备份文件失败，请检查")
        # 对源文件内容密码进行修改
        detailList = detail['stdout'].split('\r\n')
        for item in detailList:
            if re.search('Pwd', item):
                line = detailList.index(item)
                detailList[line] = 'Pwd = %s' % passwd
        # 重写文件
        for line in detailList:
            self.run({"command": ["cmd", "/c", "echo %s >> %s" % (line, '\"' + path + '\"')]})

    def restorrAgentConfig(self):
        """windows主机端防病毒服务器共享密匙配置文件修改后还原
        example:
        self.hostwin.restorrAgentConfig()
        """
        path = 'c:\\Program Files (x86)\\Huawei\\Antivirus Agent\\cfg\\'
        self.run({"command": ["cmd", "/c", "del", '\"' + path + 'agentConfig.ini' + '\"']})
        rst = self.run({"command": ["cmd", "/c", "move", 'c:\\usr\\agentConfig.ini', '\"' + path + '\"']})
        if not re.search('moved', rst['stdout']):
            raise CommandException("还原文件失败，请检查")

    def getHbaInfo(self):
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
        """
        hbaDict = dict()
        response = self.run({'command': ['cmd', '/c', 'fcinfo']})
        if 'rc' in response and response['rc'] != 0:
            self.logger.debug('####ERROR####send cmd fcinfo error\nerror message: %s' % response['stderr'])
        else:
            result = response['stdout']
            find_wwns = re.findall(r'PortWWN:\s+(\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2})', result, re.S)
            for _wwn in find_wwns:
                hbaDict[_wwn] = {'port': _wwn, 'node': _wwn}
        return hbaDict

    def dd(self, diskDevice=None, of=None, skip=None, seek=None, bs=None, count=None):
        command = ["cmd", "/c", "dd"]
        if diskDevice is not None:
            command.append('if=%s' % diskDevice)
        if of is not None:
            command.append('of=%s' % of)
        if skip is not None:
            command.append('skip=%s' % skip)
        if seek is not None:
            command.append('seek=%s' % seek)
        if bs is not None:
            command.append('bs=%s' % bs)
        if count is not None:
            command.append('count=%s' % count)
        self.run({"command": command})

    def analyUpgradeLog(self, path):
        """分析升级日志

        Returns:
        info (str): 返回升级结果

        Raises:
        CommandException: 命令执行失败.

        Examples:
        path = hostObj.analyUpgradeLog("C:\\svp_upload.log")
        Output:
        >升级结果
        """
        for line in open(path):
            if 'Windows Toolkit:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Windows Toolkit:的upgrade结果是:success")
                except:
                    self.logger.error(u"Windows Toolkit升级失败")
                    assert (False)
            if 'Windows ntp:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Windows ntp:的upgrade结果是:success")
                except:
                    self.logger.error(u"Windows ntp升级失败")
                    assert (False)
            if 'Windows server:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Windows server:的upgrade结果是:success")
                except:
                    self.logger.error(u"Windows server升级失败")
                    assert (False)
            if 'Windows fdsa:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Windows fdsa:的upgrade结果是:success")
                except:
                    self.logger.error(u"Windows fdsa升级失败")
                    assert (False)
            if 'Windows APP:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Windows APP:的upgrade结果是:success")
                except:
                    self.logger.error(u"Windows APP升级失败")
                    assert (False)
            if 'Host selfupgrade:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Host selfupgrade:的upgrade结果是:success")
                except:
                    self.logger.error(u"Host selfupgrade升级失败")
                    assert (False)
            if 'Host FDSA:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Host FDSA:的upgrade结果是:success")
                except:
                    self.logger.error(u"Host FDSA升级失败")
                    assert (False)
            if 'Host EMP_SERVER:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Host EMP_SERVER:的upgrade结果是:success")
                except:
                    self.logger.error(u"Host EMP_SERVER升级失败")
                    assert (False)
            if 'Linux selfupgrade:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux selfupgrade:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux selfupgrade:升级失败")
                    assert (False)
            if 'Linux SystemReporter:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SystemReporter:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SystemReporter:升级失败")
                    assert (False)
            if 'Linux FDSA:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux FDSA:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SFDSA:升级失败")
                    assert (False)
            if 'Linux ISM:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux ISM:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux ISM:升级失败")
                    assert (False)
            if 'Linux SVP_AGENT:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SVP_AGENT:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SVP_AGENT:升级失败")
                    assert (False)
            if 'Linux SVP_EMP_CLIENT:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SVP_EMP_CLIENT:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SVP_EMP_CLIENT:升级失败")
                    assert (False)
            if 'Linux SVP_OMM:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SVP_OMM:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SVP_OMM:升级失败")
                    assert (False)
            if 'Linux SVP_CLI:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SVP_CLI:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SVP_CLI:升级失败")
                    assert (False)
            if 'Linux SSL_PROXY:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SSL_PROXY:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SSL_PROXY:升级失败")
                    assert (False)
            if 'Linux SVP_SCRIPT:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SSL_PROXY:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux SSL_PROXY:升级失败")
                    assert (False)
            if 'Linux SMI-S:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux SMI-S:的upgrade结果是:success")
                except:
                    print(u"Linux SMI-S:升级失败")
                    assert (False)
            if 'Linux OPENSSH:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux OPENSSH:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux OPENSSH:升级失败")
                    assert (False)
            if 'Linux DEV_LOGIN:' in line:
                try:
                    re.search(line.split(":")[-1].strip(), "success").group()
                    self.logger.info(u"Linux DEV_LOGIN:的upgrade结果是:success")
                except:
                    self.logger.error(u"Linux DEV_LOGIN:升级失败")
                    assert (False)
    def getEnvPath(self, prog):
        """获取某个程序的环境变量信息

        Returns:
        info (str): 返回环境变量

        Raises:
        CommandException: 命令执行失败.

        Examples:
        path = hostObj.getEnvPath("ZIP")
        Output:
        >'C:\\Program Files\\7-Zip'
        """
        params = {}
        params["command"] = ["cmd", "/c", "path"]
        path = self.run(params)
        result = path['stdout'].split(";")
        for info in result:
            if re.search(prog, info):
                return info

    def decompress(self, srcPath, destPath):
        """用7zip解压软件

        Returns:
        info (str): 返回环境变量

        Raises:
        CommandException: 命令执行失败.

        Examples:
        path = hostObj.getEnvPath("ZIP")
        Output:
        >'C:\\Program Files\\7-Zip'
        """
        self.zipPath = self.getEnvPath("Zip")
        params = {}
        destPath = "-o" + destPath
        params["command"] = ["cmd", "/c", "7z.exe", "x", srcPath, destPath, "-aoa"]
        params['directory'] = self.zipPath + '\\'
        rs = self.run(params)
        return rs["stdout"]

    def svpupgrade(self, filename="svp_upgrade.bat", path="D:\\SvpUpgrade\\svp"):
        """svp win wm升级启动

        Returns:
        info (str): 返回升级结果

        Raises:
        CommandException: 命令执行失败.

        Examples:
        path = hostObj.svpupgrade("svp_upgrade.bat","D:\\SvpUpgrade\\svp")
        Output:
        >SVP WIN wm升级结果

        """
        params = {}
        params["command"] = ["cmd", "/c", filename]
        if path is not None:
            params["directory"] = path
        # (y: yes, n: exit):,(y: continue, n: exit):,(y: yes, n: exit):(y:reboot now automaticly n:reboot later manually):
        # (y: continue, n: exit),:(y: yes, n: exit):,(y:reboot now automaticly n:reboot later manually):
        params["waitstr"] = "(y: yes, n: exit):|(y: continue, n: exit):|" \
                            "(y:reboot now automaticly n:reboot later manually):"
        params["input"] = ["y"]
        result = self.run(params)
        # return result['stdout']
        return result

    def run_powershell_script(self, script_path, params=None, on_new_sessoin=False, timeout=15000):
        """run powershell scprit

        Returns:
        script_path (str): the script path
        params (dict): (Optional)the power shell script params

        Changes:
        l00355383 2017-11-21 20:43:15 Created
        """
        if not self.doesPathExist({'path': script_path}):
            raise UniAutosException('[%s]the script[%s] isn`t exist in windows system, please check' % (self.localIP, script_path))
        command = [r'%s' % script_path]
        if params is not None:
            command += ['-%s %s' % (k, v) for k, v in params.items()]
        if not on_new_sessoin:
            response = self.run({'command': ['cmd', '/c', 'powershell'] + command,
                                 'timeout': timeout})
            # 如果没有执行结果，或者stderr有执行错误则抛错
            if 'rc' in response and response['rc'] != 0:
                raise UniAutosException('run powershell %s error\nerror message:%s'
                                        % (command, response['stderr']))
            else:
                result = response['stdout']
                search_result = re.search(r'(Test Result\s*:\s*.*)', result, re.S)
                groups = search_result.groups()
                if len(groups) == 0:
                    raise UniAutosException('the powershell result format is not correct, there is no Test Result string')
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
                                raise UniAutosException('a line[%s] of the poershell result format is not correct' % line)
                if str(cmd_result['test_result']).lower() == 'passed' or cmd_result['test_result'] == 'True':
                    return cmd_result
                else:
                    raise UniAutosException('the powershell script[%s] running failed, TestResult is not Passed' % os.path.join(script_path, os.path.pardir))
        else:
            p = '(%s)' % ','.join(['"""-%s %s"""' % (k, v) for k, v in params.items()])
            script_params = {'UserName': self.username,
                             'Password': self.password,
                             'ScriptPath': script_path,
                             'Params': p}
            result = self.run_powershell_script(hyperv_alias.RUN_PS_SCRIPT, params=script_params, on_new_sessoin=False)
        return result

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
            raise UniAutosException('run powershell %s error\nerror message:%s' % (params['command'], response['stderr']))
        else:
            return response['stdout']

    def svpRollBack(self, filename="svp_rollback_os.bat", path="D:\\SvpUpgrade\\svp"):
        """
        欧拉补丁回退
        """
        params = {}
        params["command"] = ["cmd", "/c", filename]
        params["directory"] = path
        params["waitstr"] = "Do you want to rollback os?"
        params["input"] = ["y", "y:reboot now automaticly n:reboot later manually", "n", "effect"]
        params['timeout'] = 300
        result = self.run(params)
        return result

    def renameFile(self, path, oldName, newName):
        """重命名文件
        Args:
        path:父路径
        newName：新名
        oldName:旧名
        Raises:
        None
        Examples:
        None
        Author:
        y00464298
        """
        if path[-1] != "\\":
            path += "\\"
        wholepath = path + oldName
        cmd = "ren \"%s\" \"%s\"" % (wholepath, newName)
        res = self.sendCmd(cmd)
        return res

    def sim7ZipFault(self):
        """构造解压软件故障，切记要恢复
        Args:
        None
        Raises:
        None
        Examples:
        None
        Author:
        y00464298
        """
        zipPath = self.getEnvPath("Zip")
        normalName = "7z.dll"
        errorName = "7z.1dll"
        self.renameFile(zipPath, normalName, errorName)

    def recover7ZipFault(self):
        """恢复解压软件
        Args:
        None
        Raises:
        None
        Examples:
        None
        Author:
        y00464298
        """
        zipPath = self.getEnvPath("Zip")
        normalName = "7z.dll"
        errorName = "7z.1dll"
        self.renameFile(zipPath, errorName, normalName)

    def getFileFromSftp(self, sftpIp, sftpUser, sftpPwd, sourPath, destPath="D:\\", localPath=os.path.join(os.getcwd(), "SVP"), deleteLocal=False):
        """将sftp上的文件传输到windows虚拟机中
        Args:
        sftpIp:sftp的ip
        sftpUser:sftp用户名
        sftpPwd:服务器密码
        sourPath:在获取文件所在的包路径
        destPath：存在虚拟机的文件路径
        localPath：本地临时文件的路径
        deleteLocal:是否删除本地临时文件
        Return:
        传至远端的完整路径
        Examples:
        self.svpWindows.windows.getFileFromSftp(sftpIp=self.sftpIp, sftpUser=self.sftpUser,
        sftpPwd=self.sftpPwd,
        localPath="D:\\",
        destPath=self.decompressPath,
        sourPath=self.sftpPackageName)
        Author:
        y00464298
        """
        sftp = ftpClient(sftpIp, sftpUser, sftpPwd)
        # 获取ftp上的文件
        fileName = sftp.getPackageToLocal(ftpPath=sourPath, localPath=localPath)
        sftp.quit()
        # 传包至远端
        srcPath = os.path.join(destPath, fileName.split("\\")[-1])
        self.getCmdObj().putFile(fileName, srcPath)
        # 删除本地文件
        if deleteLocal:
            os.remove(localPath)
        return srcPath

    def getSvpCurrentVersion(self):
        """获取当前Svp版本信息
        Args:
        None
        Return:
        如：V500R700C30
        Examples:
        None
        Author:
        y00464298
        """
        cmd = "type D:\\Huawei\\version"
        stdout = self.sendCmd(cmd)
        res = stdout.split()[-1]
        if re.search("V[3|5]00R00\dC\d0", res):
            return res
        else:
            raise UniAutosException("解析版本信息失败")

    def get_file_size(self, file_path, size_unit='GB'):
        """
        获取文件大小

        Args:
        file_path: (str) 文件路径
        size_unit: (str) 容量单位

        Returns:
        size_number: (float) 容量大小
        """
        size_number = self.run_powershell({'command': ['(dir "%s").length/1%s' % (file_path, size_unit)]})
        return float(size_number)

    def get_dir_size(self, dir_path, size_unit='GB'):
        """
        获取文件夹大小

        Args:
        dir_path: (str) 文件路径
        size_unit: (str) 容量单位

        Returns:
        size_number: (float) 容量大小
        """
        size_number = self.run_powershell({'command': ['"(dir "%s" -rec -file | measure length -sum).sum/1%s"' % (dir_path, size_unit)]})
        return float(size_number)