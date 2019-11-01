#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能:

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/9 严旭光 y00292329 created

ret/Parser, Admincli/Parser, vmwarebase

Base-3

"""
import re
from UniAutos.Wrapper.Tool.AdminCli.Parser import Parser


def systemShowPackageParser(rawOutput):
"""show package info's parser.

Args:
rawOutput (str): The raw data of command: 'show upgrade package'

Returns:
software_version (dict): system software version info.
hot_patch_version (dict): system hot patch version info.

"""
softwareRawData = []
hotPatchRawData = []
for line in rawOutput:
if re.search(r'Software Version', line):
rawOutput.pop(rawOutput.index(line))
if re.search(r'HotPatch Version', line):
hotPatchIndex = rawOutput.index(line)
softwareRawData = rawOutput[0:hotPatchIndex + 1]
hotPatchRawData = rawOutput[hotPatchIndex:len(rawOutput)]
break

commonParser = Parser()
commonParser.primary = 'name'
softwareResult = commonParser.standardParser(None, softwareRawData)
commonParser.primary = 'name'
hotPatchResult = commonParser.standardParser(None, hotPatchRawData)

return {"software_version": softwareResult,
"hot_patch_version": hotPatchResult}


def cliShowHistoryParser(rawOutput):
"""show cli history's parser.

Args:
rawOutput (str): The raw data of command: 'show upgrade package'

"""
result = list()
for line in rawOutput:
match = re.search(r'\[(.+)\]\s+\[(.+)\]\s+\[(.+)\]\s+\[(.+)\]\s+\[(.+)\]', line)
if match:
lineResult = dict()
lineResult['time'] = match.group(1)
lineResult['session_type'] = match.group(2)
lineResult['user_address'] = match.group(3)
lineResult['command'] = match.group(4)
lineResult['execute_result'] = match.group(5)
result.append(lineResult)
return result


def colonParser(rawOutput):
"""命令就冒号分开的parser.

Args:
rawOutput (str): The raw data of command: 'show upgrade package'

"""
lineResult = dict()
result = list()
for line in rawOutput:
line = re.sub("^\s+|\s+$", "", line)
match = re.search(r'(.+)\s+:\s+(\d+)', line)
if match:
key = match.group(1)
value = match.group(2)
key = key.lower()
key = key.replace(' ', '_')
lineResult[key] = value
result.append(lineResult)
return result


def beforeHotPatchParser(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
rawOutput = rawOutput[3:-1]
properties = {}
keys = ["check_item_name", "controller_id", "prech_item_result"]
flag = False
for line in rawOutput:
# Strip the blank space at pre, terminal
line = re.sub("(^\s+|\s+$)", '', line)
line = re.sub("(-)", '', line)

if "Check Item Name" in line:
flag = True
continue

if "Upgrade mode" in line or "OM" in line:
continue

matcher = re.match("(\S+)\s+(\S+)\s+(.*)", line)
if flag and matcher:
values = matcher.groups()
item = dict(zip(keys, values))
properties[values[0] + values[1]] = item

return properties


def showRouteGeneralParser(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
rawOutput = rawOutput[1:-1]
properties = {}
keys = ["port", "destination", "mask", "gateway", "type"]
flag = False
for line in rawOutput:
# Strip the blank space at pre, terminal
line = re.sub("(^\s+|\s+$)", '', line)

if "Destination" in line:
flag = True
continue
if '-----------' in line:
continue

matcher = re.match("(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*", line)
if flag and matcher:
values = matcher.groups()
item = dict(zip(keys, values))
if values[0] not in properties:
properties[values[0]] = []
properties[values[0]].append(item)
return properties


def showPortRouteParser(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
rawOutput = rawOutput[1:-1]
properties = {}
keys = ["port", "destination", "mask", "gateway"]
flag = False
for line in rawOutput:
# Strip the blank space at pre, terminal
line = re.sub("(^\s+|\s+$)", '', line)
line = re.sub("(-)", '', line)

if "Destination" in line:
flag = True
continue

matcher = re.match("(\S+)\s*(\S+)\s*(\S+)\s*(\S+)\s*", line)
if flag and matcher:
values = matcher.groups()
item = dict(zip(keys, values))
if values[0] not in properties:
properties[values[0]] = []
properties[values[0]].append(item)
return properties


def unParser(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
return []


def showSecurityRule(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
rawOutput = rawOutput[1:-1]
properties = []
secureId = None
secureIp = None
enable = None
for line in rawOutput:
enableStr = re.search('yes|no', line, re.I)
if enableStr and not enable:
enable = enableStr.group()
IpStr = re.search('(\d+)\s+(\S+)', line, re.I)
if IpStr:
secureId = IpStr.groups()[0]
secureIp = IpStr.groups()[1]

properties.append({'id': secureId, 'secure_ip_address': secureIp, 'enable': enable})

if not secureId and not secureIp:
properties.append({'id': '', 'secure_ip_address': '', 'enable': enable})
return properties


def showFireWill(rawOutput):
"""Parse the check status information before hot patching into dictionary.

Args:
rawOutput Type(str): The command output for hot patch

