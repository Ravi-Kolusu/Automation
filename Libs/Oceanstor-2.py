OceanStor :

#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：控制器类
版权信息：华为技术有限公司，版本所有(C) 2014-2015
"""
from time import time, sleep, strftime
import traceback
import types
import paramiko
import threading
import os,sys
import datetime
import time
import logging
import re,socket
from UniAutos.Device.Host.Controller.ControllerBase import ControllerBase
from UniAutos.Util.Time import sleep
from UniAutos.Util.Codec import split
from UniAutos.Wrapper.Tool.AdminCli.Parser import Parser
import re
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos import Log


class OceanStor(ControllerBase):

"""NasNode初始化

功能说明: Nas Node初始化

Args:
username (str) : 与Nas Node连接时需要使用的用户名
password (str) : 与Nas Node连接时需要使用的密码
params (dict) : params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str),
"type": (str)
}
params键值对说明
protocol (str): 通信协议，key可选，取值范围：["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，key可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，key可选
type (str): 连接的类型

Returns:
返回控制器的实例

Examples:
node = OceanStor.discover(params)

"""
def __init__(self, username, password, params):
super(OceanStor, self).__init__(username, password, params)
self.nodeId = params.get('id')
# self.detail = params.get('detail')
self.role = params.get('role')
self.ipmiIp = ''
self.backwardIp = []
self.platform = ''
self.bakForwardIP = ''
if self.detail:
self.ipmiIp = self.detail.get('ipmiip', '')
self.backwardIp = self.detail.get('backwardip', [])
self.platform = self.detail.get('os')
self.bakForwardIP = self.detail.get('bak_forward_ip')
if self.backwardIp:
self.backwardIp = self.backwardIp.split(',')
self.component = None


log = Log.getLogger(__name__)

@classmethod
def discover(cls, params):
"""获取Nas Node对象

Args：
params (dict): params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str),
"type": (str)
}
params键值对说明:
protocol (str): 通信协议，key可选，取值范围["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，key可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，key可选
type (str): 连接的类型

Returns:
obj控制器对象

Raises:
None

Examples:
controller = OceanStor.discover(params)

Changes:
None

"""
wrappers = []
if 'tool_wrappers' in params:
wrappers = params.pop("tool_wrappers")

obj = super(OceanStor, cls).discover(params)
obj.wrapper_list = wrappers
obj.original_wrapper_list = wrappers
return obj

def run(self, params, sessionType=None):
"""NasNode指定模式运行命令

Args:
sessionType (str): Node命令下发到哪种模式下，取值范围：['admincli', 'debug', 'mml', 'developer', 'diagnose'],
-默认是 'admincli'
Returns:
None.

Raises:
None.

Examples:
controller.run(params, sessionType='developer')
"""
if sessionType:
params['sessionType'] = sessionType
elif 'wrapper' in params:
params['sessionType'] = params["wrapper"].sessionType

return super(OceanStor, self).run(params)

def executeCmd(self, cmdParams, sessionType=None, parser=None, primary=None):
"""执行直接执行命令.
Args:
primary: (str): 定义业务属性主键.
sessionType (str): Node命令下发到哪种模式下，取值范围：['admincli', 'debug', 'mml', 'developer', 'diagnose'],
-默认是 'admincli'
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
if sessionType:
cmdParams['sessionType'] = sessionType
elif 'wrapper' in cmdParams:
cmdParams['sessionType'] = cmdParams["wrapper"].sessionType

res = super(OceanStor, self).run(cmdParams)
if parser is None:
return res['stdout']
elif parser == 'default':
res['stdout'] = split(res['stdout'])
parser = Parser()
if primary:
parser.primary = primary
return parser.standardParser(None, res['stdout'])
return parser(res['stdout'])

def executeMml(self,cmdParams, parser=None, primary=None):
"""直接执行mml命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'mml'
return self.executeCmd(cmdParams, sessionType, parser, primary)

def executeDebug(self,cmdParams, parser=None, primary=None):
"""直接执行mml命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'debug'
return self.executeCmd(cmdParams, sessionType, parser, primary)

def executeCli(self,cmdParams, parser=None, primary=None):
"""直接执行cli命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'admincli'
return self.executeCmd(cmdParams, sessionType, parser, primary)
def executeSftp(self,cmdParams,sftpIp,sftpUser='obsbilling',sftpPassword='OBSCharging8800!'):#OBSCharging8800!
"""
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""] sftp 的执行命令，例如ls 等
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.
sftpUser :sftp 用户名

Returns:
result: 按照parser解析后的结果.
sftpPassword：sftp密码
Raises:
None.

Examples:
None
"""
logstr = ''.join(['sftp ',sftpUser,'@',sftpIp])
input = []
input.append(sftpPassword)
input.append('sftp>')
for cmd in cmdParams.get("command"):
input.append(cmd)
input.append('sftp>')
timeout = cmdParams.get("timeout") if "timeout" in cmdParams.keys() else 30
sshusername = cmdParams.get("username") if "username" in cmdParams.keys() else None
sshpasswd = cmdParams.get("password") if "password" in cmdParams.keys() else None
cmd = {"command":[logstr],"waitStr":"Password","input":input,"timeout":timeout}
if sshusername and sshpasswd:
cmd['username'] = sshusername
cmd['password'] = sshpasswd
return self.executeDebug(cmd)
def executeDiagnose(self,cmdParams, parser=None, primary=None):
"""直接执行cli命令.
Args:
primary: (str): 定义业务属性主键.
cmdParams (dict): cmdSpec = {
"command" : ["","",""]
"input" : ["", "", "", ""],
"waitstr" : "",
"directory" : "",
"timeout" : 600,
"username" : "",
"password" : "",
"checkrc" : ""
}
parser (func): 解析结果的方法.

