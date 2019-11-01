
# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：该模块提供vSphere相关功能，包括对VMware虚拟机的操作，ESX主机的管理的方法和属性

版权信息：华为技术有限公司，版本所有(C) 2008-2009

"""

import sys
import re
from UniAutos.Exception.UniAutosException import UniAutosException

# try to import VmomiAdapter if not use object to create, but this device is unavailable,
# because not have vmomi.

HAS_VMOMI = True
try:
    from uniautos_esxlib.vmomiAdapter import VmomiAdapter as Vmomi
except ImportError as error:
    HAS_VMOMI = False
Vmomi = object


class VSphere(Vmomi):
    def __init__(self, username, password, params):

        """Vsphere client类，继承于Host类，该类主要包含ESX主机相关操作于属性
    -下面的Components类属于Vshpere类，包含Nice Name与Component Class Name:

    Nice Name Component Class Name
    ================================================================
    To be Added

    -构造函数参数:
    Args:
    username (str): XenServer主机登陆使用的用户名, 建议使用root用户.
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
    vSphereObj (instance): vSphereObj.

    Raises:
    None.

    Examples:
    None.

    """


vCenter = params.get('vCenter')
self.environmentInfo = None
self.os = 'vSphere'
self.hasVmomi = True
self.resource = None
if not HAS_VMOMI:
    self.hasVmomi = False
return
if vCenter:
    super(VSphere, self).__init__(vCenter['ipv4_address'], vCenter['username'], vCenter["password"],
                                  keepSession=True)
else:
    super(VSphere, self).__init__(params['ipv4_address'], username, password, keepSession=True)


def setResource(self, resource):
    """给设备设置归属的Resource对象

    Args:
    resource (instance): Resource对象.

    Returns:
    None.

    Raises:
    None.

    Examples:
    None.

    """


self.resource = resource

if __name__ == '__main__':
    pass