Changes:
2015/11/11 y00305138 Created

"""
rawOutput = rawOutput[1:-1]
keys_ipv4 = ["id", "destination", "mask", "prohibited_service"]
keys_ipv6 = ["id", "destination", "prefix_length", "prohibited_service"]
flag = False
properties = {}
for line in rawOutput:
if line == 'IPV4 Firewall Config:' or line == 'IPV6 Firewall Config:' or line == '':
continue
# Strip the blank space at pre, terminal
line = re.sub("(^\s+|\s+$)", '', line)
line = re.sub("(-)", '', line)

if "Mask" in line:
flag = 'IPV4'
continue
if "Prefix Length" in line:
flag = 'IPV6'
continue
matcher = re.match("(\S+)\s*(\S+)\s*(\S+)\s*(\S+)", line)
if flag == 'IPV4' and matcher:
valuesipv4 = matcher.groups()
item = dict(zip(keys_ipv4, valuesipv4))
if valuesipv4[0] not in properties:
properties[valuesipv4[0]] = []
properties[valuesipv4[0]].append(item)
elif flag == 'IPV6' and matcher:
valuesipv6 = matcher.groups()
item = dict(zip(keys_ipv6, valuesipv6))
if valuesipv6[0] not in properties:
properties[valuesipv6[0]] = []
properties[valuesipv6[0]].append(item)
return properties


def showCertificateParser(rawOutput):
"""Parse the show certificate general output into dictionary.

Args:
rawOutput Type(str): The command output for show certificate general

Changes:
2018/12/11 w00354913 Created

"""
commonParser = Parser()
commonParser.primary = 'type_use'
commonParser.primaryMergeDict = {
'key': commonParser.primary,
'key_list': ['type', 'use']
}
properties = commonParser.standardParser(None, rawOutput)

# Compatible with older versions when 'use' is equal to '--'.
keys = properties.keys()
for key in keys:
if re.search(r'_--$', key):
key_new = re.sub(r'_--$', '', key)
properties[key_new] = properties[key]
properties.pop(key)

return properties
=======================================================================================
# -*- coding: utf-8 -*-

"""
功 能: 封装标准化解析

版权信息: 华为技术有限公司，版权所有(C) 2014-2015
"""

import re
from UniAutos import Log
from UniAutos.Exception.UniAutosException import UniAutosException
from UniAutos.Util.TypeCheck import validateParam
from UniAutos.Util.TypeCheck import removeSpecialCharacters


class Parser(object):
def __init__(self, convertDict=None, primary=None, tableTitle=None, splitSpaceAtLeast=2, primaryMergeDict=None):
"""解析对象的构造器

Args:
convertDict (dict): 解析指定熟悉的转换方法字典.
primary (str): 解析后生成属性时的属性主键.
tableTitle (str): 解析回显存在多个表头的情况，如show port general 存在ETH，FC等多个表头

Returns:
parser(UniAutos.Component.Clone.Huawei.OceanStor.Lun): 返回Clone对象
"""
self.logger = Log.getLogger(str(self.__module__))
self.convertDict = convertDict
self.primaryMergeDict = primaryMergeDict
self.primary = primary
self.tableTitle = tableTitle
self.splitSpaceAtLeast = splitSpaceAtLeast

@removeSpecialCharacters(
# ('show_alarm', ('\b', '^[-/\\\\|]+', '^Processing\.{3}\s{2}', '^[-/\\\\|]+')),
# ('show_event', ('\b', '^[-/\\\\|]+', '^Processing\.{3}\s{2}', '^[-/\\\\|]+')),
('show_port_general', ('\b-', '\b/', '\b\|', '\b\\\\', '\b', '-+\\\\+', '^Processing\.{3}\s{2}'))
)
def standardParser(self, wrapper, rawOutput):
"""将命令回显（横表和竖表）转换的list解析为dict

Args:
rawOutput (list): 回显字符转换后的list
wrapper () : wrapper 实例

Returns:
result (dict): 解析之后的业务属性字典.

Raises:
UniAutosException: 当横表没有分割航，或解析后为空字典

Examples:

=================================================================================
1.横表解析
show disk general

ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Normal Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Normal Online SAS 1.079TB Free Disk -- 10000

admin:/>

-解析后:
{
'CTE0.0': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': 'Normal',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.0'
},
'CTE0.1': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': 'Normal',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.1'
}
}

=================================================================================
2.竖表解析
show disk general disk_id=CTE0.0

ID : CTE0.0
Health Status : Normal
Running Status : Online
Type : SAS
Capacity : 1.079TB
Role : Free Disk
Disk Domain ID : --
Speed(RPM) : 10000

admin:/>

-解析后:
{
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': 'Normal',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.0'
}

=================================================================================
3.竖表解析，设置commonParser.primary值
show disk general disk_id=CTE0.0

ID : CTE0.0
Health Status : Normal
Running Status : Online
Type : SAS
Capacity : 1.079TB
Role : Free Disk
Disk Domain ID : --
Speed(RPM) : 10000

admin:/>

self.primary = 'id'

-解析后
{
'CTE0.0': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': 'Normal',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.0'
}
}