Returns:
result: 按照parser解析后的结果.

Raises:
None.

Examples:
None
"""
sessionType = 'diagnose'
return self.executeCmd(cmdParams, sessionType, parser, primary)
def canCommunicate(self):
"""Checks to see if we can communicate with remote host by attempting to
send a test command

Args:
None.

Returns:
True|False: True- Able to communicate
False - Unable to communicate

Raises:
None.

Examples:
None.
"""
pass

def changeCommandToBak(self):
"""Nas节点切换链接的cmd对象为备份ip
Args:
None.

Returns:
None.

Raises:
None.

Examples:
node.changeCommandToBak()
"""
from UniAutos.Command.CommandBase import discover
cmd = discover(self.connectionType, self.bakForwardIP, self.username,
self.password, port=self.port, backwardip=self.backwardIp)
self.command = cmd

def changeCommandToMaster(self):
"""Nas节点切换链接的cmd对象为主ip
Args:
None.

Returns:
None.

Raises:
None.

Examples:
node.changeCommandToMaster()
"""
from UniAutos.Command.CommandBase import discover
cmd = discover(self.connectionType, self.localIP, self.username,
self.password, port=self.port, backwardip=self.bakForwardIP)
self.command = cmd

def waitForReboot(self, waitForShutdown=True, timeout=3600):
"""Waits for Node to come back from a reboot

Args:
waitForShutDown (Boolean): (Optional) Set to true to wait for the Node to shutdown first. (Default = True).
timeout (int) : (Optional) Amount of time to wait for reboot, unit is "S"
(Default: 3600).

Returns:
None.

Raises:
None.

Examples:
None.

"""
self.log.debug("Waiting for the controller %s to finish rebooting" % self.localIP)
endTime = time() + timeout

# If specified, wait for the system to shutdown
if waitForShutdown:

self.log.debug("Waiting for the controller %s to complete shutdown" % self.localIP)
self.waitForShutdown(timeout=timeout)
self.log.debug("controller %s is shutdown" % self.localIP)

self.log.debug("Waiting for the controller %s to come up" % self.localIP)
while True:
if self.isReachable():
self.restoreCmdObj()
if self.canCommunicate():
break
sleep(10)
if time() > endTime:
raise UniAutosException("Timed out waiting for reboot [ip: %s]"
"\n(Timed out while waiting for the system to come up" % self.localIP)
pass

def getBootMode(self):
"""获取当前系统的启动模式

Args:
None.

Returns:
normal|rescue： normal mode or rescue mode.

Raises:
None.

Examples:
None.
"""

# 如果能正常下发admin cli命令证明是normal模式， 否则为rescue模式.
pass

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
InvalidParamException: 未指定参数或文件路径.

Examples:
None

Changes:
None

"""
if "path" not in params:
raise InvalidParamException("Have not define dir or file path.")

response = self.run({"command": ["ls", params["path"]], "sessionType": "debug"})
result = True
if response["rc"] != 0:
if re.search("No such file or directory", response["stdout"], re.IGNORECASE):
result = False

return result

def refreshCmdObj(self, ip=None, username=None, password=None, controlmsg={}):
"""更新底层ssh连接使用的ip地址、用户名、密码

Args:
ip (str): ip地址
username (str): 用户名
password (str): 密码
controlmsg (dict): 存放控制器的连接信息，包含key：ip, username, password

Returns:
None

Raises:
None

Examples:
None

"""
self.pauseDispatches("20M")
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% self.nodeId)
loggedOnce = True
sleep(1)
cmdObj = self.getCmdObj()
if controlmsg:
cmdObj.setConnectInfo(ip, username, password, controlmsg)
else:
cmdObj.setConnectInfo(ip, username, password)
self.pauseDispatches('1S')

def restoreCmdObj(self):
"""恢复底层ssh连接使用的连接信息到初始状态

Args:
None

Returns:
None

Raises:
None

Examples:
None

"""
self.pauseDispatches("20M")
loggedOnce = False
while self.isDispatching():
if not loggedOnce:
self.logger.debug("This controller %s is currently dispatching a command."
"Waiting until that dispatch is completed before rebooting"
% self.nodeId)
loggedOnce = True
sleep(1)
cmdObj = self.getCmdObj()
cmdObj.restoreConnectInfo()

self.pauseDispatches('1S')

command_exe_success= "Command executed successfully."


class SSHRemoteOperation:
"""
SSH Remote Operation
2012-6-12
author: caizhao
"""
log = Log.getLogger(__name__)

def __init__(self, host):
self.ip = host.localIP
self.username = host.username
self.password = host.password
self.backFarwardIp = host.backwardIp
self.ssh = paramiko.SSHClient()
self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def _sshConnet(self, exTimeOut=30):
exTimeOut = int(exTimeOut)

try:
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
tryTimeout = 1
maxTry = 3

while tryTimeout exTimeOut:
self.log.info('======execute timeout when login in mysql ,wait for # ===========')
result = 'false'
return result
time.sleep(0.5)

