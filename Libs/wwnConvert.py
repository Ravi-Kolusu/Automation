#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

功 能: 用于字符的编解码，如包含中文字符的输出等.

"""
import pprint
import json
import collections
import datetime
import re
from UniAutos import Log
from UniAutos.Util.Threads import Threads
from UniAutos.Util.Time import sleep
from UniAutos.TestEngine.ParameterType.IpAddress import IpAddress
from UniAutos.Exception.UniAutosException import UniAutosException

logger = Log.getLogger("Codec")


def wwnConvert(wwn):
"""转换不带:的wwn为带:的wwn"""
wwnList = []

length = len(wwn)
for n in range(length):
if n % 2 == 0:
wwnList.append(wwn[n:n + 2])
return ':'.join(wwnList)


def getCnFormatString(value):
"""打印包含中文的字典或列表

python 2.x中包含中文的字典输出到控制台时会输出为乱码.

Args:
value (dict|list): 包含中文的字典或列表.

"""
return json.dumps(value, encoding="utf-8", ensure_ascii=False)


def getFormatString(value):
"""安装格式打印字典或列表，中文无法打印

Args:
value (dict|list): 字典或列表.

"""
return pprint.pformat(value)


def convertBooleanToYesorNo(value):
"""转换Boolean Value为Yes或者No

Args:
value (bool): 需要被转换的值

Returns:
if value is True, return 'yes'.
if value is False, return 'no'.

"""
if value is True:
return 'yes'
elif value is False:
return 'no'
else:
raise UniAutosException("Cannot convert the value %s to Yes or No" % value)


def convertToUtf8(data):
"""转换包含unicode的字符串、字典、list为UTF-8编码格式

Args:
data (str|list|dict): 包含unicode的字符串、字典、list数据.

Returns:
data (str|list|dict): 转码为utf-8的字符串、字典、list数据.

Examples:
data = {'name': 'lun_name', 'value': u'\u4e2d\u6587'}
data = convertToUtf8(data)
>>
{'name': 'lun_name', 'value': '\xe4\xb8\xad\xe6\x96\x87'}
"""
if isinstance(data, basestring):
return data.encode('utf-8')

elif isinstance(data, collections.Mapping):
return dict(map(convertToUtf8, data.iteritems()))

elif isinstance(data, collections.Iterable):
return type(data)(map(convertToUtf8, data))

else:
return data


def trim(msg, trimMode=0):
"""
Remove all the blank space from string or unicode message,
Then return the new string

Args:
msg (object): message need remove the blank space.
trimMode (int) : remove mode， ranging from:
0 : remove all blank space.
1 : remove head blank space.
2 : remove tail blank space, if tail have \r\n, \n, this also be removed.
3 : remove head and tail blank space, if tail have \r\n, \n, this also be removed.

"""
if type(msg) in (str, unicode):
if trimMode == 0:
msg = str(msg)
msg = msg.replace(" ", "")
if trimMode == 1:
msg = re.sub(r'^\s+', "", msg)
if trimMode == 2:
msg = re.sub(r'\s+$', "", msg)
if trimMode == 3:
msg = re.sub(r'^\s+|\s+$', "", msg)
return msg


def split(msg):
"""将msg字符串的内容通过"\r\n", "\n", "\r"分段成一个list

Args：
msg (str): 待处理的字符串

Returns:
返回处理后的list

Examples:
result = self.split(msg)

"""
if not msg:
return []
return re.split("\x0d?\x0a|\x0d", msg)


def getCurrentDate():
"""
Get the current day with format

Returns:
timeStamp (str): the string for current date. 格式为: %Y-%m.
Examples:
timeStamp = self.getCurrentDate()

"""
return datetime.datetime.now().strftime("%Y-%m-%d")


def getCurrentTimeStr():
"""
Get the current time stamp with format

Returns:
timeStamp (str): the string for current time stamp. 格式为: %Y-%m-%d_%H:%M:%S.

Examples:
timeStamp = self.getCurrentTimeStr()

"""
return datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")


def isIpAddress(ipAddress):
"""
Verify whether the ip address valid or not.

Args:
ipAddress Type(str): Ipv4 address

Returns:
Type(Boolean): If valid, return true; Else return false

Changes:
2015/10/22 y00305138 Created