=================================================================================
4.横表解析，有子表
show port general physical_type=ETH
--------------- Host Port:----------------
ID Health Status Running Status Type IPv4 Address IPv6 Address MAC
--------- ------------- -------------- --------- ------------ ------------ -----------------
CTE0.A.H0 Normal Link Up Host Port -- 34:00:a3:0e:04:84
------------ Management Port:-------------

ID Health Status Running Status Type IPv4 Address IPv6 Address MAC
----------- ------------- -------------- --------------- ------------ ------------ -----------------
CTE0.A.MGMT Normal Link Up Management Port 100.15.140.2 fec0::11 34:00:a3:0e:04:82

admin:/>
-解析后
{
'CTE0.A.H0': {
'ipv6_address': '--',
'running_status': 'Link Up',
'mac': '34:00:a3:0e:04:84',
'ipv4_address': '',
'health_status': 'Normal',
'type': 'Host Port',
'id': 'CTE0.A.H0'
},
'CTE0.A.MGMT': {
'ipv6_address': 'fec0::11',
'running_status': 'Link Up',
'mac': '34:00:a3:0e:04:82',
'ipv4_address': '100.15.140.2',
'health_status': 'Normal',
'type': 'Management Port',
'id': 'CTE0.A.MGMT'
}
}

=================================================================================
5 横表解析，列中有空值
show disk general

ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000

admin:/>

-解析后
{
'CTE0.0': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.0'
},
'CTE0.1': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.1'
}
}

=================================================================================
6 设置commonParser.convertDict值，替换解析后key: 'id' 为 'disk_id',且保留原有key: 'id'
show disk general

ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000

admin:/>
self.convertDict = {
'id': {'converted_key': 'disk_id'}
}
-解析后
{
'CTE0.0': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_id': 'CTE0.0',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.0'
},
'CTE0.1': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'disk_id': 'CTE0.1',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'CTE0.1'
}
}
##请注意字典中id和disk_id##

=================================================================================
7 设置commonParser.convertDict值，用TranValue方法转换解析后key: 'role' 对应value，访问未转换的value使用 key+'_raw'，即 'key_raw',
show disk general

ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000

admin:/>

def TranVlaue(example):
return 'Disk'

self.convertDict = {
'role': {'converted_value': TranVlaue}
}
-解析后
{
'CTE0.0': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'role_raw': 'Free Disk',
'disk_domain_id': '--',
'health_status': '',
'role': 'Disk',
'type': 'SAS',
'id': 'CTE0.0'
},
'CTE0.1': {
'capacity': '1.079TB',
'running_status': 'Online',
'speed': '10000RPM',
'role_raw': 'Free Disk',
'disk_domain_id': '--',
'health_status': '',
'role': 'Disk',
'type': 'SAS',
'id': 'CTE0.1'
}
}
##请注意字典中role和role_raw对应value值##

=================================================================================
8.参考6,7；转换解析后字典中的key和value, 先修改转换value,再修改key
show disk general

ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000

admin:/>

def TranVlaue(example):
return 'Disk'

self.convertDict = {
'id': {'converted_key': 'disk_id', 'converted_value': TranVlaue}
}
-解析后
{
'CTE0.0': {
'capacity': '1.079TB',
'id_raw': 'CTE0.0',
'running_status': 'Online',
'speed': '10000RPM',
'disk_id': 'Disk',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'Disk'
},
'CTE0.1': {
'capacity': '1.079TB',
'id_raw': 'CTE0.1',
'running_status': 'Online',
'speed': '10000RPM',
'disk_id': 'Disk',
'disk_domain_id': '--',
'health_status': '',
'role': 'Free Disk',
'type': 'SAS',
'id': 'Disk'
}
}
##请注意字典中id和disk_id id对应value值##

9.只解析指定的子表，使用参数tableTitle
show port general port_id=CTE0.A6.P3
ETH port:
--------------- Host Port:----------------

ID : CTE0.A6.P3
Health Status : Normal
Running Status : Link Down
Type : Host Port
IPv4 Address :
Subnet Mask :
IPv4 Gateway :
FCoE port:

ID : CTE0.A6.P3
WWN : 2000e468a3fc4a8e
Role : TGT
SFP Status : Offline
admin:/>
self.tableTitle="FCoE Port"
-解析后
{
'sfp_status': 'Offline',
'wwn': '2000e468a3fc4a8e',
'role': 'TGT',
'id': 'CTE0.A6.P3'
}
10.竖表有子表，各表为相同类型不同对象的详细信息（子表无表名），此种情况必须指定primary来解析
show lun_copy member lun_copy_id=0
Role : Source
LUN Copy ID : 0
Type : Local
Capacity : 10.000MB
LUN ID : 1
Name : lun0001
Device ID : --
Device Name : XX.Storage
Remote LUN WWN : --
----------------------------
Role : Target
LUN Copy ID : 0
Type : Local
Capacity : 10.000MB
LUN ID : 0
Name : lun0000
Device ID : --
Device Name : XX.Storage
Remote LUN WWN : --
----------------------------
Role : Target
LUN Copy ID : 0
Type : Local
Capacity : 10.000MB
LUN ID : 2
Name : lun0000
Device ID : --
Device Name : XX.Storage
Remote LUN WWN : --
admin:/>
self.primary = 'lun_id'
解析后：
{
'1': {
'capacity': '10.000MB',
'name': 'lun0001',
'lun_copy_id': '0',
'remote_lun_wwn': '--',
'device_name': 'XX.Storage',
'lun_id': '1',
'role': 'Source',
'type': 'Local',
'device_id': '--'
},
'0': {
'capacity': '10.000MB',
'name': 'lun0000',
'lun_copy_id': '0',
'remote_lun_wwn': '--',
'device_name': 'XX.Storage',
'lun_id': '0',
'role': 'Target',
'type': 'Local',
'device_id': '--'
},
'2': {
'capacity': '10.000MB',
'name': 'lun0000',
'lun_copy_id': '0',
'remote_lun_wwn': '--',
'device_name': 'XX.Storage',
'lun_id': '2',
'role': 'Target',
'type': 'Local',
'device_id': '--'
}
}

