#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
功 能: 执行CLI命令下发相关操作

版权信息: 华为技术有限公司，版权所有(C) 2014-2015

修改记录: 2016/5/3 严旭光 y00292329 created

"""
import re
from UniAutos.Wrapper import conf
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import Adapter
from Generator import Generator
from UniAutos.Wrapper.Template.ProductModel.OceanStor.ret import Parser
from UniAutos.Wrapper.Template.ProductModel.OceanStor.ret import Common
from UniAutos.Wrapper.Template import Convert
from Dryrun import Dryrun
from UniAutos import Log
from UniAutos.Wrapper.Template.ProductModel.OceanStor.cmd import CmdMapping
from UniAutos.Exception.UnImplementedException import UnImplementedException


class CLIObj(object):
logger = Log.getLogger(__name__)
defaultVersion = "V300R003C00"
dryrun = Dryrun()

def __init__(self, productModel=None, version=None, patchVersion=None):
"""执行CLI命令下发相关操作

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Changes:
2016-06-06 y00292329 Created

"""

self.conf = {k.lower(): v for (k, v) in conf.__dict__.items() if not k.startswith("__")}
self.generator = Generator()
self.device = None
self.productModel = productModel
self.version = version
self.patchVersion = patchVersion
self.cmdTemplates = self.choseCMDTemplate(productModel, version, patchVersion)

def runWrapper(self, methodName, params, interactRule=None, option=None):
"""执行wrapper命令

Args:
methodName (str): 方法名
params (dict): 方法参数
interactRule (dict): 交互输入规则
option (dict): 控制参数

Returns:
None

Exceptions:
UnImplementedException (exception): 未实现抽象方法异常

Changes:
2016-06-06 y00292329 Created

"""
raise UnImplementedException("This is an abstracted method, please implemented via inherited class")

def adaptParams(self,methodName, params, option):
"""适配新老wrapper的adapter方法

Args:
methodName (str): 新方法名
params (dict): 方法参数
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""
adapter_cmd_params = option.get("adapter_cmd_params", True)
if adapter_cmd_params:
adapter = Adapter.__dict__.get("adapter_"+ methodName, None)
Adapter.version = self.version + self.patchVersion
Adapter.productModel = self.productModel
if adapter:
params = adapter(params)
return params

def validate(self, result, option):
"""验证回显结果

Args:
result (str): 回显结果
option (dict): 控制参数

Returns:
result (bool): 验证是否通过

Changes:
2016-06-06 y00292329 Created

"""

validata_result = option.get("validate_result", True)
ignore_codes = self.device.ignore_codes
wrapper_ignores = self.device.wrapper_ignores

def validateFunc(info):
lineRaw = info["stdout"]

# 如果当前设备设置了ignore_codes, For ##Retry Frame##
__lineForIgnore = ''.join(lineRaw)

# 首先判断wrapper_ignores中是否有指定对应的wrapper method忽略指定的关键字.
for ignore_code in wrapper_ignores.iterkeys():
if option['method'] in wrapper_ignores[ignore_code]:
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for ignore_code in ignore_codes.get(option['sessionType'], []):
# 如果ignore_code在wrapper_ignores中出现过，则以wrapper_ignores为判断依据，这里不再继续处理.
if ignore_code in wrapper_ignores.iterkeys():
continue
matcher = re.search(r'' + str(ignore_code.lower()) + '', __lineForIgnore.lower(), re.M)
if matcher:
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Ignore Code: %s, "
"Ignore this command error." % ignore_code)
info['ignored_error'] = True
return True

for line in lineRaw:
matcher = re.search(
"\^(\n|\n\r|\r)?|Get wwn failed:sdId|Error:|Command failed|command not found|Try \'help\' for more information", line,
re.IGNORECASE)
if matcher:
return False
return True
if validata_result:
validationResult = validateFunc(result)
return validationResult
return True

def paserResult(self,retTemplate, result, option):
"""解析回显结果

Args:
retTemplate (dict): 回显模板
result (dict): 回显信息
option (dict): 控制参数

Changes:
2016-06-06 y00292329 Created

"""

parser_result = option.get("parser_ret", True)
if parser_result:
params = retTemplate.get("params", {})
parser = retTemplate.get("parser", None)

if result.pop('ignored_error', None):
self.logger.warn("###[UniAutos Ignore]:### Command Result Have Error But Ignored. "
"The parser will be null.")
result['parser'] = {}
return result

elif not parser:
parser = Parser.Parser()
convertDict =dict()
parser.primary = "id"
for x in params:
if isinstance(x, dict):
srcCol = x.get("srcCol", "").lower().replace(" ","_")
dstCol = x.get("dstCol", srcCol).lower().replace(" ","_")
primary = x.get("primary", None)
alter = x.get("alter", None)
if srcCol =="" and dstCol:
srcCol = dstCol
if srcCol != dstCol:
convertDict[srcCol] = {"converted_key": dstCol}
if alter:
if srcCol not in convertDict:
convertDict[srcCol] = dict()
convertDict[srcCol]["converted_value"] = getattr(Convert, alter)
if isinstance(primary, str) and primary == "true":
parser.primary = srcCol
parser.convertDict = convertDict
result['parser'] = parser.standardParser(self, result['stdout'])
else:
result['parser'] = Parser.__dict__.get(parser)(result['stdout'])
return result

def setDevice(self, device):
"""设置Wrapper所属的设备

Changes:
2016-06-06 y00292329 Created

"""

self.device = device

def getDevice(self):
"""获取设备

Changes:
2016-06-06 y00292329 Created

"""

return self.device

def setOption(self, option):
"""设置全局配置信息

Changes:
2016-06-06 y00292329 Created

"""

option = {k.lower():v for k, v in option.items() if True}
self.conf = dict(self.conf, **option)

def getTemplate(self, methodName):
"""获取命令模板

Args:
methodName (str): 方法名

Changes:
2016-06-06 y00292329 Created

"""

cmdTemplate = self.cmdTemplates.__dict__.get(methodName, None)
retTemplate = getattr(Common, methodName, {})
return cmdTemplate, retTemplate

def choseCMDTemplate(self, productModel, version, patchVersion):
"""执行wrapper命令

Args:
productModel (str): 设备类型
version (str): 版本号
patchVersion (str): 补丁版本号

Returns:
None

Exceptions:
UnImplementedException (exception): 未实现抽象方法异常

Changes:
2016-06-06 y00292329 Created

"""
raise UnImplementedException("This is an abstracted method, please implemented via inherited class")

def createPropertyInfoHash(self, componentClass, propertiesList):
if not isinstance(componentClass, str):
componentClass = componentClass.__module__ + '.' + componentClass.__name__
methodHash = CmdMapping.MethodHash.get(componentClass, None)
if methodHash is None:
return {}
temp = {}
for prop in propertiesList:
temp[prop] = {"getmethod":methodHash.get("show"),
"setmethod":methodHash.get("update", "")}
return temp

def getCommonPropertyInfo(self, getMethod, properties=None):
objs = []
for k,v in CmdMapping.MethodHash.items():
if getMethod == v.get("show", ""):
objs.append(k)
return objs
return objs

def hasMethod(self, methodName):
if self.cmdTemplates:
if self.cmdTemplates.__dict__.get(methodName, None):
return True
return False