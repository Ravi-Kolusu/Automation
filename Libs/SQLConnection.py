#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2016

修改记录: wangaiguo 00251499 created

"""
from SSHConnection import SSHConnection
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.CommandException import CommandException


class SQLConnection(SSHConnection):
"""普通SQL连接

Args:
hostname (str): ip地址
username (str): 用户名
password (str): 密码
dbUser (str): 数据库用户
dbPasswd (str): 数据库用户密码
publickey (str): 密钥
port (str): 端口

Returns:


Raises:


Examples:


Changes:

"""
def __init__(self, hostname, username, password=None, dbUser='sysdba', dbPasswd=None, directory=None, privateKey=None, port=22):
super(SQLConnection, self).__init__(hostname, username, password=password, privateKey=privateKey, port=port)
self.hostUser = username
self.dbUser = dbUser
self.dbPasswd = dbPasswd
self.directory = directory
self.login()

def __del__(self):
self.close()

def login(self):
"""登陆设备

Args:
None

Returns:
None

Raises:
UniAutosException

Examples:


Changes:
2015-12-29 y00292329 Created

"""
if self.transport is None or not self.transport.is_active():
t = self.createClient()
self.transport = t
self.authentication(self.transport)
channel = self.transport.open_session()
channel.get_pty(width=200, height=200)
channel.invoke_shell()
channel.settimeout(10)
self.channel = channel
defaultWaitStr = 'SQL>'
self.waitstrDict = {'normal': defaultWaitStr}
self.status = 'normal'

if self.directory:
self.cmd({"command": ["cd", self.directory], "timeout": 3})

# 如果用户只指定数据库用户名，如：sysasm，使用用户名直接登录直接登录
if self.dbUser == "sysasm":
rsp = self.execCommand('sqlplus / as %s' % self.dbUser, waitstr='SQL>', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % [0])
raise UniAutosException("Connect to database failed!\n%s" % [0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")

# 如果用户未指定数据库用户名或密码，使用默认sysdba直接登录
elif not self.dbPasswd or not self.dbUser:
rsp = self.execCommand('sqlplus / as %s' % "sysdba", waitstr='SQL>', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % [0])
raise UniAutosException("Connect to database failed!\n%s" % [0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")
#add by dwx461793 for longevity 20181225
elif self.dbUser == "root":
self.execCommand('mysql -u root -P 3306 -p ',waitstr='Enter password:', timeout=5)
self.execCommand(self.dbPasswd,waitstr=defaultWaitStr, timeout=5)
# 根据用户指定的用户名密码登录数据库
else:
rsp = self.execCommand('sqlplus', waitstr='Enter user-name', timeout=5)
if not rsp[1]:
raise UniAutosException("Create SQL connection failed.\n"
"Last successful login info:\n"
"login IP:%s username:%s password:%s" % (self.username, self.password))

rsp = self.execCommand(self.dbUser, waitstr='Enter password:', timeout=5)
rsp = self.execCommand(self.dbPasswd, waitstr=defaultWaitStr, timeout=5)

if "SP2-" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % rsp[0])
raise UniAutosException("Connect to database failed!\n%s" % rsp[0])

if "Connected to an idle instance" in rsp[0] or "ORA-" in rsp[0]:
self.logger.error("Connect to database failed!\n%s" % "Connected to an idle instance.")
raise UniAutosException("Connect to database failed!\n%s" % "Connected to an idle instance.")

def cmd(self, cmdSpec):
"""主机上执行SQL命令。added by wangaiguo
Args：
params (dict): cmdSpec = {
"command" : ["","",""],
"waitstr" : "",
"timeout" : 600,
"checkrc" : "",
}

params中具体键-值说明：
command (list): 待执行命令
input (list): 命令执行中交互的参数及期望的结果，如果有交互的参数则0,1号元素成对，2,3号元素成对，以此类推，其中第1号元素是0号参数执行后的期望结束符，第3号元素是2号参数的期望结束符
timeout (int): 命令执行超时时间，默认600S，不会很精确
checkrc (int): 是否检查回显，默认值0，不检查
Returns:
result: 交互式命令的整个执行过程的输出

Raises:
CommandException: 命令执行异常

Examples:
cmdSpec = {
"command": ["help"],
"timeout": 600,
}
result = self.runSQL(cmdSpec)

"""

defaultWaitstr = self.waitstrDict.get('normal', 'SQL>')
result = {"rc": None, "stderr": None, "stdout": ""}
# 2017.5.30:修改SQL命令执行的超时时间，避免SQL命令未执行完就继续后续动作，暂定2H，基本满足SLOB测试需求
# 这里只是在用户遗漏timeout参数的一个容错手段
timeout = cmdSpec.get('timeout', 5)#modified by dwx461793 for longevity 20181225
waitstr = cmdSpec.get('waitstr', defaultWaitstr)
checkrc = cmdSpec.get("checkrc", 0)

# 获取交互输入列表
cmdstr = " ".join(cmdSpec["command"])

# 用户输入命令做格式检查，如果未包含";"，补齐后下发命令
if cmdstr[-1] != ";":
cmdstr += ";"

cmdList = []
cmdList.append([cmdstr, waitstr])
if cmdSpec.get('input'):
inputLen = len(cmdSpec['input'])
for i in range(0, inputLen, 2):
wStr = cmdSpec['input'][i + 1] if (i + 1) != inputLen else defaultWaitstr
cmdList.append([cmdSpec['input'][i], wStr])
errorCmd = False
# 是否默认输入y
confirm = cmdSpec.get('confirm', False)
if confirm is True:
confirm = 'y'

recv_return = cmdSpec.get("recv_return", True)
if recv_return:
# 正常下发命令并接收回显
for cmd in cmdList:
tmpresult, isMatch, matchStr = self.execCommand(cmd[0], cmd[1] + r'|y/n|' + waitstr, timeout)

while matchStr == 'y/n' and confirm:
result["stdout"] += tmpresult
tmpresult, isMatch, matchStr = self.execCommand(confirm, cmd[1] + r'|y/n|' + waitstr,
timeout)
if tmpresult:
result["stdout"] += tmpresult

if not checkrc and isMatch and matchStr and ("SP2-" in tmpresult or "ORA-" in tmpresult):
errorCmd = True

if errorCmd:
result["stdout"] += tmpresult
result["rc"] = 1
self.logger.warn("Wrong command:\n[command:%s][error:%s]" % (cmd[0], tmpresult))
# 2017.5.31:取消命令执行失败抛异常，由用户自行判断命令执行是否异常。避免工具脚本使用异常。
# raise CommandException("Wrong command:\n[command:%s][error:%s]" % (cmd[0], tmpresult))

else:
# 只发命令，不接收回显
for cmd in cmdList:
self.send(cmd[0], timeout)
result["stdout"] = ""

return result