11 添加处理了process的几种回显
情况一
show disk general
Processing... -\|/-\|/-\|/-\|/-\|
ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000
admin:/>
情况二
show disk general
Processing... -\|/-\|/-\|/-\|/-\| ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000
admin:/>
处理后
show disk general
ID Health Status Running Status Type Capacity Role Disk Domain ID Speed(RPM)
------- ------------- -------------- ---- ---------- --------- -------------- ----------
CTE0.0 Online SAS 1.079TB Free Disk -- 10000
CTE0.1 Online SAS 1.079TB Free Disk -- 10000
admin:/>


Changes:
2015-05-12 y00292329 Created

"""
successStrList = ["Send test alert successfully", "Command executed success"]

# 回显小于三行或等于三行，默认为命令执行信息，不必解析
if len(rawOutput) >= 3:

# 没有查询到数据的时候，直接获取命令执行结果.
if re.search('No matching records', rawOutput[-2]):
rawOutput = rawOutput[1:-2]
else:
rawOutput = rawOutput[1:-1]

properties = {} # 查询的属性字典
result = {} # 最终的返回值
#解析前去除空行
while True:
if re.search('\S+', rawOutput[0]):
break
else:
rawOutput = rawOutput[1:]
# 如果当前存在Processing字符串时，去掉Processing字符串，如果Processing后有有用信息，也可以获取
# 并将去掉后的字符串去掉首尾空白字符.
if re.search('Processing\.\.\..*', rawOutput[0]):
tmp = re.findall('[\(\w\)\s:]+', rawOutput[0])[-1].strip()
if re.search('Processing', tmp) or not re.search('\S+', tmp):
rawOutput = rawOutput[1:]
if len(rawOutput) == 0:
return result
else:
rawOutput[0] = tmp

# 如果命令返回值只存在一行，且为命令执行成功,直接返回空字典，表明为查询到数据.
if ((len(rawOutput) == 1 and re.search("success|successfully", rawOutput[0], re.IGNORECASE)) or
re.search("|".join(successStrList), rawOutput[-1], re.IGNORECASE)):
return result

if not self.tableTitle:
if re.search('(ETH|FC|FCoe|IB|COM|PCIE|SAS|RDMA)\sPort', rawOutput[0], re.IGNORECASE):
#处理processing
for i in xrange(len(rawOutput)):
ismach = re.search('(-+\s+\S+\s+\S+:-+)', rawOutput[i])
if ismach:
rawOutput[i] = ismach.group()
temp = ["start"]
result = {}
for line in rawOutput:
if not line:
continue
if re.search('(ETH|FC|FCoe|IB|COM|PCIE|SAS|RDMA)\sPort|^-+', line, re.IGNORECASE):
if len(temp) == 1:
continue
elif re.search('Gb PCIe Port', line, re.IGNORECASE):
temp.append(line)
else:
temp.append("end")
result.update(self.standardParser(wrapper, temp))
temp = ["start"]
else:
temp.append(line)
if len(temp) > 1:
temp.append("end")
result.update(self.standardParser(wrapper, temp))
return result
if re.search('(ETH|FC|FCoe|IB|COM|PCIE|SAS|RDMA)\sPort', rawOutput[0], re.IGNORECASE):
temp = ["start"]
result = {}
for line in rawOutput:
if not line:
continue
if re.search('(ETH|FC|FCoe|IB|COM|PCIE|SAS|RDMA)\sPort|^-+', line, re.IGNORECASE):
if len(temp) == 1:
continue
else:
temp.append("end")
result.update(self.standardParser(wrapper, temp))
temp = ["start"]
else:
temp.append(line)
return result

# 判断当前返回值是横表，还是竖表.
isRow = None
for line in rawOutput[::-1]:
line = re.sub('\n|\r', "", line)

# 如果是表头，跳过不做处理
if (len(line) == 0 or
re.search("^\s{4,}", line) or
re.search('(ETH|FC|FCoe|IB|COM|PCIE|RDMA)\sPort', line, re.IGNORECASE) or
re.search('Processing\.\.\..*', line)):
continue

isRow = re.search('(.*?)\s:\s(.*?)', line) # 判断如果出现 "Health Status : Normal"即为竖表.
break

canBeParsed = False

# 判断回显得数据中是否包含带括号的单位， 直接去掉.
# TODO 待优化，觉得应该可以不去掉，但是目前修改有风险-2017:07:21
complieUnit = re.compile('.*\((.*)\)$')

if isRow:
# 回显信息为竖表
key = None
value = None
# primaryKey = None
primaryKey = self.primary
matcher = None
unit = None

# 过滤行
compileSkipLine = re.compile('(Processing\.\.\..*)|(.*:/>)|(.*[=]{5,})|(Command executed success.*)')

# 子表分割行
subTableSignLine = re.compile('\-{4,}$')

for line in rawOutput:
line = re.sub('\n', '', line.strip())

# 如果当前存在Processing字符串时，去掉Processing字符串，并将去掉后的字符串去掉首尾空白字符.
if re.search('Processing\.\.\..*', line):
# 2017-07-21 h90006090 将匹配出的去掉Processing的字符串，再次去掉首尾空白字符
tmp = re.findall('[\w\s:]+', line)[-1].strip()
if re.search('Processing', tmp) or not re.search('\S+', tmp):
continue
else:
line = tmp

# 如果存在表头的Wrapper，需要判断当前line是否有表头, 如果wrapper指定了表头，但是未找到表头，则可能出现解析错误.
if self.tableTitle:
# 找到表头所在行，后续行设置能能够解析
if re.match((self.tableTitle+":").lower(), line.lower(), re.IGNORECASE):
canBeParsed = True
continue
elif re.match("([^\s]+\s)?[^\s]+:", line):
# 出现另一张表时，后续行设置为不能解析
canBeParsed = False
continue
if canBeParsed is False:
continue

if len(line) == 0 or compileSkipLine.match(line):
continue

# 解析回显数据
matcher = re.match('(.*?)\s:(.*)$', line)

if matcher:
value = matcher.groups()[1].strip()
key = re.sub("\s+", "_", matcher.groups()[0].strip().lower())
unit = complieUnit.match(key)
if unit:
if value != '--' and value != '' and self.checkExtraKey(key):
# value不为'--'且不为空，key中有单位时，value加上大写的单位,key去掉单位
value += unit.groups()[0].upper()
key = re.sub('\(.*\)$', '', key)
if key in properties:
if not primaryKey or primaryKey not in properties:
primaryKey = key
result[properties[primaryKey]] = properties
properties = {}
properties[key] = value

elif subTableSignLine.match(line) and self.primary and properties and self.primary in properties:
result[properties[self.primary]] = properties
properties = {}
continue
else:
if key:
properties[key] += "\n"+line

if not primaryKey or primaryKey not in properties:
if self.primary and self.primary in properties:
result[properties[self.primary]] = properties
else:
result = properties
else:
result[properties[primaryKey]] = properties
else:
# 回显信息为横表
keys = None
values = None
valueIndexes = None
keyLine = None
unit = None
compileSplit = re.compile('\s{'+str(self.splitSpaceAtLeast)+',}')

# Process等需要过滤的匹配正则
compileSkipLine = re.compile('(Processing\.\.\..*)|(.*:/>)|(Command executed success.*)')

# 表头正则
subTableMarkLine = re.compile('\-{4,}.*[a-zA-Z]+.*\-{4,}')

markLine = re.compile('[\-\s]*\-$')

for line in rawOutput:
line = re.sub('\n', '', line.strip())
if self.tableTitle:

if re.match(self.tableTitle+":", line):
# 找到表明所在行，后续行设置能能够解析
canBeParsed = True
continue
elif re.match("([^\s]+\s)?[^\s]+:", line):
# 出现另一张表时，后续行设置为不能解析
canBeParsed = False
continue
if canBeParsed is False:
continue

if len(line) == 0:
continue

# 如果匹配到需要过滤的字符.
if compileSkipLine.match(line):

# 如果过滤到line中存在表头
# 2017-07-24 h90006090 如果表头中出现了Process等需要过滤的字符串时，需要重置keys和valueIndexes
if subTableMarkLine.search(line):
keys = None
valueIndexes = None
continue
#如果存在过滤字段，并且不是表头,适配规避脚本验证错误命令的情况
elif line.startswith("Processing..."):
line = re.findall('[\(\w\)\s:]+', line)[-1].strip()
else:
continue

if subTableMarkLine.match(line):
# 过滤分表表头，如------------ Maintenance Port:------------
keys = None
valueIndexes = None
continue

if not keys:
keys = re.split(compileSplit, line)
keyLine = str(keys)
for i in xrange(len(keys)):
keys[i] = re.sub("\s+", "_", keys[i].strip()).lower()
elif markLine.match(line):
# 安分割行----------- ------------- -------------- ---------------取每一列在当前行的起始位置
valueIndexes = []
for i in xrange(len(line)):
if line[i] == '-':
if i == 0:
valueIndexes.append(i)
elif line[i-1]==' ':
valueIndexes.append(i)
else:
values = re.split(compileSplit, line)
if len(values) != len(keys):
if not valueIndexes:
# 回显中没有分割行，无法截取value，抛出异常
raise UniAutosException('There is no sign to get value index')
del values
values = []
for i in xrange(len(valueIndexes)):
try:
if i == len(valueIndexes)-1:
values.append(line[valueIndexes[i]:].strip())
else:
values.append(line[valueIndexes[i]:valueIndexes[i+1]].strip())
except IndexError, e:
# 处理当前列没有任何数据占位的场景
values.append('')

if str(values) == keyLine:
keys = None
continue

if len(values) > 1:
for i in xrange(len(keys)):
key = keys[i]
value = values[i]
# unit = re.search('\((.*)\)$', key)
unit = complieUnit.match(key)
if unit:
if value != '--' and value != '' and self.checkExtraKey(key):
# value不为'--'且不为空，key中有单位时，value加上大写的单位,key去掉单位
value += unit.groups()[0].upper()
key = re.sub('\(.*\)$', '', key)
properties[key] = value

if self.primary and self.primary in properties:
result[properties[self.primary]] = properties

# 如果设置了primaryMergeDict，则合并出新的key作为主键
elif self.primary and self.primary not in properties and self.primaryMergeDict \
and self.primaryMergeDict['key'] == self.primary:
tmp = ''
for tmpKey in self.primaryMergeDict['key_list']:
if tmpKey not in properties:
continue
if tmp != '':
tmp += "_%s" % properties[tmpKey]
else:
tmp = str(properties[tmpKey])
if tmp != '':
properties.update({self.primary: tmp})
result[properties[self.primary]] = properties
else:
keys[0] = re.sub('\(.*\)$', '', keys[0])
result[properties[keys[0]]] = properties
self.primary = keys[0]
else:
keys[0] = re.sub('\(.*\)$', '', keys[0])
result[properties[keys[0]]] = properties
self.primary = keys[0]
properties = {}
elif len(values) == 1:
key = keys[0]
value = values[0]
unit = re.search('\((.*)\)$', key)
if unit:
if value != '--' and value != '' and self.checkExtraKey(key):
# value不为'--'且不为空，key中有单位时，value加上大写的单位,key去掉单位
value += unit.groups()[0].upper()
key = re.sub('\(.*\)$', '', key)
result[key] = value

if self.convertDict:
result = self.convertParserResult(result, self.convertDict)

if len(result.keys()) == 0 and len(rawOutput) >= 1:
raise UniAutosException('The rawOutput should not be parsed throw this method')

return result

@validateParam(sourceDict=dict, ruleDict=dict)
def convertParserResult(self, sourceDict, ruleDict):
"""The conversion value or key in the dictionary

