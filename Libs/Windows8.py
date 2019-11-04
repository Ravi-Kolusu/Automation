#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能：windows操作系统的基类
"""

from Libs.Windows import Windows
from UniAutos.Wrapper.Tool.PowerShell.PowerShell import PowerShell

class Windows8(Windows):
    """Windows8主机类, 继承于Windows类

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
        self.os = 'Windows8'
        wrapper = PowerShell()
        self.registerToolWrapper(host=self, wrapper=wrapper)