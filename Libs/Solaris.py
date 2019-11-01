

import re
import os

from UniAutos.Device.Host.Unix import Unix
from UniAutos.Util.Units import SECOND, Units, BYTE
from UniAutos.Exception.InvalidParamException import InvalidParamException
from UniAutos.Exception.CommandException import CommandException
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Exception.FileNotFoundException import FileNotFoundException

class Solaris(Unix):
"""Solaris主机类, 继承于Unix类

提供主机操作相关接口，如: 创建分区， 创建文件系统等.

Args:
username (str) : Solaris主机登陆使用的用户名, 建议使用root用户.
password (str) : username的登陆密码.
params (dict) : 其他参数, 如下定义:
params键值对说明:
protocol (str): 通信协议，可选，取值范围:
-["storSSH", "standSSH", "local", "telnet", "xml-rpc"]
port (int): 通信端口，可选
ipv4_address (str): 主机的ipv4地址，key与ipv6_address必选其一
ipv6_address (str): 主机的ipv6地址，key与ipv4_address必选其一
os (str): 主机操作系统类型，可选
type (str): 连接的类型

Attributes:
self.os (str) : 主机的操作系统类型, 指定为: 'Solaris'.
self.openIscsi (bool) : 主机是否安装openIscsi, 默认为False; False: 未安装，True: 已安装.
self.fcInfo (bool) : 主机是否安装fcInfo, 默认为False; False: 未安装，True: 已安装.

Returns:
Solaris (UniAutos.Device.Host.Solaris.Solaris): Solaris主机对象实例.

Raises:
None.

Examples:
None.

"""
def __init__(self, username, password, params):
super(Solaris, self).__init__(username, password, params)
self.os = 'Solaris'
self.openIscsi = False
self.fcInfo = False

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
response = self.run({'command': ['sh', '-c', 'uname -p']})
if response['stdout']:
lines = self.split(response['stdout'])
for line in lines:
if re.search(r'uname', line):
continue
archMatch = re.search(r'(\S+)', line)
if archMatch:
self._setArchitecture(archMatch.group(1))
return self.architecture

