
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
功 能：Unix类操作系统的基类，提供Unix类操作系统的公共接口.
"""

import re
import datetime
import random
import os
import copy
import time

from UniAutos.Util.Units import KILOBYTE
from UniAutos.Device.Host.HostBase import HostBase
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Exception.FileNotFoundException import FileNotFoundException
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.UnImplementedException import UnImplementedException
from UniAutos.Util.TypeCheck import validateParam


class Unix(HostBase):

"""Unix基类初始化

功能说明: Unix基类初始化

Args:
username (str): 账号名
password (str): 账号密码
params (dic): params = {
"protocol": (str),
"port": (str),
"ipv4_address": (str),
"ipv6_address": (str),
"os": (str),
"type": (str)
}
params键值对说明
protocol (str): 通信协议，key可选，取值范围["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，key可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，key可选
type (str): 连接的类型

Returns:
obj具体unix的操作系统实例

Examples:
None.

"""
def __init__(self, username, password, params):
super(Unix, self).__init__(username, password, params)
self.os = 'Unix'
self.rootDisk = None
self.systemInfo = None
self.version = None
pass

@classmethod
def discoverClass(cls, command):
"""通过下发命令查询具体操作系统类型返回对应的实例

Args：
command (obj): 可以用于下发命令的对象

Returns:
obj返回对应操作系统的对象

Raises:
CommandException

Examples:
obj = Unix.discoverClass(command)

Changes:
None

"""
if not re.match(r'(UniAutos.Device.Host)', str(cls.__module__), re.IGNORECASE):
return cls

# 针对SVP做特殊处理，检测到是SVP时不在去下发命令uname获取主机的类型
classStr = str(cls.__module__) + "."+ str(cls.__name__)
if re.match(r'(UniAutos.Device.Host.Svp.Svp)|(UniAutos.Device.Host.SvpIpmi.SvpIpmi)', classStr, re.IGNORECASE):
return classStr

result = command.cmd({"command": ["uname"]})
if result is None or (isinstance(result, dict) and result["rc"]):
raise CommandException("Unable to run uname. Must not be a Unix-like system.")
if isinstance(result, dict):
response = result["stdout"]
elif isinstance(result, str):
response = result
else:
raise CommandException("Unable to run uname. Must not be a Unix-like system.")

if re.search("linux", response, re.IGNORECASE):
return "UniAutos.Device.Host.Linux.Linux"
elif re.search("solaris|Sun", response, re.IGNORECASE):
return "UniAutos.Device.Host.Solaris.Solaris"
elif re.search("HP-UX", response, re.IGNORECASE):
return "UniAutos.Device.Host.Hpux.Hpux"
elif re.search("Aix", response, re.IGNORECASE):
return "UniAutos.Device.Host.Aix.Aix"
elif re.search("Darwin", response, re.IGNORECASE):
return "UniAutos.Device.Host.Mac.Mac"
elif re.search("OpenStack", response, re.IGNORECASE):
return "UniAutos.Device.Host.OpenStack.OpenStack"
elif re.search("vmkernel", response, re.IGNORECASE):
return "UniAutos.Device.Host.Hypervisor.Esx.Esx"
else:
raise CommandException("Unable to run uname. Must not be a Unix-like system.")

def getPath(self):
"""获取当前路径

Args:
None

Returns:
currentPath (str): 当前路径

Raises:
None

Examples:
hostObj.getPath()
OutPut:
>"/root"

Changes:
None

"""
response = self.run({"command": ["pwd"]})
if response["rc"] != 0:
raise CommandException("Get Current Path Failed.")
lines = self.split(response["stdout"])
for line in lines:
if re.match(r'^/', line):
return line

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

response = self.run({"command": ["sh", "-c", "ls", params["path"]]})
result = True
if response["rc"] != 0:
#self.logger.debug(response['stderr'])
#if re.search("No such file or directory|没有那个文件或目录", response["stderr"], re.IGNORECASE):
result = False

return result

def getSystemInfo(self):
"""获取Unix操作系统信息

Args:
None

Returns:
syncSystemInfo (dict): Unix操作系统信息, 键值对说明如下:
host_name (str): 主机名，例如 'localhost@huwei.com'
os_type (str): 操作系统类型, 例如 'GNU/Linux', 'Solaris'
kernel_name (str): 内核名, 例如 'Linux', 'SunOS'
kernel_release (str): 内核发布版本,　例如 '2.6.18-8.el5', '5.10'
kernel_version (str): 内核版本信息,　例如 'SMP Tue Dec 6 16:15:40 GMT 2011' , 'Generic_127111-01'
hardware_name (str): 硬件名,　例如　'x86_64 ', 'sun4u'
processor_type (str): 处理器类型,　例如　'x86_64', 'sparc'
hardware_platform (str): 硬件平台,　例如　'GNU/Linux', 'SUNW,Sun-Fire-V490'

Raises:
CommandException: 获取系统信息命令执行失败.

Examples:
unixObj.getSystemInfo()
Output:
{'host_name': 'localhost@huwei.com',
'os_type': 'Solaris',
'kernel_name': 'SunOS',
'kernel_release': '5.10',
'kernel_version': 'Generic_127111-01'
'hardware_name': 'sun4u'
'processor_type' : 'sparc'
'hardware_platform' : 'SUNW,Sun-Fire-V490'}

"""

if self.systemInfo:
return self.systemInfo
syncSystemInfo = {}
response = self.run({"command": ["sh", "-c", 'uname -a']})
if response["rc"] != 0:
raise CommandException("Cannot get the system information")
lines = self.split(self.trim(response["stdout"]))
for line in lines:
if re.search(r'uname|root@#>', line):
continue
originalInfo = line.split()
if len(originalInfo) 1:
try:
format_time = lines[0].split(".")
ts = time.strptime(format_time[0], "%Y-%m-%d %H:%M:%S")
modifyTimeStamp = time.mktime(ts)
except Exception as ex:
self.logger.warn(lines, str(ex))
tmpInfo = {"is_dir": True if directory == "d" else False,
"last_modified": {"time": fileTime, "date": date},
"size": size + "Bytes",
"writeable": True if writeable == "w" else False,
"executable": True if re.match(r'x|s|t', writeable) else False,
"readable": True if readable == "r" else False,
"modifyTimeStamp": modifyTimeStamp if modifyTimeStamp else ""}

if iNode:
tmpInfo["inode"] = iNode
if blockCount:
tmpInfo["allocated_size"] = blockCount + "Blocks"
listFileInfo[filename] = tmpInfo
return listFileInfo

def deleteFile(self, filePath):
"""删除指定的文件

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.

Returns:
None.

Raises:
InvalidParamException: 输入的文件为"/"目录.
CommandException: 删除文件失败.

Examples:
hostObj.deleteFile("/root/1.txt")

"""
if not self.doesPathExist({"path": filePath}):
return
if filePath == "/":
raise InvalidParamException("Attempting to delete root is not allowed.")
response = self.run({"command": ["sh", "-c", "rm", "-rf", filePath]})
if response["rc"] != 0:
raise CommandException("Unable to delete %s" % filePath)

def createFile(self, filePath, username=None, password=None):
"""创建指定的文件

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.

Returns:
None.

Raises:
CommandException: 创建文件失败.

Examples:
hostObj.createFile("/root/1.txt")

"""
userOptions = {}
param = {"command": ["sh", "-c", "touch", filePath]}
if username and password:
userOptions = {"username": username,
"password": password}
param.update(userOptions)
response = self.run(param)
if response["rc"] != 0:
raise CommandException("Problem creating file: %s\n Error: %s" % (filePath, response["stderr"]))

def writeToFile(self, filePath, contents, append=True):
"""向文件中写类容

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.
contents (str): 向文件写的类容
append (bool): (可选参数)是否向文件中追加，默认True

Returns:
None.

Raises:
CommandException: 创建文件失败.

Examples:
hostObj.writeToFile(filePath="/root/1.txt",contents="aaaa")

"""
userOptions = {}
type = ">"
if append:
type = ">>"
param = {"command": ["sh", "-c", "echo", "\'%s\'" % contents, type, filePath]}
response = self.run(param)
if response["rc"] != 0:
raise CommandException("Problem creating file: %s\n Error: %s" % (filePath, response["stderr"]))

def renameFile(self, file, newString, originalString=None):
"""重命名文件

Args:
file (str): 文文件名， 若存在特殊字符需要加转义字符.
newString (str): 新名称
originalString (str): 老的名称，默认为文件名

Returns:
None.

Raises:
CommandException: 创建文件失败.

Examples:
hostObj.renameFile(file="a",newString="aaaa")

"""
userOptions = {}
oldName = file
if originalString != None:
oldName = originalString
param = {"command": ["sh", "-c", "rename", oldName, newString, file]}
response = self.run(param)
if response["rc"] != 0:
raise CommandException("Problem rename file: %s\n Error: %s" % (file, response["stderr"]))

def truncateFile(self, file, size):
"""缩减扩大文件

Args:
file (str): 文文件名， 若存在特殊字符需要加转义字符.
size (str): 大小

Returns:
None.

Raises:
CommandException: 缩减扩大文件失败.

Examples:
hostObj.renameFile(file="a",newString="aaaa")

"""
userOptions = {}
param = {"command": ["sh", "-c", "truncate", file, "-s", size]}
response = self.run(param)
if response["rc"] != 0:
raise CommandException("Problem truncate file: %s\n Error: %s" % (file, response["stderr"]))

def ddFile(self, filePath, bs, count, inputFile='/dev/zero', skip=None, seek=None, conv=None, oflag=None, iflag=None, bg=True, timeout=None):
"""创建指定的文件

Args:
filePath (str): 文件路径，包含文件名， 若存在特殊字符需要加转义字符.
inputFile (str): 输入文件名，默认为/dev/zero
bs (str): 读写块大小
count (str): 块个数
seek (str): 写的偏移数
conv (str): 是否覆盖写
timeout (int|str): 命令执行的超时时间
Raises:
CommandException: 创建文件失败.

Examples:
hostObj.ddFile("/root/1.txt"， "1", "5")

"""
userOptions = {}
param = {"command": ["sh", "-c", "dd", "if="+inputFile, "of="+filePath, "bs="+bs, "count="+str(count)]}
if skip is not None:
param['command'].append('skip=%s' % str(skip))
if conv is not None:
param['command'].append('conv=%s' % str(conv))
if seek is not None:
param['command'].append('seek=%s' % str(seek))
if oflag is not None:
param['command'].append('oflag=%s' % str(oflag))
if iflag is not None:
param['command'].append('iflag=%s' % str(iflag))
if bg:
param['command'].append('&')
if timeout is not None:
param.update({"timeout": int(timeout)})
response = self.run(param)
if response["rc"] != 0:
raise CommandException("Problem creating file: %s\n Error: %s" % (filePath, response["stderr"]))
return response

def setFileAccessPermissions(self, user, permission, path):
change = user + permission
response = self.run({"command": ["sh", "-c", "chmod", change, path]})

if response["rc"] != 0:
raise CommandException("Problem copying file: %s into %s\n Error: %s"
% (path, response["stderr"]))

def renameDirectory(self, path, newPath):
response = self.run({"command": ["sh", "-c", "rm", "-rf", path, newPath]})

if (response["rc"] != 0):
return 0
else:
return 1

def renameDirecTory(self, path, newPath):
"""重命名目录

Args:
path (str): 源目录名.
newPath (str): 修改目录名.

Raises:
CommandException: 重命名目录失败.

Examples:
hostObj.renameDirecTory("/mnt/dir1", "/mnt/dir2")

"""
response = self.run({"command": ["sh", "-c", "mv", "-f", path, newPath]})

if (response["rc"] != 0):
raise CommandException("Problem rename directory: %s rename %s\n Error: %s"
% (path, newPath, response["stderr"]))

def copyFile(self, source, destination):
"""删除指定的文件

Args:
source (str): 源文件路径，包含文件名，若存在特殊字符需要加转义字符.
destination (str): 目的文件目录或文件的全路径，若存在特殊字符需要加转义字符.

Raises:
CommandException: 拷贝文件失败.

Examples:
hostObj.copyFile("/root/1.txt", "/root/Desktop/2.txt")
or
hostObj.copyFile("/root/1.txt", "/root/Desktop")

"""
if source == destination:
return

response = self.run({"command": ["sh", "-c", "cp", "-f", source, destination]})

if response["rc"] != 0:
raise CommandException("Problem copying file: %s into %s\n Error: %s"
% (source, destination, response["stderr"]))

def cutFile(self, source, destination):
"""剪切文件

Args:
source (str): 源文件路径，包含文件名，若存在特殊字符需要加转义字符.
destination (str): 目的文件目录或文件的全路径，若存在特殊字符需要加转义字符.

Raises:
CommandException: 剪切文件失败.

Examples:
hostObj.cutFile("/root/1.txt", "/root/2.txt")

"""
if source == destination:
return

response = self.run({"command": ["sh", "-c", "mv", source, destination]})

if response["rc"] != 0:
raise CommandException("Problem cut file: %s into %s\n Error: %s"
% (source, destination, response["stderr"]))

def createHardlink(self, file1, file2):
"""创建硬链接

Args:
file1 (str): 源文件
file2 (str): 目的文件

Raises:
CommandException: 创建硬链接失败

Examples:
hostObj.createHardlink("/root/file1", "/root/file2")
"""
if file1 == file2:
return
response = self.run({"command": ["sh", "-c", "ln", file1, file2]})
if response["rc"] !=0:
raise CommandException("Problem creating: %s to %s\n Error: %s"
% (file1, file2, response["stderr"]))

def createSoftlink(self, file1, file2):
"""创建硬链接

Args:
file1 (str): 源文件
file2 (str): 目的文件

Raises:
CommandException: 创建软链接失败

Examples:
hostObj.createSoftlink("/root/file1", "/root/file2")
"""
if file1 == file2:
return
response = self.run({"command": ["sh", "-c", "ln", "-s", file1, file2]})
if response["rc"] !=0:
raise CommandException("Problem creating: %s to %s\n Error: %s"
% (file1, file2, response["stderr"]))

def copyDirectory(self, source, destination):
"""删除指定的文件

Args:
source (str): 源目录，若存在特殊字符需要加转义字符.
destination (str): 目的目录，若存在特殊字符需要加转义字符.

Raises:
CommandException: 拷贝目录失败.

Examples:
hostObj.copyDirectory("/root", "/root/Desktop")

"""
if source == destination:
return

response = self.run({"command": ["sh", "-c", "cp", "-rf", source, destination]})
if response["rc"] != 0:
raise CommandException("Problem copying: %s to %s\n Error: %s"
% (source, destination, response["stderr"]))

def readFile(self, filePath):
"""读取文件内容并返回

Args:
filePath (str): 文件全路径，若存在特殊字符需要加转义字符.

Returns:
lines (list): 文件内容的列表, 列表单个元素内容为文件的一行.

Raises:
CommandException: 拷贝目录失败.

Examples:
hostObj.copyDirectory("/root", "/root/Desktop")

"""
response = self.run({"command": ["sh", "-c", "cat", filePath]})
if response["rc"] != 0:
raise CommandException("Read file %s failed" % filePath)
lines = self.split(response["stdout"])
for line in lines:
if re.search(r'cat', line):
lines.pop(lines.index(line))
lines.pop()
return lines

def tarFile(self, filename, target_path):
"""解压tgz文件中的指定文件到指定的目录.
Args:
target_path (str): the extract target directory, do not end with '/'.
filename (str): need to extract filename.

Raises:
CommandException: 解压失败

"""
response = self.run({'command': ['tar', '-xzf', '%s' % filename, '-C', '%s' % target_path]})
if response["rc"] != 0:
raise CommandException("Problem tarFile. Error: %s" % response['stderr'])

def shutdown(self):
pass

def reboot(self, delay=5, wait=False, timeout=None, mountPath=None):
pass

def getVersion(self):
"""获取操作系统内核版本

Args:
None.

Returns:
self.version (str): 操作系统版本.

Raises:
None.

Examples:
None.
"""
response = self.run({"command": ["sh", "-c", "uname -r"]})
if response["rc"] != 0:
raise CommandException("Get Os Version Failed.")

lines = self.split(self.trim(response["stdout"]))
for line in lines:
if re.search(r'uname', line):
continue
versionMatch = re.match(r'(\S+)', line)
if versionMatch:
self.version = versionMatch.group(1)
return self.version

def getArchitecture(self):
"""查看系统的架构信息

Args:
None.

Returns:
self.architecture (str): 系统架构名称.

Raises:
None.

Examples:
None.

"""
if self.architecture:
return self.architecture
response = self.run({"command": ["sh", "-c", "uname -m"]})
if response["stdout"]:
lines = self.split(response["stdout"])
for line in lines:
if re.search(r'uname', line) or re.search(r'root', line):
continue
archMatch = re.search(r'(\S+)', line)
if archMatch:
self._setArchitecture(archMatch.group(1))
return self.architecture

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
raise InvalidParamException("Tried creating a random folder in %s , "
"but %s does not exist!" % (baseDir, baseDir))
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
randomDir = self.catDir(baseDir, output)
self.logger.info("The want to create directory is: %s" % randomDir)
if self.doesPathExist({"path": randomDir}) and var > 0:
self.logger.info("The want to be create directory is exist, but template have some '%c 'or '%d', "
"generate again.")
return self._createRandomDirectory(baseDir, template)
elif self.doesPathExist({"path": randomDir}):
# intendedDir = self.catDir(baseDir, output)
raise UniAutosException("There is no randomness in template, and %s is taken." % randomDir)
else:
# randomDir = self.catDir(baseDir, output)
self.createDirectory(randomDir)
return randomDir

def getProcessMemoryUsage(self, process=None):
"""获取当前主机指定进程的内存信息

Args:
process (list): 指定的进程列表, 默认为None，为None时返回所有的进程信息.

Returns:
tmpInfo (dict): 指定进程或所有进程的内存信息, 键值对说明如下:
{
swap_memory_usage (str): swap分区内存使用率.
total_memory_usage (str): 总的内存使用率.
process (str): 各进程的内存使用率.
}
Raises:
CommandException: 命令执行失败返回.

Examples:
hostObj.getProcessMemoryUsage()
hostObj.getProcessMemoryUsage("sshd")
hostObj.getProcessMemoryUsage(["sshd","ls"])

"""
response = self.run({"command": ["sh", "-c", "top -bn 1"], 'check_rc': 1})
if response["rc"] != 0:
raise CommandException("Get Mem Usage info Failed")

memInfo = self.split(response["stdout"])
tmpInfo = {}
processIDIndex = 0
memoryIndex = 0
processNameIndex = 0
for line in memInfo:
swapMatch = re.search(r'Swap:\s+\d+\w+\s+total,\s+(\d+\w+)\s+used', line)
memMatch = re.search(r'Mem:\s+\d+\w+\s+total,\s+(\d+\w+)\s+used', line)
if swapMatch:
tmpInfo["swap_memory_usage"] = swapMatch.group(1) + "B"
continue
elif memMatch:
tmpInfo["total_memory_usage"] = memMatch.group(1) + "B"
continue
elif re.search(r'PID\s+USER', line):
line = self.trim(line)
headArray = re.split(r'\s+', line)
for index in range(0, len(headArray)):
if re.match(r'^PID$', headArray[index]):
processIDIndex = index
elif re.match(r'^RES$', headArray[index]):
memoryIndex = index
elif re.match(r'^COMMAND$', headArray[index]):
processNameIndex = index
elif re.match(r'^\s+\d+', line):
line = self.trim(line)
proArray = re.split(r'\s+', line)
processName = proArray[processNameIndex]
if process and isinstance(process, str):
matchInfoList = map(lambda proc: re.search(r'' + str(proc) + '', processName), [process])
if not re.search(r'SRE', str(matchInfoList)):
continue
elif process and isinstance(process, list):
matchInfoList = map(lambda proc: re.search(r'' + str(proc) + '', processName), process)
if not re.search(r'SRE', str(matchInfoList)):
continue
processID = proArray[processIDIndex]
processMem = proArray[memoryIndex]
if re.match(r'^\d+$', processMem):
processMem += KILOBYTE
else:
processMem += "B"
tmpInfo["%s[%s]" % (processName, processID)] = processMem
return tmpInfo

def getCpuUsage(self):
"""获取当前主机的详细CPU使用信息

Args:
None.

Returns:
tmpInfo (dict): 指当前主机的CPU使用信息, 键值对说明如下:
{
total_usage (str): 总的CPU使用率.
CORE[x] (str): 各CPU核的使用率.
}
Raises:
CommandException: 命令执行失败返回.

Examples:
hostObj.getCpuUsage()

"""
response = self.run({"command": ["sh", "-c", "mpstat -P ALL 1 1"], 'check_rc': 1})
if response["rc"] != 0:
raise CommandException("Get Cpu Usage info Failed, maybe not install mpstat.")
cpuArray = self.split(response["stdout"])
tmpInfo = {}
coreNumberIndex = 0
idleUsageIndex = 0
for line in cpuArray:

if re.search(r'\s+CPU\s+', line):
headArray = re.split(r'\s+', line)
for index in range(0, len(headArray)):
i = headArray[index]
if re.match(r'^CPU$', headArray[index]):
coreNumberIndex = index
elif re.search(r'idle', headArray[index]):
idleUsageIndex = index
continue

elif re.search(r'\s+all\s+', line):
allUsage = re.split(r'\s+', line)
tmpInfo["total_usage"] = "%.2f" % (100 - float(allUsage[idleUsageIndex]))
continue

elif re.search(r'^\d+\w+', line) and not re.search(r'^Average', line):
processorArray = re.split(r'\s+', line)
a = processorArray[idleUsageIndex]
c = "core%s" % (int(processorArray[coreNumberIndex]) + 1)
d = float(100 - float(a))
tmpInfo["core%s" % (int(processorArray[coreNumberIndex]) + 1)] =\
"%.2f" % float(100 - float(processorArray[idleUsageIndex]))

elif re.search(r'(\w+|\s+)+\w+', line) and re.search(r'^Average', line):
break
return tmpInfo

def getIpAddress(self, interface=None, ipType=None):
"""获取ip地址

Args:
interface (str): 接口
ipType (str): ip地址类型

Returns:
ip地址的值

Raises:
None

Examples:
None

"""
addrType = ipType + '_address'
if not interface:
if hasattr(self, addrType):
return self.addrType

intHash = self.getNetworkInfo()
if not interface:
for interface in intHash['interfaces']:
if isinstance(intHash['interfaces'][interface], dict):
return intHash['interfaces'][interface][addrType]

if interface not in intHash['interfaces'] or not intHash['interfaces'][interface]:
raise InvalidParamException("Interface %s does not exist on this host" %interface)

if addrType not in intHash['interfaces'][interface] or not intHash['interfaces'][interface][addrType]:
raise InvalidParamException("Interface %s does not have an IP Address or the interface is down." %interface)

return intHash['interfaces'][interface][addrType]

def getNetworkInfo(self):
raise UnImplementedException(self.__class__.__module__ + "." + self.__class__.__name__+".getNetworkInfo")
pass


def findPath(self, name):
"""通过下发find命令查找指定的路径或者文件

Args:
name (str): 需要查找指定的路径或者文件

Returns:
path (list): 查找到路径返回值

Raises:
None

Examples:
None

"""
response = self.run({"command": ["sh", "-c", "find", "/", "-name" ,name]})
pattern = "No such file or directory"
result = []
if not response["stdout"] or re.match(pattern, response["stdout"], re.IGNORECASE):
host = self.getHostname()
msg = "%s was not found in %s's" % (name, host)
raise FileNotFoundException(msg)
lines = self.split(self.trim(response["stdout"]))
for line in lines:
if re.search(r'' + str(name) + '', line):
result.append(line)
return result

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
result = []
response = self.run({"command": ['sh','-c', 'grep', '-F', '\'%s\''%string, path]})

if response['stdout']:
result = self.split(response['stdout'])

return result

def getPortInformation(self, ethPort):
"""查询指定文件中是否包含string，包含则返回文件内容列表.

Args:
ethPort (str): 需要查询的ethPort口。

Returns:
result (dict): 查询返回的结果

Raises:
None.

Examples:
None.

"""
result = {}
response = self.run({"command": ['sh','-c', 'ethtool', ethPort]})

if response['stdout']:
tempList = self.split(response['stdout'])
if len(tempList) != 0:
for item in tempList:
temp = re.search('(.*):(\s+)(.*)', item)
if temp:
key = re.sub('\t', '', temp.groups()[0])
result[key] = temp.groups()[2]
if key == 'Supported link modes' or key == 'Advertised link modes':
curIndex = tempList.index(item)
result[key] = result[key] + ' ' + re.sub('\t', '', tempList[curIndex+1])
result[key] = result[key] + ' ' + re.sub('\t', '', tempList[curIndex+2])

return result

def setIpAddress(self, kwargs):
"""设置IP地址

Args:
*ethPort (str) eth接口 例：eth0， eth1
*ip (str) ip 例：192.168.1.1
*mask (str) 子网掩码 例：255.255.255.0


Returns:
None.

Raises:
raise CommandException("Get ip information failed. ip: %s" % kwargs["ip"])
raise CommandException("Get ethPort information failed. ethPort: %s" % kwargs["ethPort"])
raise CommandException("Get mask information failed. mask: %s" % kwargs["mask"])
raise InvalidParamException("The value of eth0 or value of netmask is invalid. ethPort: %s, mask: %s" % (kwargs["ethPort"], kwargs["mask"]))
raise CommandException("Execute Command Failed.")
raise CommandException("Execute Restart Command Failed.")

Examples:
params = {"ethPort":"eth0", "ip":"192.168.1.1", "mask":"255.255.255.0"}
hostObj.setIpAddress(params)

Notes:

"""
#判断获取的参数中中否有ip值
if "ip" not in kwargs:
raise CommandException("Get ip information failed. ip: %s" % kwargs["ip"])

#判断获得的参数表中是否有ethPort
if "ethPort" not in kwargs:
raise CommandException("Get ethPort information failed. ethPort: %s" % kwargs["ethPort"])

#判断获取的参数中是否有mask
if "mask" not in kwargs:
raise CommandException("Get mask information failed. mask: %s" % kwargs["mask"])

#判断关键字”ip“或”mask“的值是否合法
if not (isinstance(kwargs["ethPort"], str)) or not (isinstance(kwargs["mask"], str)):
raise InvalidParamException("The value of eth0 or value of netmask is invalid. ethPort: %s, mask: %s" % (kwargs["ethPort"], kwargs["mask"]))

#执行命令
response = self.run({"command": ["sh", "-c", "ifconfig", kwargs["ethPort"], kwargs["ip"], "netmask", kwargs["mask"]]})
#判断命令是否执行成功
if response["rc"] != 0:
raise CommandException("Execute Command Failed.")

def scp(self, ip, remotePath, localPath, type, username='ibc_os_hs', password='Storage@21st', timeout=600):
"""远端拷贝

Args:
ip (str)： 远端设别ip地址
username (str): 远端设备用户名
timeout (str): 超时时间,默认为600s
remotePath (str): 远端文件路径或者目录
localPath (str): 本地文件路径或者目录
type (str): 拷贝到本地或者拷贝到远端，取值范围：input、output

Raises:
CommandException: 拷贝目录/文件失败.

Examples:
self.host.scp(ip="8.46.102.190", remotePath='/tmp', localPath='/tmp/sd_tmp_partitions', type='output', username='ibc_os_hs', password='Storage@21st')
Changes:
2018-03-19 wwx271515 去掉input和output 中输入yes或password前的sh-c
2018-03-28 wwx271515 适配拷贝文件名存在空格等特殊字符无法正常拷贝情况，localPath采用''屏蔽空格特殊字符，remotePath采用''+\进行空格处理
"""
if ' ' in remotePath:
remotePath = remotePath.replace(' ','\ ')
remoteFilePath = username + '@' + ip + ':' + "'%s'"%remotePath
# 远端拷贝到本地
if type == 'input':
response = self.run({"command": ["sh","-c","scp", remoteFilePath, "'%s'"%localPath], "timeout": timeout,
"waitstr": "yes\/no|assword"})
if response['stdout']:
if 'continue' in response['stdout']:
self.run({"command": ['yes'], "waitstr": "assword", "timeout": timeout,
"input": [password, "[>#]"]})
elif 'assword' in response['stdout']:
self.run({"command": [password], "timeout": timeout})
# 本地拷贝到远端
# 2018-03-13 wwx271515 适配output情况下需要输入yes或no场景
if type == 'output':
response = self.run({"command": ["sh","-c","scp", "'%s'"%localPath, remoteFilePath], "timeout": timeout,
"waitstr": "yes\/no|assword"})
if response['stdout']:
if 'continue' in response['stdout']:
self.run({"command": ['yes'], "waitstr": "assword", "timeout": timeout,
"input": [password, "[>#]"]})
elif 'assword' in response['stdout']:
self.run({"command": [password], "timeout": timeout})
if response["rc"] != 0:
raise CommandException("Problem SCP Error: %s" % response['stderr'])

def hostUpTime(self):
"""下发uptime命令

Returns:
result (str): 包含当前时间的字典.


Raises:
CommandException: 获取当前时间失败.

Examples:
hostObj.upTime()

"""

response = self.run({"command": ["sh", "-c", "uptime"]})
if response["rc"] != 0:
raise CommandException("send command uptime failed.")
result = response["stdout"]

return result

def getDiskSpace(self, path=None):
"""获取磁盘空间信息

Returns:
result (dic): 包含当前磁盘空间信息的字典.
{"/dev/sda2":{"Size": "914G", "Use%": "2%", "Size": "914G", "Used": "17G"},
"/dev/sda1":{"Size": "914G", "Use%": "2%", "Size": "914G", "Used": "17G"}}

Examples:
hostObj.getDiskSpace()

"""
if path:
response = self.run({"command": ["sh", "-c", "df", "-h", path]})
else:
response = self.run({"command": ["sh", "-c", "df", "-h"]})
if response["rc"] != 0:
raise CommandException(response["stderr"])
result, info = {}, {}
lines = response["stdout"].split('\n')[:-1]
iterm = lines[0].split()
for line in lines[1:]:
for i in range(len(line.split()))[1:]:
info[iterm[i]] = line.split()[i]
result[line.split()[0]] = copy.deepcopy(info)
return result

if __name__ == "__main__":
pass