Args:
sourceDict (Dict): 需要转换的字典
ruleDict (Dict): 转换规则
format {
'key1': {'converted_key': key1a, 'converted_value': method1},
'key2': ...
.
.
}
converted_key : 可选，将sourceDict中key为key1修改为key1a
converted_value : 可选，将sourceDict中key为key1对应的value以参数传给method1，并转换为method1的返回值

注：
1.转换方式为，先进行value的转换，再对key进行修改
2.如果sourceDict中不存在key:key1，key2其中一个或多个，不报错

Returns:
Dict

Raises:
None

Examples:
参考commonParser:Examples:6,7,8
"""
# template = {key: {'converted_key': str 'converted_value': str}}
for key in ruleDict:
if key in sourceDict:
# 回显为非component
if 'converted_value' in ruleDict[key]:
sourceDict[key+'_raw'] = sourceDict[key]
sourceDict[key] = ruleDict[key]['converted_value'](sourceDict[key])
if 'converted_key' in ruleDict[key]:
sourceDict[ruleDict[key]['converted_key']] = sourceDict[key]
else:
# 回显为component
popElement = []
for ele in sourceDict.keys():
if key in sourceDict[ele]:
if 'converted_value' in ruleDict[key]:
sourceDict[ele][key+'_raw'] = sourceDict[ele][key]
sourceDict[ele][key] = ruleDict[key]['converted_value'](sourceDict[ele][key])

# 修改的value也作为字典key时，转换key的值，删除原key对应元素
if self.primary == key and ele == sourceDict[ele][key+'_raw']:
sourceDict[ruleDict[key]['converted_value'](ele)] = sourceDict[ele]
popElement.append(ele)

if 'converted_key' in ruleDict[key]:
sourceDict[ele][ruleDict[key]['converted_key']] = sourceDict[ele][key]
else:
break
for key in popElement:
sourceDict.pop(key)

return sourceDict

def checkExtraKey(self, key):

result = True

if re.search('id\(s\)$', key):
result = False

return result

def performanceParserPre(self, wrapper, rawOutput):
result = dict()
for line in rawOutput:
line = re.sub("^\s+|\s+$", "", line)
match1 = re.match(r'(\d+)\.(.*)\s+(\d+)\.(.*)', line)
match2 = re.match(r'(\d+)\.(.*)', line)
if match1:
value1 = re.sub("^\s+|\s+$", "", match1.group(2))
value2 = re.sub("^\s+|\s+$", "", match1.group(4))
result[match1.group(1)] = value1
result[match1.group(3)] = value2
elif match2:
key1 = re.sub("^\s+|\s+$", "", match2.group(1))
result[match2.group(1)] = match2.group(2)
return result

def performanceParser(self, wrapper, rawOutput):
"""将性能统计的回显进行解析