"""
typeAndValidation = {"type": "ip_address"}
ipObject = IpAddress(typeAndValidation)

return ipObject.getValidInput(ipAddress)


def isIpv4Address(ip):
"""判断输入的ip是否为ipv4格式.

Args:
ip (str): 需要校验的ipv4地址字符串.

Returns:
True (bool): 是ipv4.
False(bool): 不是ipv4.

Examples:
IpAddress.__isIpv4Address("10.20.10.30")

"""
# ipv4正则表达式, 从0.0.0.0到255.255.255.255
ipv4Regex = r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|' \
r'2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|' \
r'[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

return re.match(ipv4Regex, ip) is not None


def isIpv6Address(ip):
"""判断输入的ip是否为ipv6格式.

Args:
ip (str): 需要校验的ipv6地址字符串.

Returns:
True (bool): 是ipv6.
False (bool)：不是ipv6.

Examples:
IpAddress.__isIpv6Address("2001:0DB8:02de::0e13")

"""
# 通常输入的格式，如：2001:0DB8:0000:0000:0000:0000:1428:0000
ipv6RegexNormal = r'^(((?=.*(::))(?!.*\3.+\3))\3?|[\dA-F]{1,4}:)([\dA-F]{1,4}(\3|:\b)' \
r'|\2){5}(([\dA-F]{1,4}(\3|:\b|$)|\2){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})\Z'

# 按组压缩格式，如：1763:0:0:0:0:b03:1:af18
ipv6RegexStandard = r'^(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}$'

# "." ，":"混合格式 ，如：1763:0:0:0:0:b03:127.32.67.15
ipv6RegexMixed = r'^(?:[a-fA-F0-9]{1,4}:){6}(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.)' \
r'{3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$'

# 最大化压缩格式，如：1762::B03:1:AF18
ipv6RegexCompressed = r'(?x)\A(?:(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}' \
r'|(?=(?:[a-fA-F0-9]{0,4}:){0,7}[a-fA-F0-9]{0,4}\Z)' \
r'(([0-9a-fA-F]{1,4}:){1,7}|:)((:[0-9a-fA-F]{1,4}){1,7}|:)' \
r'|(?:[a-fA-F0-9]{1,4}:){7}:|:(:[a-fA-F0-9]{1,4]){7})\Z'

return re.match(ipv6RegexNormal, ip) is not None \
or re.match(ipv6RegexStandard, ip) is not None \
or re.match(ipv6RegexCompressed, ip) is not None \
or re.match(ipv6RegexMixed, ip) is not None


def parallelExecute(functionName, instances, kwargs, timeOut=None):
"""Parallel execute the special function with parameters provided

Args:
functionName Type(function): The function will be call
instances Type(classobj): The class object list, which will call the function
kwargs Type(dict): Parameter key value list
timeOut Type(int): [Optional] Waiting seconds till thread killed. Used for thread.join().
By default: None

Changes:
2015/12/18 y00305138 Created

"""

i = 0
threads = []
errors = []

for inst in instances:
th = Threads(getattr(inst, str(functionName)), threadName="Thread: %d" % i, **kwargs)

threads.append(th)
i += 1

for th in threads:
th.start()

for th in threads:
if th.is_alive():
if timeOut is not None:
th.join(timeOut)
else:
th.join()
if th.errorMsg:
errors.append(th.errorMsg)

if len(errors) > 0:
raise UniAutosException("Failed to parallel execute all function, \n %s" % errors)


def jsonLoadByFile(fp):
return _unicodeToString(
json.load(fp, object_hook=_unicodeToString),
ignoreDicts=True
)


def jsonLoadByText(jsonText):
return _unicodeToString(
json.loads(jsonText, object_hook=_unicodeToString),
ignoreDicts=True
)


def _unicodeToString(data, ignoreDicts=False):
# if this is a unicode string, return its string representation
if isinstance(data, unicode):
return data.encode('utf-8')
# if this is a list of values, return list of byteified values
if isinstance(data, list):
return [_unicodeToString(item, ignoreDicts=True) for item in data]
# if this is a dictionary, return dictionary of byteified keys and values
# but only if we haven't already byteified it
if isinstance(data, dict) and not ignoreDicts:
return {
_unicodeToString(key, ignoreDicts=True): _unicodeToString(value, ignoreDicts=True)
for key, value in data.iteritems()
}
# if it's anything else, return it in its original form
return data