while True:
if chan.send_ready() :
chan.send(loginStr)
time.sleep(0.5)
chan.send(passwd)
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in mysql,wait for send login string ===========')
result = 'false'
return result
time.sleep(0.1)

tempOutput = ''
while tempOutput.find("mysql>") < 0:
if chan.recv_ready():
tempOutput = tempOutput + chan.recv(1024)
if tempOutput.endswith("#") :
result = tempOutput
break
tempOutput = tempOutput.strip()

endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in sftp,wait for /> ===========')
result = 'false'
return result
time.sleep(0.1)

return result
def _loginForCLI(self, chan, exTimeOut=60, user='admin', password='Admin@storage'):
"""
deal with the CLI login information
"""
exTimeOut = int(exTimeOut)
startTime = datetime.datetime.now()
result = 'true'
tempOutput = ''

loginStr = "cd /startup_disk/image/ISM/ism_ap/CLI/ismcli/;./start.sh -u %s -ip 127.0.0.1 -port 8080\n"%(user)
passwd = "%s\n"%(password)
self.log.info(loginStr)
while not tempOutput.endswith("#"):
if chan.recv_ready():
tempOutput = tempOutput + chan.recv(1024)
tempOutput = tempOutput.replace("\b", "")
tempOutput = tempOutput.strip()
self.log.debug("init login:%s"%tempOutput)

endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in CLI,wait for # ===========')
result = 'false'
return result
time.sleep(0.5)

while True:
if chan.send_ready() :
chan.send(loginStr)
time.sleep(0.5)
chan.send(passwd)
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in CLI,wait for send login string ===========')
result = 'false'
return result
time.sleep(0.1)

tempOutput = ''
#while not tempOutput.endswith("/>"):
while tempOutput.find("/>")=0 :
result = tempOutput
break
tempOutput = tempOutput.strip()

endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in CLI,wait for /> ===========')
result = 'false'
return result
time.sleep(0.1)

return result
def _loginForSftp(self,chan,exTimeOut=30,ip='', user='admin', password='Admin@storage'):
"""
登录sftp
ip:sftp ip
user： sftp 用户名
password：sftp 密码
"""
exTimeOut = int(exTimeOut)
startTime = datetime.datetime.now()
result = 'true'
tempOutput = ''

loginStr = "sftp %s@%s\n"%(user,ip)
passwd = "%s\n"%(password)
self.log.info(loginStr)
while not tempOutput.endswith("#"):
if chan.recv_ready():
tempOutput = tempOutput + chan.recv(1024)
tempOutput = tempOutput.replace("\b", "")
tempOutput = tempOutput.strip()
self.log.info("init login:%s"%tempOutput)

endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in sftp ,wait for # ===========')
result = 'false'
return result
time.sleep(0.5)

while True:
if chan.send_ready() :
chan.send(loginStr)
time.sleep(.2)
if chan.recv_ready():
confirm = chan.recv(1024)
if confirm.find('(yes/no)?')>0:
chan.send('yes\n')
time.sleep(0.5)
chan.send(passwd)
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in sftp,wait for send login string ===========')
result = 'false'
return result
time.sleep(0.1)

tempOutput = ''
while tempOutput.find("sftp>")=0:
chan.send('ls')
if tempOutput.endswith("Password: ") :
chan.send(passwd)
if tempOutput.endswith("sftp>") :
break
tempOutput = tempOutput.strip()

endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in sftp,wait for /> ===========')
result = 'false'
return result
time.sleep(0.1)

return result
def _loginForMML(self, chan, port='988', exTimeOut=30):
"""
deal with the MML login information
"""
hostIP = self.backFarwardIp[0]
exTimeOut = int(exTimeOut)
startTime = datetime.datetime.now()
result = 'true'
tempOutput = ''
while not tempOutput.endswith("#"):
if chan.recv_ready():
tempOutput = tempOutput + chan.recv(1024)
tempOutput = tempOutput.replace("\b", "")
tempOutput = tempOutput.strip()
self.log.info("init login:%s" % tempOutput)
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in CLI,wait for # ===========')
result = 'false'
return result
time.sleep(0.5)

loginStr = "cd /opt/huawei/snas/sbin/; killall ./mml; ./mml %s %s"%(hostIP,port)
self.log.info('logstr:',loginStr)

while True:
if chan.send_ready() :
chan.send(loginStr+"\n")
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in MML ===========')
result = 'false'
return result
time.sleep(1)

while not tempOutput.endswith("mml>>>"):
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in MML ===========\n')
self.log.info(endTime,'\n',startTime)
#logging.warn(tempOutput)
self.log.info("===timeout result==",tempOutput)
result = 'false'
return result

if chan.recv_ready():
tempOutput = tempOutput + chan.recv(3048).strip()
tempOutput = tempOutput.strip()
tempOutput = tempOutput.replace("\033[0;39m", "")
tempOutput = tempOutput.replace("\033[0;35m", "")
tempOutput = tempOutput.replace("\033[0;32m", "")
tempOutput = tempOutput.strip()

time.sleep(1)
return result

def _loginForDiagNS(self, chan, exTimeOut=30):
"""
deal with the DoagNS login information
"""
hostIP = self.backFarwardIp[0]
exTimeOut = int(exTimeOut)
startTime = datetime.datetime.now()
result = 'true'
tempOutput = ''