def getSystemUptime(self):
"""Gets the system uptime in UniAuto time unit.

Args:
None.

Returns:
upTime (UniAuto time unit): indicating the uptime.

Raises:
None.

Examples:
None.

"""
days, hours, minutes, upTimeInSeconds = 0, 0, 0, 0
response = self.run({'command': ['sh', '-c', 'uptime']})
if response['rc'] == 1 and response['stdout']:
lines = self.split(response['stdout'])
for line in lines:
upTimeMatch = re.match(r'up\s+(\d+)\s+day.*\s+(\d+):(\d+)', line)
if upTimeMatch:
days = upTimeMatch.group(1)
hours = upTimeMatch.group(2)
minutes = upTimeMatch.group(3)
upTimeInSeconds = ((days * 24 + hours) * 60 + minutes) * 60
else:
daysMatch = re.match(r'up\s+(\S+)\s+day', line)
hoursMatch = re.match(r'(\d+)\s+hour', line)
minutesMatch = re.match(r'(\d+)\s+hour', line)
if daysMatch:
days = daysMatch.group(1)
if hoursMatch:
hours = hoursMatch.group(1)
if minutesMatch:
minutesMatch.group(1)
upTimeInSeconds = ((days * 24 + hours) * 60 + minutes) * 60
return str(upTimeInSeconds) + SECOND

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
'interfaces' (str): {
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
'hostname': 'nodel',
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
responseName = self.run({'command': ['sh', '-c', 'uname', '-n'], 'check_rc': 1})
lines = self.split(responseName['stdout'])

for line in lines:
if re.match(r'^uname -n', line):
continue
tmpMatch = re.match(r'^\S+$', line)
if tmpMatch:
networkInfo['hostname'] = tmpMatch.group()
break
networkInfo['dns_domain'] = self.getDomainInfo()

# 获取网络信息
responseNet = self.run({'command': ['sh', '-c', 'ifconfig', '-a'], 'check_rc': 1})
currentInterface = None
networkInfo['interface'] = {}

netLines = self.split(responseNet['stdout'])
for line in netLines:

currentNetMatch = re.match(r'^([\S:]+):', line) # 匹配interface名称.
if currentNetMatch:
currentInterface = currentNetMatch.group(1)
networkInfo['interface'][currentInterface] = {}
continue

ipv4Match = re.search(r'^\s+inet\s+(\S+)\s+netmask\s+(\S+)', line) # 匹配ipv4和mask.
if ipv4Match and currentInterface in networkInfo['interface']:
networkInfo['interface'][currentInterface]['ipv4_address'] = ipv4Match.group(1)
networkInfo['interface'][currentInterface]['netmask'] = ipv4Match.group(2)
continue

ipv6Match = re.search(r'^\s+inet6\s+(\S+)', line) # 匹配ipv6.
if ipv6Match and currentInterface in networkInfo['interface']:
networkInfo['interface'][currentInterface]['ipv6_address'] = ipv6Match.group(1)

responseGateway = self.run({'command': ['sh', '-c', 'netstat', '-rn'], 'check_rc': 1})

gatwayLines = self.split(responseGateway['stdout'])
for line in gatwayLines:
gatewayMatch = re.match(r'^(?:default|0\.0\.0\.0)\s+(\S+)', line)
if gatewayMatch:
networkInfo['gateway'] = gatewayMatch.group(1)

return networkInfo

def getDisks(self):
"""Gets the list of LUNs seen on the host system disk names on host system.
This method will attempt to find the disks in the following order:
- Powerpath (powermt)
- MPxIO (luxadm | mpathadm)
- format
- /dev/dsk/*

If you're having trouble with disks, please ensure powermt is installed or that
MPxIO is enabled as these are the most accurate tools.

Args:
None.

Returns:
retArray (list): An array of all disk IDs.

Raises:
CommandException: Could not get a disk listing.

Examples:
# Typical scenario using Solaris disks
disks = host.getDisks()
host.createFilesystem(disks[0])
host.createMount(disks[0], '/mnts/1')

"""
retArray = []

def addDisks(outPut):
lines = self.split(outPut)
ioPathsMap = {}
for line in lines:
diskDict = self._breakApartDeviceName(line)
if 'base_name' in diskDict:
if self.rootDisk and re.match(r' ' + str(self.rootDisk) + ' ', line):
continue
if diskDict['disk'] in ioPathsMap:
ioPathsMap[diskDict['disk']][diskDict['controller']].append(diskDict['target'])
ioPathsMap[diskDict['disk']]['base_name'].append(diskDict['base_name'])
else:
tmp = {diskDict['disk']:
{diskDict['controller']: [diskDict['target']],
'base_name': [diskDict['base_name']]
}
}
ioPathsMap.update(tmp)
for disk in ioPathsMap:
retArray.append(ioPathsMap[disk]['base_name'][0])
# 1.) Try `powermt`
# TODO
# UniAuto::Utilities::Powermt->lunMapInfo() ?

# 2.) Try MPxIO luxadm (this only works for FC)

response = self.run({'command': ['sh', '-c', 'luxadm', 'probe']})
if response['rc'] == 0:
addDisks(response['stdout'])
if len(retArray) > 0:
return retArray
# 3.) Try pulling from format; format will return the root disk
# (as will /dev/dsk..) and since we don't want to give that to the user,
# make sure we know what it is (&$addDisks will check for it)

if not self.rootDisk:
self.getMountPoints()
disk = self._breakApartDeviceName(self.rootDisk)
self.rootDisk = disk['base_name']

response = self.run({'command': ['sh', '-c', 'format < /dev/null']})
if response['rc'] == 0 or response['stdout']:
addDisks(response['stdout'])
if len(retArray) > 0:
return retArray

# 4.) Try pulling from /dev/dsk
disks = self.listFile('/dev/dsk')
disksString = '\n'.join(disks.iterkeys())
addDisks(disksString)
if len(retArray) > 0:
return retArray
raise CommandException("Could not get a disk listing.")

def initializeDisk(self, disk, mount=None, filesystem=None):
"""对指定的已映射的磁盘或Lun对象进行初始化
#初始化包含将整个磁盘或Lun对象创建为一个分区, 并格式化为指定的文件系统, 挂载到指定的mount点或指定的驱动器号.

Args:
disk (str): The disk to initialize (e.g. '/dev/dsk/c2t3d5')
mount (str): (可选参数)初始化后磁盘的挂载点, 可选参数，默认: None.
filesystem (str): (可选参数)The intended filesystem on disk. Only UFS is supported at this time.
-Defaults to UFS.

Returns:
None.

Raises:
None.

Examples:
hostObj.initializeDisk(disk="/dev/dsk/c2t3d5", filesystem="ufs", mount="/mnt/1")

"""
nameMatch = re.match(r'^/dev/rdsk/(\S)', disk)
if nameMatch:
diskName = nameMatch.group(1)
else:
diskName = disk

if filesystem is not None and not re.match(r'^ufs$', filesystem):
raise InvalidParamException("filesystem Only UFS is supported, now is %s" % filesystem)
self.createFilesystem(disk=disk)

if not mount:
mount = self._createRandomDirectory('/mnt', "uniAutoMnt_%d%d%d%d_%s" % diskName)

self.createMount(device=disk, mountPoint=mount)

return mount

def createFilesystem(self, disk):
"""This method creates a UFS file system that spans the entire disk. UniAuto
does not support multiple partitions per disk in Solaris at this time.

Args:
disk (str) : The disk to create a filesystem on.

Returns:
None.

Raises:
None.

Examples:
None.
"""
# We need to use the "block" path to disk - /dev/rdsk/[id]s2
# Slice 2 targets the entire disk in Solaris

if re.match(r'^/dev/rdsk/(\S)', disk):
disk += "s2"
else:
disk = '/dev/rdsk/%ss2' % disk
# todo优化

# We use `newfs` to create a UFS filesystem
# Parameters used:
# -v : verbose
response = self.run({'command': ['sh', '-c', 'newfs', '-v', disk], 'input': 'y'})
if response['rc'] !=0:
raise CommandException("Creating filesystem on disk %s failed" % disk)

def createMount(self, device, mountPoint=None):
"""Solaris wrapper to create a mount.

Args:
device (str): The device to mount (/dev/dsk/c2t3d5)
mountPoint (str): (可选参数)Path to mount disk upon. Defaults to a dir in /mnt/
that equals 'uniAutoMnt_%d%d%d%d_DiskName'; e.g. '/mnt/uniAutoMnt_3941_c0t2d2'

Returns:
mountPoint (str): The path to which the device was mounted

Raises:
None.

Examples:
None.

"""
nameMatch = re.match(r'^/dev/rdsk/(\S)', device)
if nameMatch:
diskName = nameMatch.group(1)
else:
diskName = device

if not mountPoint:
mountPoint = self._createRandomDirectory('/mnt', 'uniAutoMnt_%d%d%d%d_%s' % diskName)
disk = self._breakApartDeviceName(device)
if 'controller' in disk and disk['controller']:
device = disk['base_name']
mountPoint = super(Solaris, self).createMount(device="dev/dsk/%ss2" % device, mountPoint=mountPoint)
else:
mountPoint = super(Solaris, self).createMount(device=device, mountPoint=mountPoint)

return mountPoint

def getNasMountPoints(self):
"""Gets an inventory of all current nfs and cifs mount points

Args:
None.

Returns:
Dict containing the following key/value pairs

=> { #mountpoint format is in the format of '/mnt/mntpoint'
type (str): nfs | cifs
export (str): server's export, '\\10.1.1.5\Share1' or '10.1.1.5:/Share1'
status (str): disconnected | connected
}

Raises:
None.

Examples:
None.

"""
cmd = ['mount', '-v']
response = self.run({'command': cmd, 'check_rc': 1})
ret = {}
if response['stdout']:
lines = self.split(response['stdout'])
for line in lines:
match = re.match(r'^(.+) on (.+) type (cifs|nfs)', line)
if match:
mountPoint = match.group(2)
export = match.group(1)
export = re.sub(r'/', r'\\', export)
ret = {mountPoint: {'type': match.group(3),
'export': export,
'status': 'connected'}}
return ret

def _breakApartDeviceName(self, device):
"""Used in Solaris to take in a disk, and extract the controller, target, and disk of it.

Args:
device (str): A string containing a disk somewhere in it

Returns:
A hash containing the following key value pairs:
controller (str): scsi controller
target (str): scsi target
disk (str): disk
base_name (str): controller + target + disk

Raises:
None.

Examples:
None.

"""
deviceMatch = re.match(r'(c\d+)(t.*)(d\d+)([sp]\d)?', device)
disk = {}
if deviceMatch:
disk = {'controller': deviceMatch.group(1),
'target': deviceMatch.group(2),
'disk': deviceMatch.group(3),
'base_name': str(deviceMatch.group(1)) + str(deviceMatch.group(2)) + str(deviceMatch.group(3))}
return disk

@validateParam(delay=int)
def _getRebootCommand(self, delay=5):
"""Provides the system-specific reboot command.

Args:
delay (int): (可选参数)time to delay before reboot. Default: '5'， Units is "S"

Returns:
Reboot command.

Raises:
None.

Examples:
None.
"""
return ['shutdown', '-y', '-i', '6', '-g', '%s' % delay]

def mountNfsFilesystem(self, export, mountPoint=None, retryType=None, interrupt=None, timeout=None,
nfsVersion=None, port=None, readSize=None, writeSize=None, securityMode=None,
protocol=None, maxDirFileAttrCacheTime=None, minDirFileAttrCacheTime=None,
maxFileAttrCacheTime=None, minFileAttrCacheTime=None, fileAttributeCachedTime=None,
retryMode=None, directIo=None, attributeCaching=None, closeToOpen=None, posix=None,
quota=None, retransmissionCount=None, retryCount=None, extendAttributes=None):
"""Mounts an exported Nfs filesystem to this host.

Args:
export (str) : The exported filesystem or 'share'. e.g., '10.1.1.5:/server2fs9'.

mountPoint (str) : (可选参数)Destination mountpoint to use on this host.
By default one is chosen for you and placed in /mnt directory.
If mountpoint does not exist it will be created for you automatically.

retryType (str) ：(可选参数)hard|soft, Specifies whether the program using a file via an NFS
connection should stop and wait (hard) for the server to come back online,
if the host serving the exported file system is unavailable, or if it
should report an error (soft).

interrupt (Boolean) : (可选参数) Boolean, if type is hard. Allows NFS requests to be interrupted
if the server goes down or cannot be reached.

timeout (UniAuto Time Unit) : (可选参数)if type is soft. Specifies the timeout value
-after which the error is reported.

nfsVersion (str) : (可选参数)2|3|4. Specifies which version of the NFS protocol to use.
This is useful for hosts that run multiple NFS servers. If no version
is specified, NFS uses the highest supported version by the kernel
and mount command.

port (int) : (可选参数)Specifies the numeric value of the NFS server port.
If num is 0 (the default), then mount queries the remote host's
port mapper for the port number to use. If the remote host's NFS daemon
is not registered with its portmapper, the standard NFS port number of
TCP 2049 is used instead.

readSize (UniAuto Size Unit) : (可选参数) The maximum number of bytes in each network READ request
that the NFS client can receive when reading data from a file on an
NFS server. The actual data payload size of each NFS READ request is
equal to or smaller than the read_size setting. The largest read payload
supported by the Linux NFS client is 1,048,576 bytes (one megabyte).
The read_size value is a positive integral multiple of 1024. Specified
read_size values lower than 1024 are replaced with 4096; values larger
than 1048576 are replaced with 1048576. If a specified value is
within the supported range but not a multiple of 1024, it is rounded
down to the nearest multiple of 1024. *Format is 1024 B, or 4096 B*

writeSize (UniAuto Size Unit) : (可选参数)*See readSize*

securityMode (str) : (可选参数)Specifies the type of security to utilize when authenticating
an NFS connection. Security types are sys|dh|krb5|krb5i|krb5p (Not
supported by all linux distros)

protocol (str) : (可选参数) tcp|udp

maxDirFileAttrCacheTime (UniAuto Time Unit) : (可选参数) Specifies the maximum time holding cached file
attributes after directory update (Default: '60S').

minDirFileAttrCacheTime (UniAuto Time Unit) : (可选参数) Specifies the minimum time holding cached
attributes after directory update (Default: '30S').

maxFileAttrCacheTime (UniAuto Time Unit) : (可选参数) Specifies the maximum time holding cached
attributes after file modification (Default: '60S').

minFileAttrCacheTime (UniAuto Time Unit) : (可选参数)Specifies the minimum time holding cached
attributes after file modification (Default: '3S').

fileAttributeCachedTime (UniAuto Time Unit) : (可选参数)Specifies the time for the above 4 as the same
value. When set this to '0 S', attribute caching will be
disabled.

retryMode (str) : (可选参数) bg|fg. Specifies the retry mode if first attempt
fails, retry in the background or in the foreground.
(Default: 'bg').

directIo (boolean) : (可选参数) forcedirectio|noforcedirectio. Specifies whether
the filesystem uses direct I/O. If use forcedirectio,
data is transferred directly between client and server
with no buffering on the client. If the filesystem is
mounted using noforcedirectio, data is buffered on the
client. forcedirectio is a performance option that is of
benefit only in large sequential data transfers.
The default behavior is noforcedirectio.

attributeCaching (Boolean) : (可选参数) Specifies whether suppress data and attribute
caching. The data caching that is suppressed is the
write-behind. The local page cache is still maintained,
but data copied into it is immediately written to the server.

closeToOpen (Boolean) : (可选参数) Specifies whether perform the normal close-to-open
consistency. When a file is closed, all modified data
associated with the file is flushed to the server and not
held on the client. When a file is opened the client sends
a request to the server to validate the client's local caches.
This behavior ensures a file's consistency across multiple
NFS clients. When -nocto is in effect, the client does not
perform the flush on close and the request for validation,
allowing the possiblity of differences among copies of the
same file as stored on multiple clients.

posix (Boolean) : (可选参数)Specifies whether request POSIX.1 semantics for
the file system.

quota (Boolean) : (可选参数)Enable or prevent quota to check whether the user
is over quota on this file system; if the file system has
quotas enabled on the server, quotas are still checked for
operations on this file system.

retransmissionCount (integer) : (可选参数)Specifies the number of NFS retransmissions.The
default value is 5. For connection-oriented transports,
this option has no effect because it is assumed that the
transport performs retransmissions on behalf of NFS.

retryCount (int) : (可选参数) Specifies the number of times to retry the mount
operation. The default for the mount command is 10000.
The default for the automounter is 0.

extendAttributes (Boolean) : (可选参数) Allow or disallow the creation and manipulation
of extended attributes.

Returns:
mountPoint (str): mountPoint used.

Raises:
None.

Examples:
None.
"""

# Valid syntax for mount:
# mount -F nfs -o opt1, opt2=xyz,etc
# 10.1.1.5:/Share1 /tmp/mnt2

cmd = ['mount', '-F', 'nfs']

options = []
if maxDirFileAttrCacheTime:
acdirmax = Units.getNumber(Units.convert(maxDirFileAttrCacheTime, SECOND))
options.append('acdirmax=%s' % acdirmax)

if minDirFileAttrCacheTime:
acdirmin = Units.getNumber(Units.convert(minDirFileAttrCacheTime, SECOND))
options.append('acdirmin=%s' % acdirmin)

if maxFileAttrCacheTime:
acregmax = Units.getNumber(Units.convert(maxFileAttrCacheTime, SECOND))
options.append('acregmax=%s' % acregmax)

if minFileAttrCacheTime:
acregmin = Units.getNumber(Units.convert(minFileAttrCacheTime, SECOND))
options.append('acregmin=%s' % acregmin)

if fileAttributeCachedTime:
actimeo = Units.getNumber(Units.convert(fileAttributeCachedTime, SECOND))
options.append('actimeo=%s' % actimeo)

if retryMode:
options.append(retryMode)

if directIo is not None:
directIo = 'forcedirectio' if directIo else 'noforcedirectio'
options.append(directIo)

if retryType:
options.append(retryType)

if interrupt is not None:
interrupt = 'intr' if interrupt else 'nointr'
options.append(interrupt)

if attributeCaching:
options.append('noac')

if closeToOpen:
options.append('nocto')

if port:
options.append('port=%s' % port)

if posix:
options.append('posix')

if protocol:
options.append('proto=%s' % protocol)

if quota is not None:
quota = "quota" if quota else 'noquota'
options.append(quota)

if retransmissionCount:
options.append('retrans=%s' % retransmissionCount)

if retryCount:
options.append('retry=%s' % retryCount)

if readSize:
readSize = Units.convert(readSize, BYTE)
options.append('rsize=%s' % readSize)

if writeSize:
writeSize = Units.convert(writeSize, BYTE)
options.append('wsize=%s' % writeSize)

if timeout:
timeout = Units.getNumber(Units.convert(timeout, SECOND))
options.append('timeo=%s' % timeout)

if nfsVersion:
options.append('vers=%s' % nfsVersion)

if extendAttributes is not None:
extendAttributes = 'xattr' if extendAttributes else 'noxattr'
options.append(extendAttributes)

if securityMode:
options.append('sec=%s' % securityMode)

if options:
cmd.extend(['-o', ",".join(options)])

if not self.doesPathExist({'path': mountPoint}):
self.createDirectory(mountPoint)

cmd.append(mountPoint)

response = self.run({'command': cmd, 'check_rc': 1})
return mountPoint

def unmountNfsFilesystem(self, mountPoint, force=False):
"""Unmounts a mounted Nfs filesystem on this host

Args:

mountPoint (str) : mountPoint to unmount.
BE CAREFUL NOT TO UNMOUNT ANY Huawei MOUNTS!
force (boolean) : (可选参数)boolean to force the unmount operation

Returns:
None.

Raises:
None.

Examples:
None.
"""
cmd = ['umount']
if force:
cmd.append('-f')
cmd.append(mountPoint)
response = self.run({'command': cmd, 'check_rc': 1})
self.deleteDirectory(mountPoint)

def getKerberosTicketList(self, suUser=None):
"""show Kerberos ticket-granting ticket

Args:
suUser (str) init ticket for user

Returns:
Array which contains all ticket information

Raises:
None.

Examples:
None

"""
cmd = ['/usr/bin/klist']
if suUser:
cmd = ['sh', '-c', 'su', suUser, '-c', '/usr/bin/klist']
response = self.run({'command': cmd, 'check_rc': 1})
# 1. failure
# Exit code: 1
# Error: getKerberosTicketList: No credentials cache file found (ticket cache FILE:/tmp/krb5cc_0)

if response["rc"]:
return []
else:
return self._parseGetKerberosTicketList(response['stdout'])

def _parseGetKerberosTicketList(self, rawOutput):
"""Parse the output of parsergetKerberosTicketList's command

Args:
rawOutput (str) : the raw output from the command that was executed

Returns:
parsedInfo (list) : Array containing a collection of the attribute values:

(start code)
Put each line to @parsedInfo
(end)

Raises:
None.

Examples:
None.

"""
parsedInfo = []
lines = self.split(rawOutput)
for line in lines:
parsedInfo.append(line)
return parsedInfo

def initKerberosTicket(self, principal, password, suUser=None):
"""obtain and cache Kerberos ticket-granting ticket

Args:
principal (str): the principal need to be created
su_user (str): (可选参数)init ticket for user
password (str): password required for init ticket

Returns:
None.

Raises:
None.

Examples:
None.
"""
cmd = ['sh', '-c', '/usr/bin/kinit', principal]
if suUser:
cmd = ['sh', '-c', 'su', suUser, '-c', '/usr/bin/kinit %s' % principal]
self.run({'command': cmd, 'input': password, 'check_rc': 1})

def destroyKerberosTicket(self, suUser=None):
"""destroy Kerberos tickets

Args:
suUser (str): (可选参数)destroy ticket for user

Returns:
None.

Raises:
None.

Examples:
None.

"""
cmd = ['sh', '-c', '/usr/bin/kdestroy']
if suUser:
cmd = ['sh', '-c', 'su', suUser, '-c', '/usr/bin/kdestroy']
self.run({'command': cmd, 'check_rc': 1})

def _baseKdcCmd(self, command):
"""Admin Kerberos on Kerberos Key Distribution Center (Base command of all other KDC kerberos Command)

Args:
command (str) : sub command should be run

Returns:
response (dict) : the response from command object.

Raises:
None.

Examples:
None.
"""
cmd = ['sh', '-c', '/usr/sbin/kadmin.local']
inputStr = command + 'quit%s' % os.linesep
response = self.run({'command': cmd, 'input': inputStr, 'check_rc': 1, 'prompt': ": "})
return response

def addKerberosPrincipal(self, principal, password):
"""Add Kerberos Principal to KDC database

Args:
principal (str) principal should be added
password (str) password required for init ticket

Returns:
None.

Raises:
None.

Examples:
None.
"""
cmd = "addprinc -pw " + password + " " + principal + "%s" % os.linesep
self._baseKdcCmd(cmd)

def deleteKerberosPrincipal(self, principal, password):
"""Delete Kerberos Principal on Kerberos Key Distribution Center

Args:
principal (str) principal should be added
password (str) password required for init ticket

Returns:
None.

Raises:
None.

Examples:
None.
"""
command = 'delprinc -force ' + principal + "%s" % os.linesep
self._baseKdcCmd(command)

def getKerberosPrincipalList(self):
"""Show Kerberos Principals on Kerberos Key Distribution Center

Args:
None

Returns:
princs (list) Command output

Raises:
None.

Examples:
None.
"""
out = self._baseKdcCmd("listprincs %s" % os.linesep)
return self._parseGetKerberosPrincipalList(out['stdout'])

def _parseGetKerberosPrincipalList(self, rawOutput):
"""Parse the output of the _parseGetKerberosPrincipalList list princs command

Args:
rawOutput (str): Command output

Returns:
princs (list): Array Reference of all Principals

Raises:
None.

Examples:
None.

"""
princs = []
lines = self.split(rawOutput)
for line in lines:
princs.append(line)
return princs

def getIqn(self):
"""Gets the iqn of this host

Args:
None.

Returns:
iqn (str): IQN for this Host

Raises:
None.

Examples:
None.

"""
# example:
# bash-3.00# iscsiadm list initiator-node
# Initiator node name: iqn.1986-03.com.sun:01:002128b13968.55af641c
# Initiator node alias: s10u8c
# Login Parameters (Default/Configured):
# Header Digest: NONE/-
# Data Digest: NONE/-
# Authentication Type: NONE
# RADIUS Server: NONE
# RADIUS access: unknown
# Configured Sessions: 1

self._checkOpenIscsi()
cmd = ['iscsiadm', 'list', 'initiator-node']
response = self.run({'command': cmd, 'check_rc': 1})
iqn = ''
lines = self.split(response['stdout'])
for line in lines:
match = re.match(r'Initiator node name:\s*(\S+)', line)
if match:
iqn = match.group(1)
break
return iqn

def _checkOpenIscsi(self):
"""Checks this host to see if iscsiadm program is installed.

Args:
None.

Returns:
None.

Raises:
FileNotFoundException: 未安装openIscsi软件.

Examples:
None.

"""
# Check to see if we've already checked (No need to call this a million times)

if self.which("iscsiadm"):
self.openIscsi = True
else:
raise FileNotFoundException("Open iSCSI is not installed on this Host.")

def addTargetPortal(self, ip, iqn, port=None):
# example
# iscsiadm add static-config iqn.1986-03.com.sun:2510.600a0b80003487e400000000474c6e0b,192.168.1.1
# or
# iscsiadm add static-config iqn.1986-03.com.sun:2510.600a0b80003487e400000000474c6e0b,192.168.1.1:3100
self._checkOpenIscsi()
staticTarget = iqn + ',' + ip
if port:
staticTarget += ':' + port

cmd = ['iscsiadm', 'add', 'static-config', staticTarget]
self.run({'command': cmd, 'check_rc': 1})

def getTargets(self):
"""Gets a full list of iSCSI targets this system can see. Targets must be logged into
to before you can use their LUNs.

Args:
None.

Returns:
Hash containing the following structure

(start code)
target1Iqn (str): [portalIp1, # Array ref of Portal IP addresses
portalIp2],
target2Iqn (str): [portalIp1, # Array ref of Portal IP addresses
portalIp2],
etc...

Raises:
None.

Examples:
None.

"""
self._checkOpenIscsi()
cmd = ['iscsiadm', 'list', 'static-config']
response = self.run({'command': cmd, 'check_rc': 1})

# #####################
# iscsiadm list static-config
# Static Configuration Target: iqn.1986-03.com.sun:2510.600a0b80003487e400000000474c6e0b,192.168.1.1:3260
# Static Configuration Target: iqn.1986-03.com.sun:2510.600a0b80003487e400000000474c6e0b,192.168.2.1:500
# #####################

targets = {}
lines = self.split(response['stdout'])
for line in lines:
targetsMatch = re.match(r'^Static Configuration Target:\s*(\S+),(\S+):\S+', line)
if targetsMatch:
target = targetsMatch.group(1)
ip = targetsMatch.group(2)
if target in targets:
targets[target].append(ip)
else:
targets[target] = [ip]

return targets

def targetsLogin(self):
"""Logs into an iSCSI Targets. The process of logging into a target adds the physical LUNs
to this host's OS. After issuing this command the LUNs will become ready for IO.
It may take several seconds to complete the commands.

Args:
None.

Returns:
None.

Raises:
None.

Examples:
None.
"""
self._checkOpenIscsi()
# #####################
# iscsiadm modify discovery --static enable
# devfsadm -i iscsi
# #####################

cmd = ['iscsiadm' ,'modify', 'discovery', '--static', 'enable']
self.run({'command': cmd, 'check_rc': 1})
cmd = ['devfsadm' ,'-i', 'iscsi']
self.run({'command': cmd, 'check_rc': 1})

def removeTargetPortal(self, ip, iqn, socket=None):
"""Removes a target from this Host's iSCSI configuration

Args:
ip (str): IP Address of the target portal
iqn (str): iqn of the target
socket (str): (可选参数)the port for iSCSI, default is 3260.

Returns:
None.

Raises:
None.

Examples:
None.

"""
self._checkOpenIscsi()
# #####################
# iscsiadm modify discovery --static disable
# iscsiadm remove static-config iqn.1986-03.com.sun:2510.600a0b80003487e400000000474c6e0b,192.168.1.1
# iscsiadm modify discovery --static enable
# devfsadm -i iscsi
# #####################

cmd = ['iscsiadm', 'modify', 'discovery', '--static', 'disable']
self.run({'command': cmd, 'check_rc': 1})

staticTarget = iqn + ',' + ip
if socket:
staticTarget += ':' + socket

cmd = ['iscsiadm', 'remove', 'static-config', staticTarget]
self.run({'command': cmd, 'check_rc': 1})

cmd = ['iscsiadm', 'modify', 'discovery', '--static', 'enable']
self.run({'command': cmd, 'check_rc': 1})

cmd = ['devfsadm', '-i', 'iscsi']
self.run({'command': cmd, 'check_rc': 1})

def getHbaInfo(self):
"""Gets information about this host's HBA cards

Args:
None.

Returns:
A hash containing Port keys mapped to the following hash
(start code)
port => {
node (str): node wwn
port (str): port wwn
}
(end code)
"""
self._checkFcInfo()
response = self.run({'command': ['fcinfo', 'hba-port'], 'check_rc': 1})

# bash-3.00# fcinfo hba-port
# HBA Port WWN: 10000000c9ae9434
# OS Device Name: /dev/cfg/c2
# Manufacturer: Emulex
# Model: LPe12002-M8
# Firmware Version: 2.01a12 (U3D2.01A12)
# FCode/BIOS Version: Boot:5.11a0 Fcode:3.10a3
# Serial Number: VM04653562
# Driver Name: emlxs
# Driver Version: 2.40s (2009.07.17.10.15)
# Type: N-port
# State: online
# Supported Speeds: 2Gb 4Gb 8Gb
# Current Speed: 8Gb
# Node WWN: 20000000c9ae9434
# HBA Port WWN: 10000000c9ae9435
# OS Device Name: /dev/cfg/c3
# Manufacturer: Emulex
# Model: LPe12002-M8
# Firmware Version: 2.01a12 (U3D2.01A12)
# FCode/BIOS Version: Boot:5.11a0 Fcode:3.10a3
# Serial Number: VM04653562
# Driver Name: emlxs
# Driver Version: 2.40s (2009.07.17.10.15)
# Type: N-port
# State: online
# Supported Speeds: 2Gb 4Gb 8Gb
# Current Speed: 8Gb
# Node WWN: 20000000c9ae9435

fcInfo = {}
lines = self.split(response['stdout'])
port = None
for line in lines:
portWwnMatch = re.match(r'HBA Port WWN:\s*(.*)', line)
nodeWwnMatch = re.match(r'Node WWN:\s*(.*)', line)
if portWwnMatch:
wwn = portWwnMatch.group(1)
port = self.normalizeWwn(wwn)
if port and port in fcInfo:
fcInfo[port].update({'port': port})
else:
fcInfo[port] = {'port': port}
elif nodeWwnMatch:
if port and port in fcInfo:
fcInfo[port].update({'node': nodeWwnMatch.group(1)})
else:
fcInfo[port] = {'node': port}

def _checkFcInfo(self):
"""Checks this host to see if fcinfo program is installed.

Args:
None.

Returns:
None.

Raises:
None.

Examples:
None.
"""
# Check to see if we've already checked (No need to call this a million times)

if self.which("fcinfo"):
self.fcInfo = True
else:
raise FileNotFoundException("Open fcinfo is not installed on this Host.")

if __name__ == "__main__":
pass
