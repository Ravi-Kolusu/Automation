#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：提供所有通信的共有函数
"""

from Libs.Exception.CustomExceptions import InvalidParamException
from Libs import Log
import sys
import re
from Libs.Exception.CustomExceptions import UnImplementedException


class CommandBase(object):
"""所有通信类的基类

Args:
ip (str): ip地址
username (str): 用户名
passwd (str): 密码
port (int): 端口号

Attributes:
None

Returns:
None

Raises:
None

Examples:
None

"""

logger = Log.getLogger(__name__)

def __init__(self, ip, username, passwd, port):
    super(CommandBase, self).__init__()


self.ip = ip
self.username = username
self.passwd = passwd
self.port = port
pass


def cmd(self, cmdSpec):
    """声明通用方法接口，给用户下发单独的命令

    Args:
    cmdSpec (dict): cmdSpec = {
    "command": ["", "", ""],
    "input": ["", "", "", ""],
    "waitstr": "",
    "directory": "",
    "timeout": 600,
    "username": "",
    "passwd": ""
    }
    cmdSpec中具体键-值说明：
    command (list): 具体要执行的命令，如show lun general封装成["show",
    "lun", "general"]
    input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号
    -元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参
    -数执行后的期望结束符，第3号元素是2号参数的期望结束符
    waitstr (str): 命令执行后的期望结束符，默认值"[>#]"
    directory (str): 指定命令执行的目录
    timeout (int): 命令执行超时时间，默认600S，不会很精确
    username (str): 建立SSH连接时需要使用的用户名，当命令中出现username或者
    passwd时会自动重新连接
    passwd (str): 建立SSH连接时需要使用的密码，当命令中出现username或者
    passwd时会自动重新连接

    Returns:
    None

    Raises:
    None

    Examples:
    None

    """


raise UnImplementedException("CommandBase's cmd method is unimplemented.")
pass


def connect(self):
    """声明通用方法接口，连接设备

    Args:
    None

    Returns:
    None

    Raises:
    None

    Examples:
    None

    """


raise UnImplementedException("CommandBase's connect method is unimplemented.")
pass


def disConnect(self):
    """声明通用方法接口，断开与设备的连接

    Args:
    None

    Returns:
    None

    Raises:
    None

    Examples:
    None

    """


raise UnImplementedException("CommandBase's disConnect method is unimplemented.")
pass


def discover(protocol=None, ip=None, username=None, password=None, newpassword=None,
             ssh_public_key=None, ssh_private_key=None, port=None, max_session=1,
             debug_username=None, debug_password=None, controlmsg=None, backwardip=None, waitstr=None,
             docker_ip=None, docker_user=None, docker_password=None, docker_port=None, heartbeatIp=None,
             vrf_inner_flag=None):
    """工厂方法，提供所有通信实例的统一初始化

    Args:
    protocol (str|None): 说明需要初始化的通信类型，取值范围["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
    ip (str|None): 通信需要连接的ip地址，Local时不需要
    username (str|None): 建立连接使用的用户名，Local时不需要
    password (str|None): 建立连接使用的密码，Local时不需要
    newpassword (str|None): 新密码(可能登录时需要输入新密码)
    ssh_public_key (str|None): 公钥路径
    ssh_private_key (str|None): 私钥路径
    port (str|None): 端口
    max_session (int|str) : 最大连接数
    debug_username (str|None): debug模式的用户名
    debug_password (str|None): debug模式的密码
    controlmsg (str|None): 控制器信息(针对SVP设备)


    Returns:
    None

    Raises:
    Command子类的实例，根据type的值不同，返回不同对象

    Examples:
    from UniAutos.Command import Command
    local = Command.discover("local")
    result = local.cmd(["dir"])

    """


if protocol:
    protocol = protocol.lower()
if ip is None or username is None:
    raise InvalidParamException
args = [ip, username, password]
if port:
    port = int(port)
args.append(port)
if waitstr:
    args.append(waitstr)
if protocol in ['storssh', 'svpstorssh', 'standssh', 'nasssh', 'fusionssh', 'dswaressh', 'emustorssh',
                'demostorssh', 'svpipmissh', 'rocssh', 'heartbeatssh', 'dockerssh', 'ipenclosuressh',
                'ipenclosureheartbeatssh']:
    from ConnectionPool import ConnectionPool
from HeartbeatConnectionPool import HeartbeatConnectionPool
from IPenclosureConnectionPool import IPenclosureConnectionPool

if not port:
    port = 22
kwargs = dict()
kwargs['ip'] = ip
kwargs['username'] = username
kwargs['password'] = password
kwargs['key'] = ssh_private_key
kwargs['port'] = port
kwargs['maxSession'] = int(max_session)
if protocol == 'standssh':
    return ConnectionPool.createStandSSHPool(**kwargs)

if protocol == 'rocssh':
    kwargs['osConnectInfo'] = {
        'dockerIp': docker_ip,
        'dockerUser': docker_user,
        'dockerPassword': docker_password,
        'dockerPort': docker_port
    }
return ConnectionPool.createRocSSHPool(**kwargs)

if protocol == 'svpipmissh':
    return ConnectionPool.createSvpIpmiPool(**kwargs)

if protocol == 'nasssh':
    kwargs['backwardip'] = backwardip
return ConnectionPool.createNasSSHPool(**kwargs)
if protocol == 'fusionssh':
    kwargs['backwardip'] = backwardip
return ConnectionPool.createFusionSSHPool(**kwargs)
if protocol == 'dswaressh':
    kwargs['backwardip'] = backwardip
return ConnectionPool.createDSwareSSHPool(**kwargs)
if protocol == 'dockerssh':
    return ConnectionPool.createDockerSSHPool(**kwargs)
if protocol == 'ipenclosuressh':
    return IPenclosureConnectionPool.createIPenclosureConnectionPool(**kwargs)
osConnectInfo = dict()
osConnectInfo['ip'] = ip
osConnectInfo['username'] = debug_username if debug_username else 'ibc_os_hs'
osConnectInfo['password'] = debug_password if debug_password else 'Storage@21st'
osConnectInfo['port'] = port
kwargs['osConnectInfo'] = osConnectInfo
if protocol == 'storssh':
    kwargs['newpassword'] = newpassword
return ConnectionPool.createStorSSHPool(**kwargs)
if protocol == 'ipenclosureheartbeatssh':
    kwargs['newpassword'] = newpassword
kwargs['heartbeatIp'] = heartbeatIp
kwargs['vrf_inner_flag'] = vrf_inner_flag
return ConnectionPool.createIpEnclosureHearBeatPool(**kwargs)
if protocol == 'emustorssh':
    return ConnectionPool(ip=ip, username=username, password=password, protocol='emustorssh')
if protocol == 'demostorssh':
    return ConnectionPool(ip=ip, username=username, password=password, protocol='demostorssh')
if protocol == 'heartbeatssh':
# 心跳控制器使用管理控制器的osConnectInfo登录
kwargs['protocol'] = 'heartbeatssh'
kwargs['heartbeatIp'] = heartbeatIp
kwargs['vrf_inner_flag'] = vrf_inner_flag
return HeartbeatConnectionPool(**kwargs)
kwargs['controlmsg'] = controlmsg
if protocol == 'svpstorssh':
    return ConnectionPool.createSVPStorSSHPool(**kwargs)
elif protocol == 'local':
    from UniAutos.Command.Advanced.Local import Local

return Local()
elif protocol == 'telnet':
from UniAutos.Command.Connection.TelnetConnection import TelnetConnection

if len(args) > 3 and not isinstance(args[-1], str):
    args.insert(3, '>')
conn = TelnetConnection(*args)
conn.login()
return conn
elif protocol == 'xmlrpc':
from UniAutos.Command.Advanced.Rpc import Rpc

return Rpc(*args)
elif protocol == "emcstor":
from Connection.EMCConnection import EMCConnection

return EMCConnection(*args)
else:
for cmdClass in ["UniAutos.Command.Advanced.Rpc.Rpc",
                 "UniAutos.Command.StandSSH.StandSSH",
                 "UniAutos.Command.StorSSH.StorSSH",
                 "UniAutos.Command.Telnet.Telnet",
                 "UniAutos.Command.Advanced.Local.Local"]:
    moduleName = cmdClass[0: cmdClass.rfind(".")]
className = cmdClass[cmdClass.rfind(".") + 1: len(cmdClass)]
try:
    __import__(moduleName)
if className == "Local":
    cmdObj = getattr(sys.modules[moduleName], className)()
else:
    if ip is None or username is None or password is None:
        raise InvalidParamException
    else:
    cmdObj = getattr(sys.modules[moduleName], className)(ip, username, password)
if className == "StorSSH":
    cmdSpec = {"command": ["show", "system", "general"]}
else:
    cmdSpec = {"command": ["ping"]}
cmdObj.cmd(cmdSpec)
return cmdObj
except Exception:
CommandBase.logger.error("To communicate with " + className + " Failed")
return None