loginStr = "cd /OSM/script/; killall ./diagnose; ./diagnose"
self.log.debug('logstr:', loginStr)

while True:
if chan.send_ready() :
chan.send(loginStr+"\n")
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in diagnose ===========')
result = 'false'
return result
time.sleep(1)

while not tempOutput.endswith("root:/diagnose>"):
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in diagnose ===========\n')
self.log.info(endTime,'\n',startTime)
#logging.warn(tempOutput)
self.log.info("===timeout result==",tempOutput)
result = 'false'
return result

if chan.recv_ready():
tempOutput = tempOutput + chan.recv(3048).strip()
tempOutput = tempOutput.strip()
tempOutput = tempOutput.replace("\033[0;39m", "")
tempOutput = tempOutput.replace("\033[0;35m", "")
tempOutput = tempOutput.replace("\033[0;32m", "")
tempOutput = tempOutput.strip()

time.sleep(1)
return result

def SSHRoStartCommand(self, cmd, exTimeOut=30):
"""
Execute the command on remote machine, and return nothing, use asynchronous mode
"""
exTimeOut = int(exTimeOut)

t = threading.Thread(target=self._cmdThread,args=(cmd,exTimeOut))
t.start()
return "NULL"
def SSHRoOpenSSHConnection(self,exTimeOut=2):
exTimeOut = int(exTimeOut)