Args:
rawOutput (list): 回显字符转换后的list
wrapper () : wrapper 实例

Returns:
result (dict) : 命令回显封装成字典

Raises:
None

Examples:
None
"""
result = dict()
for line in rawOutput:
line = re.sub("^\s+|\s+$", "", line)
match = re.match(r'(.*)\s+:\s+(\d+|\d+\.\d+)', line)
if match:
key = re.sub('^\s+|\s+$', '', match.group(1))
result[key] = match.group(2)
return result

def equalParser(self, wrapper, rawOutput):
"""将类似'A' = 'B'的回显进行解析,返回字典

Args:
rawOutput (list): 回显字符转换后的list

Returns:
result (dict) : 命令回显封装成字典

Raises:
None

Examples:
None
"""
result = dict()
for line in rawOutput:
line_list = line.split('=')
if len(line_list) == 2:
key = re.sub("\s+", "_", line_list[0].strip().lower())
value = line_list[1].strip()
result[key] = value
return result
========================================================================================
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
功 能：当前模块为VMware VirtualMachine SDK API实现的UniAutos Wrapper API，针对Vmware进行操作，
包含对VirtualMachine、Datastore、Disk和ESX等模块

版权信息：华为技术有限公司，版本所有(C) 2014-2015

"""
from UniAutos.Wrapper.Api.ApiBase import ApiBase