tryTimeout = 1
maxTry = 3
while(tryTimeout exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
else:
if len(cmdItem)==1 :
pass
else:
tempOutput = tempOutput.replace(cmdItem,'')
tempOutput = tempOutput.replace('sftp>','')

tempOutput = tempOutput.strip()
tempOutput = re.sub('\r\n:\r\n', '',tempOutput)

output = output + tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
finally:
if chan is not None:
exitTime = 5
while exitTime > 0 :
if chan.send_ready():
self.log.info("send Ctrl+C and exit")
chan.send("\^Cexit\n")
self.log.info("send exit sftp command ")
break
exitTime += 1
time.sleep(1)
chan.close()
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None

self.log.info("=========out:%s==========" % output)
self.log.error( "=========err:%s==========" % err)
return output, err
def SSHRoExecuteMySqlCommand(self,cmd,sqlUser,sqlPassword,exTimeOut=60,splitcha=';'):
output = ""
err = ""
#print splitcha
commandList = cmd.split(str(splitcha))
exTimeOut = int(exTimeOut)+60
starttime = datetime.datetime.now()

try:
if self.ssh is None or self.ssh.get_transport() is None or self.ssh.get_transport().is_active() is False:
self.SSHRoOpenSSHConnection()
chan = None
tryTimeout = 1
maxTry = 3
while chan is None and (tryTimeout exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
else:
if len(cmdItem)==1 :
pass
else:
tempOutput = tempOutput.replace(cmdItem,'')
tempOutput = tempOutput.replace('msql>','')

tempOutput = tempOutput.strip()
tempOutput = re.sub('\r\n:\r\n', '',tempOutput)

output = output + tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
finally:
if chan is not None:
exitTime = 5
while exitTime > 0 :
if chan.send_ready():
self.log.info("send Ctrl+C and exit")
chan.send("\^Cexit\n")
self.log.info("send exit sftp command ")
break
exitTime += 1
time.sleep(1)
chan.close()
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
self.log.info("=========out:%s==========" % output)
self.log.error( "=========err:%s==========" % err)
return output, err
def SSHRoExecuteCommandWithUserPassword(self, cmd, exTimeOut=60,user='root',password='Root@storage'):
"""
Execute CLI command
"""
output = ""
err = ""
commandList = cmd.split(";")
exTimeOut = int(exTimeOut)

try:
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(self.ip, 22, user, password, timeout=0.8)
ssh.get_transport().set_keepalive(30) # This can be useful to keep connections alive over a NAT
chan = ssh.invoke_shell("SSHShellName")
chan.settimeout(exTimeOut)
tempOutput = ''
boolSend = True

for cmdItem in commandList:
tempOutput = ''
if not chan.send_ready():
time.sleep(.5)
if chan.send_ready() and boolSend:
time.sleep(0.5)
boolSend = False
self.log.info('cmdItem :%s',cmdItem)
if "\\004" == cmdItem :
#send Ctrl-D
chan.send("\004")
else:
chan.send(cmdItem + "\n")
time.sleep(0.2)
if not chan.recv_ready():
time.sleep(1)
if chan.recv_ready():
boolSend = True
tempOutput = tempOutput + chan.recv(1024)
self.log.debug("tempOutput in while:%s"%tempOutput)
tempOutput = tempOutput.rstrip()
while not (tempOutput.endswith("#") or tempOutput.endswith(":") or tempOutput.endswith("?") or
tempOutput.endswith(">") or tempOutput.endswith("]") or tempOutput.endswith("(YES|yes|NO|no)")):
tempOutput = tempOutput + chan.recv(1024)
tempOutput = tempOutput.rstrip()
time.sleep (0.2)
output += tempOutput
time.sleep(.5)

except Exception:

err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]"%(self.ip, cmd)
self.log.error(output,err)
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
ssh.close()
if chan is not None:
chan.close()

return output, err

def SSHRoExecCmdWithTimeLimit(self,cmd, exTimeOut=30):
"""
Execute the command on remote machine, and return
remote stdout and stderr before overtime. If overtime return "[overtime]
"""
exTimeOut= int(exTimeOut)

self.log.info("SSHRoExecCmdWithTimeLimit", cmd, exTimeOut)
try:
if self.ssh is None or self.ssh.get_transport() is None or self.ssh.get_transport().is_active() is False:
self.SSHRoOpenSSHConnection()
stdin, stdout, stderr = self.ssh.exec_command(cmd, -1, exTimeOut)
out = "".join(stdout.readlines())
err = "".join(stderr.readlines())

out = out.strip()
err = err.strip()
return out,err
except Exception:
err = traceback.format_exc()
if "timeout" in err:
err = "timeout"
out = "execute command timeout"
else:
out = "execute command error ip:%s,command:%s" % (self.ip, cmd)

# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None

return out, err

def SSHRoExecuteUntilExpected(self, cmd, expected, timeout, exTimeOut=30):
"""Execute Command until meet expected"""
timeout = int(timeout)
exTimeOut = int(exTimeOut)
expected = str(expected)
retryLoopCnt = timeout/exTimeOut + 1
starttime = datetime.datetime.now()

for i in range(0,retryLoopCnt):
out,err = self.SSHRoExecuteCommand(cmd, exTimeOut)
endtime = datetime.datetime.now()
logging.info(out)

if (endtime - starttime).seconds > timeout:
self.log.warn("Execute overtime")
return "overtime"

if type(out)==types.StringType and out.find(expected)>=0 :
self.log.info("true")
return "true"
elif type(out)==types.ListType :
for line in out:
if expected in line:
return "true"

time.sleep(exTimeOut)
self.log.warn("overtime")
return "overtime"


def SSHRoExecuteUntilNull(self, cmd, timeout, exTimeOut=10):
"""Execute Command until Return Null"""
timeout = int(timeout)
exTimeOut = int(exTimeOut)
retryLoopCnt = timeout/exTimeOut + 1
starttime = datetime.datetime.now()

try:
for i in range(0,retryLoopCnt):
out,err = self.SSHRoExecuteCommand(cmd, exTimeOut)
logging.info(out)
logging.info("[ERR:]" + err)
endtime = datetime.datetime.now()
if (endtime - starttime).seconds > timeout:
return "overtime"

if 0 == len(out+err):
return "true"
time.sleep(exTimeOut)
return "overtime"
except Exception:
self.log.error(traceback.format_exc())
return "false"

def SSHPutFilesToRemote(self, srcDirPath, dstDirPath, flag='FILE'):
"""
Put File To Remote Machines
"""
port = 22

dstDirPath.replace('\\','/')
if not dstDirPath.endswith('/'):
dstDirPath += '/'

srcDirPath.replace('\\','/')
if not srcDirPath.endswith('/') and flag !='FILE':
srcDirPath += '/'
transport = None
try :
transport = paramiko.Transport((self.ip, port))
transport.set_keepalive(30) # This can be useful to keep connections alive over a NAT
transport.connect(username=self.username, password=self.password)
sftp = paramiko.SFTPClient.from_transport(transport)
if flag =='FILE':
filename = os.path.basename(srcDirPath)
sftp.put(srcDirPath,dstDirPath+'/'+filename)
return 'true'
else:
for root, dirs, files in os.walk(srcDirPath):
troot = root.replace(srcDirPath,dstDirPath).replace("\\","/")
for dn in dirs:
sftp.mkdir(troot+"/"+dn)

for fn in files:
sftp.put(root+"/"+fn,troot+"/"+fn)
return "true"
except Exception,e:
self.log.error(traceback.format_exc())
return "false"
finally:
if transport:
transport.close()

def SSHGetFilesFromRemote(self,srcDirPath,dstDirPath):
"""get files from remote"""
port = 22

try :
transport = paramiko.Transport((self.ip, port))
transport.connect(username=self.username, password=self.password)
transport.set_keepalive(30) # This can be useful to keep connections alive over a NAT
sftp = paramiko.SFTPClient.from_transport(transport)
files = sftp.listdir(srcDirPath)

for line in files:
srcFilePath = os.path.join(srcDirPath,line)
dstFilePath = os.path.join(dstDirPath,line)
sftp.get(srcFilePath, dstFilePath)
transport.close()
return "true"
except :
return traceback.format_exc()


#added 2014-6-23 for layout check by p00266662
def SSHGetFileFromRemote(self,RemoteFile,LocalFile):
err = ""
out = "false"
try:
port = 22
transport = paramiko.Transport((self.ip, port))
transport.connect(username=self.username, password=self.password)
transport.set_keepalive(30) # This can be useful to keep connections alive over a NAT
sftp = paramiko.SFTPClient.from_transport(transport)
sftp.get(RemoteFile, LocalFile)
transport.close()
out = "true"
except:
err = traceback.format_exc()
self.log.error(err)
finally:
return out,err

def SSHRoExcuteCmdGetSpecifiedContent(self,cmd,key,row,exTimeOut=30):
"""
Excute Cmd Get Specified Content
"""
exTimeOut = int(exTimeOut)

try:
errortag = "linux get nothing but error\n"
out,err = self.SSHRoExecCmdWithTimeLimit(cmd, exTimeOut)
lines = out.split("\n")
for line in lines:
if key in line:
detail = line.split()
if len(detail)>=int(row):
return detail[int(row) - 1]
if len(detail)=0 :
if out.find(expected)>=0 :
self.log.debug('if str true')
return "true"
elif type(out)==types.ListType :
for line in out:
if expected in line:
return "true"
return "false"

def SSHRoRemoveAllInDirectory(self,path, exTimeOut=60):
"""
be used in Teardown after excuting test case
"""
out,err = "",""
delUserCmd ='pkill AT_;groupdel grouptest;userdel usertest -rf;userdel usertest2 -rf;rm /home/usertest* -rf'
out1,err1 = self.SSHRoExecuteCommand(delUserCmd, exTimeOut)
cmd = "cd %s;ls %s |xargs -i rm {} -rf"%(path,path)
self.log.debug("RemoteOperation Command:[%s]"%(cmd))
out,err = self.SSHRoExecuteCommand(cmd, exTimeOut)
err = err.strip()
if err!='' :
cmd = "rm %s* -r -f;"%(path)
self.log.debug("RemoteOperation Command:[%s]"%(cmd))
return self.SSHRoExecuteCommand(cmd, exTimeOut)
else:
return out,err

def SSHRoExecuteCLICommand(self, cmd, exTimeOut=60, CLIuser='admin', CLIpassword='Admin@storage',
YESORNO='YES',StayTime=0,splitcha=";"):
"""
Execute CLI command
"""
output = ""
err = ""
#print splitcha
commandList = cmd.split(str(splitcha))
exTimeOut = int(exTimeOut)+60
starttime = datetime.datetime.now()

try:
if self.ssh is None or self.ssh.get_transport() is None or self.ssh.get_transport().is_active() is False:
self.SSHRoOpenSSHConnection()
#chan = ssh.invoke_shell("CliShellName")
chan = None
tryTimeout = 1
maxTry = 3
while chan is None and (tryTimeout =0:
if len(cmd)=0) or tempOutput.endswith("(y/n)") \
or tempOutput.endswith("--More--"):
if tempOutput.endswith("--More--") and boolSend:
chan.send(" ")
boolSend = False
self.log.info("++++++++++++++send space for --More-- ++++++++++++++++++++")
if (tempOutput.endswith("(press RETURN)") or tempOutput.split('\n')[-1]==':' )and boolSend:
chan.send("\n")
boolSend = False
self.log.info("++++++++++++++send space for --RETURN-- ++++++++++++++++++++")
elif tempOutput.endswith("(y/n)") :
#boolSendNo = False
if chan.send_ready() and boolSend and YESORNO == 'NO':
self.log.info('++++++++send key n for (y/n) ++++++++')
boolSend = False
chan.send("n\n")
elif chan.send_ready() and boolSend and YESORNO == 'YESNO':
self.log.info("===========YESNO++++++++++++++++++++")
boolSend = False
if not boolSendNo:
self.log.info('++++++++send key y for (y/n) ++++++++')
boolSendNo = True
chan.send("y\n")
else:
self.log.info('++++++++send key n for (y/n) ++++++++')
chan.send("n\n")
elif chan.send_ready() and boolSend:
self.log.info('++++++++send key y for (y/n) ++++++++')
boolSend = False
chan.send("y\n")

if chan.recv_ready():
boolSend = True
tempOutput = tempOutput + (chan.recv(1024)).decode("UTF-8")
self.log.debug("628 tempOutput in while:%s"%tempOutput)
time.sleep(0.1)

tempOutput = tempOutput.lstrip()
endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
else:
if len(cmdItem)==1 :
pass
else:
tempOutput = tempOutput.replace(cmdItem,'')
tempOutput = tempOutput.replace('admin:/>','')
tempOutput = tempOutput.replace('cli:/>','')

tempOutput = tempOutput.strip()
tempOutput = re.sub('\r\n:\r\n', '',tempOutput)
tempOutput = re.sub('.*--More--.*\b\b\b\b\b\b\b\b', '',tempOutput)

output = output + tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
if chan is not None:
exitTime = 5
while exitTime > 0 :
if chan.send_ready():
self.log.info("send Ctrl+C and exit")
chan.send("\^Cexit\n")
self.log.info("send exit CLI command ")
break
exitTime += 1
time.sleep(1)
chan.close()

self.log.info("=========out:%s==========" % output)
self.log.error( "=========err:%s==========" % err)
return output, err

def SSHRoExecuteCLICmdGetSpecifiedContent(self,cmd, key, column, exTimeOut=60,
CLIuser='admin', CLIpassword='Admin@storage', splitcha=";"):
"""
"""
out,err = self.SSHRoExecuteCLICommand(cmd, exTimeOut, CLIuser, CLIpassword, "YES", 0, splitcha)

lines = out.split("\n")
for line in lines:
if key in line:
if column == 'LINEVALUES':
return line,err
detail = line.split()
if len(detail)>=int(column):
return detail[int(column) - 1],err
if len(detail) exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
output = output + tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
if chan is not None:
if chan.send_ready() :
killStr = "\nq"
chan.send(killStr + "\n")
time.sleep(1)
chan.close()

self.log.info("out=", output)
self.log.error("err=", err)
return output, err

def SSHRoExecuteMMLCommandWithEnd(self, cmd, endStrList, port='988', exTimeOut=60):
"""
Execute 1 MML command unitil timeout or any str in endStrList(case sensitive) returns.
"""
output = ""
err = ""
exTimeOut = int(exTimeOut)
starttime = time.time()
if isinstance(endStrList, str) and not endStrList:
endStrList = [endStrList]
elif isinstance(endStrList, list):
for strValue in endStrList:
if not strValue.strip():
endStrList.remove(strValue)
if not endStrList:
return '', 'endStrList error'
else:
return '', 'endStrList error'
loginLoop = 1
try:

while loginLoop= 0:

end_mark = True
if chan.recv_ready():
output += chan.recv(4096)
self.log.debug('endstr: [%s] received, mml exit' %endStr)
break
if end_mark:
break
time.sleep(0.2)
endtime = datetime.datetime.now()
if time.time() - starttime > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
except :
err = traceback.format_exc()
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
output = output.replace("\033[0;39m", "")
output = output.replace("\033[0;35m", "")
output = output.replace("\033[0;32m", "")
output = output.strip()
if chan is not None:
if chan.send_ready() :
killStr = "killall ./mml"
chan.send(killStr + "\n")
time.sleep(1)
chan.close()
return output, err

def SSHRoExecuteMMLCmdGetSpecifiedContent(self,cmd, key, column, port='988', exTimeOut=60):
"""
"""
out,err = self.SSHRoExecuteMMLCommand(cmd, port, exTimeOut)

lines = out.split("\n")
for line in lines:
if key in line:
detail = line.split()
if len(detail)>=int(column):
return detail[int(column) - 1],err
if len(detail) exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
output += tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
if chan is not None:
if chan.send_ready() :
killStr = "\nq"
chan.send(killStr + "\n")
time.sleep(1)
chan.close()

self.log.info("out=", output)
self.log.error("err=", err)
return output, err

def SSHRoExecuteDiagNSCmdGetSpecifiedContent(self,cmd, key, column, exTimeOut=60):
"""
"""
out,err = self.SSHRoExecuteDiagNSCommand(cmd, exTimeOut)

lines = out.split("\n")
for line in lines:
if key in line:
detail = line.split()
if len(detail)>=int(column):
return detail[int(column) - 1],err
if len(detail)=int(column):
detaillist.append(detail[int(column) - 1])
else:
err += "expected column is empty"
return "",err
if len(detaillist)== 0:
err += "cannot find the key: %s" % key
return "", err
else:
return detaillist,err

def SSHRoExecuteDbgCommand(self, cmd, exTimeOut=60):
"""
Execute dbg command
"""
output = ""
err = ""
commandList = cmd.split(";")
exTimeOut = int(exTimeOut)
starttime = datetime.datetime.now()

self.log.info("commandList",commandList, self.ip)
try:
tempOutput = ''
output = ''
endString = 'Diagnose>>'

loginLoop = 1
while loginLoop 3 :
output, err ='','login Diagnose failed'
return '','login Diagnose failed'

for cmdItem in commandList:
tempOutput = ''

if chan.send_ready():
self.log.info('cmdItem :%s ',cmdItem)
chan.send(cmdItem + "\n")
while not (tempOutput.endswith("#") or tempOutput.endswith(":") or tempOutput.endswith("Diagnose>>")):
if chan.recv_ready():
tempOutput = tempOutput + chan.recv(2048)
time.sleep(0.2)
tempOutput = tempOutput.replace("\033[0;39m", "")
tempOutput = tempOutput.replace("\033[0;35m", "")
tempOutput = tempOutput.replace("\033[0;32m", "")
#tempOutput = tempOutput.strip()

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break

endtime = datetime.datetime.now()
if (endtime - starttime).seconds > exTimeOut:
self.log.error('======execute timeout===========')
err = 'execute timeout'
break
output = output + tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
# if self.ssh is not None:
# self.ssh.close()
# self.ssh = None
finally:
if chan is not None:
if chan.send_ready() :
killStr = "\nq"
chan.send(killStr + "\n")
time.sleep(1)
chan.close()
self.log.info("out=",output)
self.log.error("err=",err)
return output, err

def _loginForDgb(self,chan, exTimeOut=30):
"""
deal with the DoagNS login information
"""
hostIP = self.ip
exTimeOut = int(exTimeOut)
startTime = datetime.datetime.now()
result = 'true'
tempOutput = ''

loginStr = "cd /opt/huawei/snas_rep/bin; killall ./dbg_client; ./dbg_client"
self.log.info('logstr:',loginStr)

while True:
if chan.send_ready() :
chan.send(loginStr+"\n")
break
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.info('======execute timeout when login in diagnose ===========')
result = 'false'
return result
time.sleep(1)

while not tempOutput.endswith("Diagnose>>"):
endTime = datetime.datetime.now()
if (endTime - startTime).seconds > exTimeOut:
self.log.debug('======execute timeout when login in diagnose ===========\n')
self.log.debug(endTime,'\n',startTime)
#logging.warn(tempOutput)
self.log.debug("===timeout result==", tempOutput)
result = 'false'
return result

if chan.recv_ready():
tempOutput = tempOutput + chan.recv(3048).strip()
tempOutput = tempOutput.strip()
tempOutput = tempOutput.replace("\033[0;39m", "")
tempOutput = tempOutput.replace("\033[0;35m", "")
tempOutput = tempOutput.replace("\033[0;32m", "")
tempOutput = tempOutput.strip()

time.sleep(1)
return result

def SSHRoExecuteDbgCmdGetSpecifiedContent(self,cmd, key, column, exTimeOut=60):
"""
"""
out,err = self.SSHRoExecuteDbgCommand(cmd, exTimeOut)
lines = out.split("\n")
for line in lines:
if key in line and "failed" not in line:
detail = line.split()
if len(detail)>=int(column):
return detail[int(column) - 1],err
if len(detail)=0:
if len(cmd)=0) or \
tempOutput.endswith("(y/n)") or tempOutput.endswith("--More--"):
if tempOutput.endswith("--More--") and boolSend:
chan.send(" ")
boolSend = False
self.log.info("++++++++++++++send space for --More-- ++++++++++++++++++++")
if (tempOutput.endswith("(press RETURN)") or tempOutput.split('\n')[-1]==':' )and boolSend:
chan.send("\n")
boolSend = False
self.log.info("++++++++++++++send space for --RETURN-- ++++++++++++++++++++")
elif tempOutput.endswith("(y/n)") :
#boolSendNo = False
if chan.send_ready() and boolSend and YESORNO == 'NO':
self.log.debug('++++++++send key n for (y/n) ++++++++')
boolSend = False
chan.send("n\n")
elif chan.send_ready() and boolSend and YESORNO == 'YESNO':
self.log.debug("===========YESNO++++++++++++++++++++")
boolSend = False
if not boolSendNo:
self.log.debug('++++++++send key y for (y/n) ++++++++')
boolSendNo = True
chan.send("y\n")
else:
self.log.debug('++++++++send key n for (y/n) ++++++++')
chan.send("n\n")
elif chan.send_ready() and boolSend:
self.log.debug('++++++++send key y for (y/n) ++++++++')
boolSend = False
chan.send("y\n")

if chan.recv_ready():
boolSend = True
tempOutput += (chan.recv(1024)).decode("UTF-8")
self.log.debug("628 tempOutput in while:%s"%tempOutput)
time.sleep(0.1)

tempOutput = tempOutput.lstrip()
if len(cmdItem)==1 :
pass
else:
tempOutput = tempOutput.replace(cmdItem,'')
tempOutput = tempOutput.replace('admin:/>','')
tempOutput = tempOutput.replace('cli:/>','')

tempOutput = tempOutput.strip()
tempOutput = re.sub('\r\n:\r\n', '',tempOutput)
tempOutput = re.sub('.*--More--.*\b\b\b\b\b\b\b\b', '',tempOutput)

output += tempOutput
except :
err = traceback.format_exc()
output = "execute command error! IPAddr:[%s] Command Line:[%s]" % (self.ip, cmd)
finally:
self.log.info("=========out:%s==========" % output)
self.log.error("=========err:%s==========" % err)
return output, err

def CloseCLIConnection(self,chan):
"Close CLI and ssh Connection"
if chan is not None:
exitTime = 5
while exitTime > 0 :
if chan.send_ready():
self.log.debug("send Ctrl+C and exit")
chan.send("\^Cexit\n")
self.log.debug("send exit CLI command ")
break
exitTime -= 1
time.sleep(1)
chan.close()