import sys
import threading
import datetime
try:
from pyVim import connect
from pyVmomi import vim, vmodl
except Exception:
pass

from UniAutos.Exception.UniAutosException import UniAutosException

class VmwareBase(ApiBase):
"""对所有VMware API方法进行封装、回显解析、API交互等操作， 目前已支持以下业务API操作

UniAutos.Wrapper.Api.Vmware.VirtualMachine
UniAutos.Wrapper.Api.Vmware.Datastore
UniAutos.Wrapper.Api.Vmware.Disk
UniAutos.Wrapper.Api.Vmware.ESX

"""

modules = ['UniAutos.Wrapper.Api.Vmware.VirtualMachine',
'UniAutos.Wrapper.Api.Vmware.Datastore',
'UniAutos.Wrapper.Api.Vmware.Disk',
'UniAutos.Wrapper.Api.Vmware.Esx',
'UniAutos.Wrapper.Api.Vmware.Properties']

def __init__(self, username=None, password=None, ipAddr=None):
"""VMware Wrapper API 构造函数

Args:
username (Str) : (可选参数)Vmware ESX/vSphere的用户名
password (Str) : (可选参数)Vmware ESX/vSphere的密码
ipAddr (Str) : (可选参数)Vmware ESX/vSphere的IP地址

Returns:
None

Raises:


"""

for m in self.modules:
__import__(m)
sys.modules[m]
for i in dir(sys.modules[m]):
if i.find("__") < 0:
method = getattr(sys.modules[m], i)
setattr(self, i, method)
super(VmwareBase, self).__init__()
self.siObj = None
self.virtualDiskManager = None
if username:
self.username = username
if password:
self.password = password
if ipAddr:
self.ipAddr = ipAddr
self.conntectDict={}
self.connectedTime = datetime.datetime.now()
self.connect(username, password, ipAddr)


def connect(self, username=None, password=None, ipAddr=None):
"""VMware SDK API Connection方法

Args:
username (Str) : (可选参数)Vmware ESX/vSphere的用户名
password (Str) : (可选参数)Vmware ESX/vSphere的密码
ipAddr (Str) : (可选参数)Vmware ESX/vSphere的IP地址

Returns:
None

Raises:


"""
if not username:
username = self.username
if not password:
username = self.password
if not ipAddr:
ipAddr = self.ipAddr

try:
self.siObj = connect.SmartConnect(host = ipAddr,
user = username,
pwd = password)
except Exception as exc:
if isinstance(exc, vim.fault.HostConnectFault) and '[SSL: CERTIFICATE_VERIFY_FAILED]' in exc.msg:
try:
import ssl
default_context = ssl._create_default_https_context
ssl._create_default_https_context = ssl._create_unverified_context
self.siObj = connect.SmartConnect(host = ipAddr,
user = username,
pwd = password,)
ssl._create_default_https_context = default_context
except Exception as exc1:
raise Exception(exc1)
else:
raise Exception(exc)

self.enableThreadConnection()

def enableThreadConnection(self):
"""Enable 线程 connection

Args:
None

Returns:
None

Raises:


"""

key = 'connected_'+ str(threading.current_thread())
self.conntectDict[key] = 1


def disConnect(self):
"""断开VMware API connection

Args:
None

Returns:
None

Raises:


"""

connect.Disconnect(self.siObj)
self.disableThreadConnection()

def disableThreadConnection(self):
"""Disable 线程 connection

Args:
None

Returns:
None

Raises:


"""