def FSCLIShowLastEventsequ(self, event, sequence=30000, exTimeOut=60, CLIuser='admin',
CLIpassword='Admin@storage', YESORNO='YES', StayTime=0, splitcha=";",chan=None):
"check instant event sequence"
LoginCLIResult = ""
ssh = ""
result_se_num = ""
se_len = ""
result_sequence = ""
sequence = int(sequence)
try:
if chan == None:
LoginCLIResult,chan = self.SSHRoOpenCLIConnection(exTimeOut,CLIuser, CLIpassword)
result_se_num = self._Binary_Search_Seq(chan,event,sequence,0,YESORNO, StayTime, splitcha)
except Exception,e:
self.log.info(e)
result_se_num = "get instant event sequence failed! LoginCLIResult:[%s] "%(LoginCLIResult)
return result_se_num
finally:
self.CloseCLIConnection(chan)
return result_se_num

def _Binary_Search_Seq(self,chan,event,high,low,YESORNO="YES", StayTime=0, splitcha=';'):
"""
"""
mid = (int(high)+int(low))/2
cmd = "show " + event +" "+ str(mid) + " 100|filterColumn include sequence"
result_sequence = 0
se_len = 0
result_sequence,se_len = self._Get_Instant_Seq_No(chan,cmd, StayTime, splitcha)
if se_len == -1:
high = mid-1
result_sequence = self._Binary_Search_Seq(chan,event,high,low,YESORNO, StayTime, splitcha)
# if se_len < 100:
# return result_sequence
if se_len == 100:
low = mid
high = high*2
result_sequence = self._Binary_Search_Seq(chan,event,high,low,YESORNO, StayTime, splitcha)
return result_sequence

def _Get_Instant_Seq_No(self,chan,cmd, StayTime, splitcha):
""
LastSequence = ""
sequencelist = []
stdout,stderr = self.SSHRoSendCmdtochan(chan, cmd, "YES", StayTime, splitcha)
stdout = stdout.replace("-", "").strip(" ")
sequence_len = 0
if stdout != "" and stderr == "":
if stdout.find(command_exe_success) >= 0:
sequence_len=-1
LastSequence = stdout
else:
sequence_len = len(re.findall(":",stdout))
sequencelist = stdout.replace("sequence", "").replace(":", "").split()
sequencelist = map(eval,sequencelist)
LastSequence = max(sequencelist)

return LastSequence,sequence_len