key = 'connected_'+ str(threading.current_thread())
self.conntectDict[key] = 0

def can(self, methodname):
"""判断该类是否存在methodname的方法，如果存在则返回方法的code reference

Args:
None

Returns:
None

Raises:
None

"""

key = 'connected_'+ str(threading.current_thread())
if key not in self.conntectDict:
self.connect()
self.conntectDict[key] = 1
if hasattr(self, methodname):
return eval("self."+methodname)

return None

def getHostSystems(self, hostObj=None, hostIpAddr=None):
"""获取Vmware Host System 对象

Args:
None

Returns:
None

Raises:
None

"""

if hostObj:
hostIpAddr = hostObj.getIpAddress()
if hostIpAddr:
index = self.siObj.content.searchIndex
if index:
return index.FindByIp(datacenter=None, ip=hostIpAddr, vmSearch=False)
else:
return self.getObjects([vim.hostSystem])


def getObjects(self, vimtype, name=None):
"""根据vimtype返回该类型的VMware vimtype

Args:
None

Returns:
None

Raises:
None

"""

container = self.siObj.content.viewManager.CreateContainerView(self.siObj.content.rootFolder, vimtype, True)
if name:
for c in container.view:
if c.name == name:
return c
else:
return container.view

def getLocationObj(self, name, locationType):
"""根据name和locationType获取VMware location对象

Args:
None

Returns:
None

Raises:
None

"""

return self.siObj.content.rootFolder.childEntity[0].vmFolder
vimType=[]
if locationType == 'Folder':
vimType.append(vim.Folder)
elif locationType == 'ResoucePool':
vimType.append(vim.ResoucePool)
elif locationType == 'Datacenter':
vimType.append(vim.Datacenter)
objects = self.getObjects(vimType)

if locationType == 'Datacenter':
return objects[0].hostFolder
else:
return objects[0]


def getHostDatastores(self, hostObj=None, hostIpAddr=None):
"""获取VMware Host Datastore objects

Args:
None

Returns:
None

Raises:
None

"""

hostSystems = self.getHostSystems(hostObj, hostIpAddr)
dataStores = []
for host in hostSystems:
dataStores.extend(host.configManager.datastoreSystem.datastore)

return dataStores

def getHostDatastoreSystems(self, hostObj=None, hostIpAddr=None):
"""获取VMware Host Datastore System objects

Args:
None

Returns:
None

Raises:
None

"""

hostSystems = self.getHostSystems(hostObj, hostIpAddr)
dataStoreSystems = []
for host in hostSystems:
dataStoreSystems.extend(host.configManager.datastoreSystem)

return dataStoreSystems

def getCustomizationSpecManager(self):
"""获取VMware Customization Spec Manager Object

Args:
None

Returns:
None

Raises:
None

"""

return self.siObj.content.customizationSpecManager

def getStorageSystem(self):
"""获取VMware Storage System Object

Args:
None

Returns:
None

Raises:
None

"""

storageSystems=[]
hosts = self.getObjects([vim.hostSystem])
for host in hosts:
storageSystems.append(host.configManager.storageSystem)

return storageSystems


def waitForTask(self, tasks):
"""Wait for VMware_Task completed

Args:
None

Returns:
None

Raises:
None

"""

property_collector = self.siObj.content.propertyCollector
task_list = [str(task) for task in tasks]
# Create filter
obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
for task in tasks]
property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
pathSet=[],
all=True)
filter_spec = vmodl.query.PropertyCollector.FilterSpec()
filter_spec.objectSet = obj_specs
filter_spec.propSet = [property_spec]
pcfilter = property_collector.CreateFilter(filter_spec, True)
try:
version, state = None, None
# Loop looking for updates till the state moves to a completed state.
while len(task_list):
update = property_collector.WaitForUpdates(version)
for filter_set in update.filterSet:
for obj_set in filter_set.objectSet:
task = obj_set.obj
for change in obj_set.changeSet:
if change.name == 'info':
state = change.val.state
elif change.name == 'info.state':
state = change.val
else:
continue

if not str(task) in task_list:
continue

if state == vim.TaskInfo.State.success:
# Remove task from taskList
task_list.remove(str(task))
elif state == vim.TaskInfo.State.error:
raise task.info.error
# Move to next version
version = update.version
finally:
if pcfilter:
pcfilter.Destroy()

def getDiskObjects(self, available=1):
"""获取VMware Disk Object

Args:
None

Returns:
None

Raises:
None

"""

diskObjs = []
disks = []
if available == 1:
dsSystem = self.getHostDatastoreSystems()
for system in dsSystem:
disks = system.QueryAvailableDisksForVmfs
diskObjs.extend(disks)
else:
hosts = self.getHostSystems()
for host in hosts:
disks = host.config.storageDevice.scsiLun
diskObjs.extend(disks)

return diskObjs

def getVirtualDiskManager(self):
"""获取VMware Virtual Disk Manager对象

Args:
None

Returns:
None

Raises:
None

"""


if not self.virtualDiskManager:
self.virtualDiskManager = self.siObj.content.virtualDiskManager
return self.virtualDiskManager
=======================================================================================